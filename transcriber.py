# transcriber.py
import os
import json
import queue
import threading
import time
import sys

try:
    from vosk import Model, KaldiRecognizer
except Exception as e:
    print("Vosk import error:", e, file=sys.stderr)
    raise

# optional webrtcvad
try:
    import webrtcvad
    HAVE_VAD = True
except Exception:
    HAVE_VAD = False

import sounddevice as sd
import numpy as np

class Transcriber:
    """
    Transcriber: encapsula audio capture + Vosk decoding.
    Callbacks (set via set_callbacks):
      - on_partial(text)
      - on_final(text)
      - on_error(exc)
    Methods:
      - start(): inicia stream e worker
      - stop(): para tudo
    """

    def __init__(self, config):
        self.config = config.copy()
        self.model_path = config.get("model_path")
        self.sample_rate = int(config.get("sample_rate", 16000))
        self.blocksize = int(config.get("blocksize", 800))
        self.frame_ms = int(config.get("frame_ms", 20))
        self.device = config.get("device", None)
        self.use_vad = bool(config.get("use_vad", True)) and HAVE_VAD
        self.vad_mode = int(config.get("vad_mode", 2)) if HAVE_VAD else None

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        # load model
        self.model = Model(self.model_path)

        # streaming recognizer used for partials
        self.streaming_recognizer = KaldiRecognizer(self.model, self.sample_rate)

        # vad
        self.vad = None
        if self.use_vad:
            try:
                self.vad = webrtcvad.Vad(self.vad_mode)
            except Exception:
                self.vad = None
                self.use_vad = False

        # audio queue and worker control
        self.audio_q = queue.Queue(maxsize=8)
        self.running = threading.Event()

        # callbacks
        self._on_partial = None
        self._on_final = None
        self._on_error = None

        # worker thread and stream
        self._worker = None
        self._stream = None

    def set_callbacks(self, on_partial=None, on_final=None, on_error=None):
        self._on_partial = on_partial
        self._on_final = on_final
        self._on_error = on_error

    # helper to split bytes into frames
    def _frame_generator(self, frame_ms, sample_rate, data_bytes):
        bytes_per_sample = 2
        frame_bytes = int(sample_rate * (frame_ms / 1000.0) * bytes_per_sample)
        offset = 0
        length = len(data_bytes)
        while offset + frame_bytes <= length:
            yield data_bytes[offset:offset + frame_bytes]
            offset += frame_bytes

    # audio callback passed to sounddevice
    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            # keep printing minimal
            print("Audio status:", status, file=sys.stderr)
        try:
            b = indata.tobytes()
            try:
                self.audio_q.put_nowait(b)
            except queue.Full:
                # drop oldest then put new
                try:
                    _ = self.audio_q.get_nowait()
                    self.audio_q.put_nowait(b)
                except queue.Empty:
                    pass
        except Exception as e:
            if self._on_error:
                self._on_error(e)

    def start(self):
        """Start audio stream and worker thread."""
        if self.running.is_set():
            return
        self.running.set()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

        try:
            # start input stream
            self._stream = sd.InputStream(samplerate=self.sample_rate,
                                         device=self.device,
                                         dtype='int16',
                                         channels=1,
                                         callback=self._audio_callback,
                                         blocksize=self.blocksize,
                                         latency='low')
            self._stream.start()
        except Exception as e:
            self.running.clear()
            if self._on_error:
                self._on_error(e)
            else:
                raise

    def stop(self):
        """Stop streaming and worker."""
        self.running.clear()
        # stop audio stream
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception:
            pass
        # join worker shortly
        if self._worker is not None:
            self._worker.join(timeout=1.0)

    def _worker_loop(self):
        """Worker: reads queue, feeds recognizer, calls callbacks."""
        last_partial = ""
        in_speech = False
        silence_frames = 0

        while self.running.is_set():
            try:
                data = self.audio_q.get(timeout=0.2)
            except queue.Empty:
                continue

            for frame in self._frame_generator(self.frame_ms, self.sample_rate, data):
                is_speech = True
                if self.vad is not None:
                    try:
                        is_speech = self.vad.is_speech(frame, self.sample_rate)
                    except Exception:
                        is_speech = True

                if self.vad is not None and not is_speech and not in_speech:
                    # occasional small feed to keep model state
                    silence_frames += 1
                    if silence_frames < 2:
                        try:
                            if self.streaming_recognizer.AcceptWaveform(frame):
                                res = self.streaming_recognizer.Result()
                                final = json.loads(res).get("text", "")
                                if final and self._on_final:
                                    self._on_final(final)
                        except Exception as e:
                            if self._on_error:
                                self._on_error(e)
                    continue

                silence_frames = 0
                try:
                    if self.streaming_recognizer.AcceptWaveform(frame):
                        res = self.streaming_recognizer.Result()
                        final = json.loads(res).get("text", "")
                        if final:
                            if self._on_final:
                                self._on_final(final)
                            last_partial = ""
                            in_speech = False
                    else:
                        pr = self.streaming_recognizer.PartialResult()
                        p = json.loads(pr).get("partial", "")
                        if p is None:
                            p = ""
                        # only send partial if changed (avoids floods)
                        if p != last_partial and self._on_partial:
                            self._on_partial(p)
                            last_partial = p
                            in_speech = True
                except Exception as e:
                    # try to recover recognizer
                    try:
                        self.streaming_recognizer = KaldiRecognizer(self.model, self.sample_rate)
                    except Exception:
                        pass
                    if self._on_error:
                        self._on_error(e)

        # loop ended
