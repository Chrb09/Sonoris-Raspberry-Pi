"""High-performance streaming transcription helper built on top of Vosk."""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
import wave
from collections import deque
from dataclasses import dataclass
from typing import Callable, Deque, Dict, Optional, Tuple

try:
    from vosk import Model, KaldiRecognizer
except Exception as exc:  # pragma: no cover - ensures clear error on import
    print("Vosk import error:", exc, file=sys.stderr)
    raise

try:  # optional voice activity detection
    import webrtcvad

    HAVE_VAD = True
except Exception:
    HAVE_VAD = False

import numpy as np
import sounddevice as sd


Callback = Optional[Callable[[str], None]]

DEFAULT_CONFIG: Dict[str, object] = {
    "model_path": "modelLarge",
    "sample_rate": 16000,
    "blocksize": 960,
    "frame_ms": 20,
    "queue_max_chunks": 32,
    "use_vad": True,
    "vad_mode": 2,
    "device": None,
    "enable_energy_gate": True,
    "energy_gate_dbfs": -45.0,
    "max_silence_frames": 6,
    "partial_debounce_ms": 120,
    "word_blacklist": ["aguardando...", "<unk>", "ah"],
}


@dataclass
class BenchmarkResult:
    audio_seconds: float
    wall_seconds: float
    real_time_factor: float
    final_transcript: str


