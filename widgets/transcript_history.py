"""Transcript history widgets and persistence helpers."""

import datetime
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from kivy.clock import Clock
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from utils.device_info import DeviceInfo
from env import TEXT_COLOR, FONT_SIZE_HISTORY, LINE_HEIGHT, FONT_NAME

BASE_DIR = os.path.dirname(__file__)

# Configurações exportadas (utilizadas por outros módulos)
MAX_PARTIAL_CHARS = 120
PARTIAL_UPDATE_MIN_MS = 80
HISTORY_MAX_LINES = 200
PARTIAL_RESET_MS = 3000
MAX_LINE_CHARS = 40

TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "..", "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

FLUSH_DEBOUNCE_SEC = 0.6
TRANSCRIPT_EXECUTOR = ThreadPoolExecutor(max_workers=1)
DEBUG_TRANSCRIPTS = bool(int(os.environ.get("SONORIS_DEBUG_TRANSCRIPTS", "0")))


def _log_debug(message: str) -> None:
    if DEBUG_TRANSCRIPTS:
        print(message)


def _persist_conversation(
    conversation_id: str,
    created_at: str,
    lines: List[dict],
    finalized: bool,
) -> None:
    if not conversation_id or not lines:
        return
    try:
        payload = {
            "conversation_id": conversation_id,
            "created_at": created_at,
            "finalized": finalized,
            "lines": lines,
        }
        conversation_file = os.path.join(TRANSCRIPTS_DIR, f"{conversation_id}.json")
        with open(conversation_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        if DEBUG_TRANSCRIPTS:
            print(f"[TRANSCRIPTS] Persisted {conversation_id} ({len(lines)} linhas)")
    except Exception as exc:
        print(f"[TRANSCRIPTS] Erro ao salvar {conversation_id}: {exc}")


class TranscriptHistory(GridLayout):
    """Widget que exibe e persiste o histórico de transcrições."""

    def __init__(self, ble_service_ref=None, **kwargs):
        kwargs.setdefault("padding", 10)
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.spacing = 10
        self.bind(minimum_height=self.setter("height"))
        self.lines: List[Label] = []

        self.ble_service_ref = ble_service_ref
        self.device_info = DeviceInfo()

        self.is_private_mode = False
        self.saved_lines: List[dict] = []
        self.conversation_id: Optional[str] = None
        self._conversation_created_at: Optional[str] = None
        self.conversation_finalized = False
        self._flush_event = None

        self._begin_new_conversation()
        TRANSCRIPT_EXECUTOR.submit(self._finalize_old_conversations)

    def _begin_new_conversation(self):
        self.saved_lines = []
        self.conversation_finalized = False
        self.conversation_id = self._generate_conversation_id()
        self._conversation_created_at = datetime.datetime.now().isoformat()
        self.device_info.increment_conversation_counter()
        _log_debug(f"[TRANSCRIPTS] Nova conversa: {self.conversation_id}")

    def _generate_conversation_id(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"Conversa_{timestamp}"

    def _finalize_old_conversations(self) -> None:
        try:
            if not os.path.exists(TRANSCRIPTS_DIR):
                return
            for file in os.listdir(TRANSCRIPTS_DIR):
                if not file.endswith(".json"):
                    continue
                path = os.path.join(TRANSCRIPTS_DIR, file)
                try:
                    with open(path, "r", encoding="utf-8") as handle:
                        data = json.load(handle)
                    lines = data.get("lines", [])
                    if not lines:
                        os.remove(path)
                        continue
                    if not data.get("finalized"):
                        data["finalized"] = True
                        with open(path, "w", encoding="utf-8") as handle:
                            json.dump(data, handle, ensure_ascii=False, indent=2)
                except Exception as exc:
                    print(f"[TRANSCRIPTS] Erro ao finalizar {file}: {exc}")
        except Exception as exc:
            print(f"[TRANSCRIPTS] Erro geral ao finalizar conversas: {exc}")

    def start_new_conversation(self):
        if not self.is_private_mode and self.saved_lines:
            self._flush_conversation_async(finalized=True)
        self._begin_new_conversation()

    def set_private_mode(self, is_private: bool):
        self.is_private_mode = is_private
        if is_private and self._flush_event:
            try:
                self._flush_event.cancel()
            except Exception:
                pass
            self._flush_event = None

    def add_line(self, text):
        import env as env_module

        lbl = Label(
            text=text,
            size_hint_y=None,
            halign="left",
            valign="middle",
            text_size=(self.width, None),
            font_size=env_module.FONT_SIZE_HISTORY,
            color=env_module.TEXT_COLOR,
            font_name=env_module.FONT_NAME,
            line_height=env_module.LINE_HEIGHT,
        )

        def _on_width(inst, width_val):
            inst.text_size = (width_val, None)

        def _on_texture_size(inst, tex_size):
            try:
                inst.height = tex_size[1]
            except Exception:
                pass

        lbl.bind(width=_on_width, texture_size=_on_texture_size)
        self.add_widget(lbl)
        Clock.schedule_once(lambda dt: _on_texture_size(lbl, lbl.texture_size), 0)
        self.lines.append(lbl)

        if self.is_private_mode:
            return

        timestamp = datetime.datetime.now().isoformat()
        self.saved_lines.append({"text": text, "timestamp": timestamp})
        self._schedule_flush()

    def clear_all(self):
        self.start_new_conversation()
        for widget in list(self.lines):
            try:
                self.remove_widget(widget)
            except Exception:
                pass
        self.lines = []

    def _schedule_flush(self, force: bool = False):
        if self.is_private_mode:
            return
        if force:
            if self._flush_event:
                try:
                    self._flush_event.cancel()
                except Exception:
                    pass
                self._flush_event = None
            self._flush_conversation_async()
            return
        if self._flush_event is None:
            self._flush_event = Clock.schedule_once(self._flush_timer_cb, FLUSH_DEBOUNCE_SEC)

    def _flush_timer_cb(self, _dt):
        self._flush_event = None
        self._flush_conversation_async()

    def _flush_conversation_async(
        self,
        lines_snapshot: Optional[List[dict]] = None,
        finalized: Optional[bool] = None,
    ) -> None:
        if self.is_private_mode:
            return
        lines = lines_snapshot if lines_snapshot is not None else list(self.saved_lines)
        if not lines:
            return
        conversation_id = self.conversation_id
        created_at = self._conversation_created_at or datetime.datetime.now().isoformat()
        finalized_flag = self.conversation_finalized if finalized is None else finalized
        TRANSCRIPT_EXECUTOR.submit(
            _persist_conversation,
            conversation_id,
            created_at,
            lines,
            finalized_flag,
        )

    def get_saved_conversations(self):
        conversations = []
        try:
            for file in os.listdir(TRANSCRIPTS_DIR):
                if not file.endswith(".json"):
                    continue
                path = os.path.join(TRANSCRIPTS_DIR, file)
                with open(path, "r", encoding="utf-8") as handle:
                    conversations.append(json.load(handle))
        except Exception as exc:
            print(f"Erro ao listar conversas salvas: {exc}")
        return conversations

    def get_device_info_for_bluetooth(self):
        self.device_info.update_active_time()
        return self.device_info.get_device_data_for_bluetooth()

    def update_device_name(self, name):
        try:
            return self.device_info.update_device_name(name)
        except Exception as exc:
            print(f"[DEVICE_INFO] Erro ao atualizar nome: {exc}")
            return False