class Transcriber:
    """Streaming transcriber with backpressure-aware audio ingestion."""

    def __init__(self, config: Optional[Dict[str, object]] = None):
        cfg = DEFAULT_CONFIG.copy()
        if config:
            cfg.update(config)

        self.config = cfg
        self.model_path = str(cfg["model_path"])
        self.sample_rate = int(cfg["sample_rate"])
        self.blocksize = int(cfg["blocksize"])
        self.frame_ms = int(cfg["frame_ms"])
        self.device = cfg.get("device")
        self.queue_max_chunks = int(cfg["queue_max_chunks"])
        self.use_vad = bool(cfg["use_vad"]) and HAVE_VAD
        self.vad_mode = int(cfg["vad_mode"]) if self.use_vad else None
        self.enable_energy_gate = bool(cfg.get("enable_energy_gate", True))
        self.energy_gate_dbfs = float(cfg.get("energy_gate_dbfs", -45.0))
        self.max_silence_frames = int(cfg.get("max_silence_frames", 6))
        self.partial_debounce = float(cfg.get("partial_debounce_ms", 120)) / 1000.0
        raw_blacklist = cfg.get("word_blacklist", []) or []
        normalized = [str(item).strip() for item in raw_blacklist if str(item).strip()]
        self._blacklist_exact = {item.lower() for item in normalized}
        self._blacklist_tokens = {token.lower() for item in normalized for token in item.split()}

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        self.model = Model(self.model_path)
        self.streaming_recognizer = KaldiRecognizer(self.model, self.sample_rate)
        try:  # enables richer metadata when model supports it
            self.streaming_recognizer.SetWords(True)
        except AttributeError:
            pass

        self.vad = None
        if self.use_vad:
            try:
                self.vad = webrtcvad.Vad(self.vad_mode)
            except Exception:
                self.vad = None
                self.use_vad = False

        self.bytes_per_sample = 2  # int16 PCM
        self.frame_bytes = int(self.sample_rate * (self.frame_ms / 1000.0) * self.bytes_per_sample)
        if self.frame_bytes <= 0:
            raise ValueError("frame_ms too small for the configured sample rate")
        self.min_feed_bytes = max(self.frame_bytes * 2, self.frame_bytes)

        self._audio_q: "queue.Queue[Tuple[float, bytes]]" = queue.Queue(maxsize=self.queue_max_chunks)
        self._running = threading.Event()
        self._worker: Optional[threading.Thread] = None
        self._stream: Optional[sd.RawInputStream] = None

        self._pending_bytes = bytearray()
        self._chunk_times: Deque[Tuple[float, int]] = deque()
        self._speech_buffer = bytearray()
        self._silence_frames = 0
        self._speech_active = False

        self._on_partial: Callback = None
        self._on_final: Callback = None
        self._on_error: Optional[Callable[[Exception], None]] = None

        self._last_partial_text = ""
        self._last_partial_emit = 0.0
        self._last_audio_ts = time.perf_counter()

        self._latency_samples: Deque[float] = deque(maxlen=100)
        self._frames_processed = 0

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def set_callbacks(self, on_partial: Callback = None, on_final: Callback = None, on_error: Callback = None) -> None:
        self._on_partial = on_partial
        self._on_final = on_final
        self._on_error = on_error

    def start(self) -> None:
        if self._running.is_set():
            return
        self._running.set()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

        try:
            self._stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.blocksize,
                dtype="int16",
                channels=1,
                device=self.device,
                callback=self._audio_callback,
                latency="low",
            )
            self._stream.start()
        except Exception as exc:
            self._running.clear()
            if self._on_error:
                self._on_error(exc)
            else:
                raise

    def stop(self) -> None:
        if not self._running.is_set():
            return
        self._running.clear()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self._signal_worker_shutdown()
        if self._worker is not None:
            self._worker.join(timeout=2.0)
            self._worker = None
        self._flush_recognizer(force=True)

    def get_stats(self) -> Dict[str, float]:
        latencies = list(self._latency_samples)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        return {
            "latency_ms_avg": avg_latency * 1000.0,
            "latency_ms_max": max_latency * 1000.0,
            "frames_processed": float(self._frames_processed),
            "queue_fill_ratio": self._audio_q.qsize() / float(self.queue_max_chunks),
        }

    # ------------------------------------------------------------------
    # Audio ingestion pipeline
    # ------------------------------------------------------------------
    def _audio_callback(self, indata, frames, time_info, status) -> None:
        if status:
            print("Audio status:", status, file=sys.stderr)
        chunk = bytes(indata)
        timestamp = time.perf_counter()
        try:
            self._audio_q.put_nowait((timestamp, chunk))
        except queue.Full:
            try:
                _ = self._audio_q.get_nowait()
            except queue.Empty:
                pass
            try:
                self._audio_q.put_nowait((timestamp, chunk))
            except queue.Full:
                pass
        except Exception as exc:
            if self._on_error:
                self._on_error(exc)

    def _worker_loop(self) -> None:
        while self._running.is_set() or not self._audio_q.empty():
            try:
                item = self._audio_q.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break
            chunk_ts, chunk = item
            self._append_chunk(chunk_ts, chunk)
            self._drain_pending_frames()

    def _append_chunk(self, timestamp: float, chunk: bytes) -> None:
        self._pending_bytes.extend(chunk)
        self._chunk_times.append((timestamp, len(chunk)))

    def _drain_pending_frames(self) -> None:
        while len(self._pending_bytes) >= self.frame_bytes:
            frame = bytes(self._pending_bytes[: self.frame_bytes])
            del self._pending_bytes[: self.frame_bytes]
            frame_ts = self._consume_chunk_time(self.frame_bytes)
            self._handle_frame(frame, frame_ts)

    def _consume_chunk_time(self, consumed: int) -> float:
        ts = 0.0
        remaining = consumed
        while remaining > 0 and self._chunk_times:
            chunk_ts, chunk_len = self._chunk_times[0]
            if ts == 0:
                ts = chunk_ts
            take = min(remaining, chunk_len)
            remaining -= take
            if take == chunk_len:
                self._chunk_times.popleft()
            else:
                self._chunk_times[0] = (chunk_ts, chunk_len - take)
        return ts or time.perf_counter()

    # ------------------------------------------------------------------
    # Frame handling and decoding
    # ------------------------------------------------------------------
    def _handle_frame(self, frame: bytes, frame_ts: float) -> None:
        self._frames_processed += 1
        speech = self._is_speech(frame)

        if speech:
            self._speech_active = True
            self._silence_frames = 0
            self._speech_buffer.extend(frame)
            if len(self._speech_buffer) >= self.min_feed_bytes:
                self._feed_recognizer(frame_ts)
        else:
            self._silence_frames += 1 if self._speech_active else 0
            if self._speech_buffer:
                self._feed_recognizer(frame_ts)
            if self._speech_active and self._silence_frames >= self.max_silence_frames:
                self._speech_active = False
                self._flush_recognizer()

    def _is_speech(self, frame: bytes) -> bool:
        if self.vad is not None:
            try:
                if not self.vad.is_speech(frame, self.sample_rate):
                    return False
            except Exception:
                pass
        if not self.enable_energy_gate:
            return True
        frame_view = np.frombuffer(frame, dtype=np.int16)
        if not frame_view.size:
            return False
        rms = np.sqrt(np.mean(frame_view.astype(np.float32) ** 2))
        if rms <= 0:
            return False
        dbfs = 20 * np.log10(rms / 32768.0)
        return dbfs >= self.energy_gate_dbfs

    def _feed_recognizer(self, frame_ts: float) -> None:
        if not self._speech_buffer:
            return
        chunk = bytes(self._speech_buffer)
        self._speech_buffer.clear()
        self._last_audio_ts = frame_ts or time.perf_counter()

        try:
            accepted = self.streaming_recognizer.AcceptWaveform(chunk)
            if accepted:
                self._emit_final_from_result(self.streaming_recognizer.Result())
                self._last_partial_text = ""
            else:
                self._emit_partial()
        except Exception as exc:
            self._recover_recognizer(exc)

    def _emit_partial(self) -> None:
        if not self._on_partial:
            return
        try:
            payload = json.loads(self.streaming_recognizer.PartialResult())
        except Exception:
            return
        partial_raw = payload.get("partial", "") or ""
        partial = self._sanitize_text(partial_raw)
        now = time.perf_counter()
        if (
            partial
            and partial != self._last_partial_text
            and (now - self._last_partial_emit) >= self.partial_debounce
        ):
            self._last_partial_text = partial
            self._last_partial_emit = now
            self._on_partial(partial)

    def _emit_final_from_result(self, result_json: str) -> None:
        if not self._on_final:
            return
        try:
            payload = json.loads(result_json)
        except Exception:
            return
        final_raw = payload.get("text", "") or ""
        final = self._sanitize_text(final_raw)
        if final:
            latency = max(0.0, time.perf_counter() - self._last_audio_ts)
            self._latency_samples.append(latency)
            self._on_final(final)

    def _flush_recognizer(self, force: bool = False) -> None:
        if self._speech_buffer:
            self._feed_recognizer(time.perf_counter())
        try:
            final_json = self.streaming_recognizer.FinalResult()
        except AttributeError:
            final_json = self.streaming_recognizer.Result()
        if force or final_json:
            self._emit_final_from_result(final_json)

    def _recover_recognizer(self, exc: Exception) -> None:
        try:
            self.streaming_recognizer = KaldiRecognizer(self.model, self.sample_rate)
        except Exception:
            pass
        if self._on_error:
            self._on_error(exc)

    def _sanitize_text(self, text: str) -> str:
        cleaned = (text or "").strip()
        if not cleaned:
            return ""
        lowered = cleaned.lower()
        if lowered in self._blacklist_exact:
            return ""
        tokens = [token for token in cleaned.split() if token.lower() not in self._blacklist_tokens]
        sanitized = " ".join(tokens).strip()
        if sanitized.lower() in self._blacklist_exact:
            return ""
        return sanitized

    def _signal_worker_shutdown(self) -> None:
        try:
            self._audio_q.put_nowait(None)
        except queue.Full:
            try:
                _ = self._audio_q.get_nowait()
            except queue.Empty:
                pass
            try:
                self._audio_q.put_nowait(None)
            except queue.Full:
                pass

    # ------------------------------------------------------------------
    # Benchmark helper
    # ------------------------------------------------------------------
    @staticmethod
    def benchmark_from_wav(
        wav_path: str,
        model_path: str = DEFAULT_CONFIG["model_path"],
        sample_rate: int = DEFAULT_CONFIG["sample_rate"],
        frame_ms: int = DEFAULT_CONFIG["frame_ms"],
    ) -> BenchmarkResult:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found at {model_path}")
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Audio file not found at {wav_path}")

        model = Model(model_path)
        recognizer = KaldiRecognizer(model, sample_rate)
        try:
            recognizer.SetWords(True)
        except AttributeError:
            pass

        with wave.open(wav_path, "rb") as wav_file:
            if wav_file.getnchannels() != 1:
                raise ValueError("Benchmark WAV must be mono")
            if wav_file.getsampwidth() != 2:
                raise ValueError("Benchmark WAV must be 16-bit PCM")
            if wav_file.getframerate() != sample_rate:
                raise ValueError(f"Expected {sample_rate}Hz audio for benchmark")

            frame_samples = int(sample_rate * (frame_ms / 1000.0))
            total_frames = wav_file.getnframes()
            audio_seconds = total_frames / sample_rate
            start = time.perf_counter()

            final_text = ""
            while True:
                data = wav_file.readframes(frame_samples)
                if not data:
                    break
                if recognizer.AcceptWaveform(data):
                    final_text += " " + json.loads(recognizer.Result()).get("text", "")

            # include tail result
            final_text += " " + json.loads(recognizer.FinalResult()).get("text", "")
            wall_seconds = time.perf_counter() - start
            rtf = wall_seconds / audio_seconds if audio_seconds else 0.0

        return BenchmarkResult(
            audio_seconds=audio_seconds,
            wall_seconds=wall_seconds,
            real_time_factor=rtf,
            final_transcript=final_text.strip(),
        )


def _build_cli_parser():
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark or smoke-test the Transcriber")
    parser.add_argument("--benchmark", dest="wav", help="Path to WAV file for speed test")
    parser.add_argument("--model", dest="model", default=DEFAULT_CONFIG["model_path"], help="Model folder path")
    parser.add_argument("--sample-rate", dest="sample_rate", type=int, default=DEFAULT_CONFIG["sample_rate"], help="Sample rate")
    parser.add_argument("--frame-ms", dest="frame_ms", type=int, default=DEFAULT_CONFIG["frame_ms"], help="Chunk size for benchmark")
    return parser


def _run_cli():
    parser = _build_cli_parser()
    args = parser.parse_args()
    if not args.wav:
        parser.error("--benchmark <wav_path> is required")
    result = Transcriber.benchmark_from_wav(
        wav_path=args.wav,
        model_path=args.model,
        sample_rate=args.sample_rate,
        frame_ms=args.frame_ms,
    )
    print(
        json.dumps(
            {
                "audio_seconds": round(result.audio_seconds, 3),
                "wall_seconds": round(result.wall_seconds, 3),
                "real_time_factor": round(result.real_time_factor, 3),
                "transcript_preview": result.final_transcript[:80],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    _run_cli()
