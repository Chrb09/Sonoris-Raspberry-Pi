# widgets/transcript_history.py
import os
import json
import time
from datetime import datetime

from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from utils.colors import parse_color

# ------------------------------
# TranscriptHistory
# ------------------------------

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# configurações
FONT_SIZE_PARTIAL = 35
TEXT_COLOR_GRAY = parse_color(cfg.get("color_gray", None), default=((0.30, 0.31, 0.31, 1))) # cor cinza para o texto TODO
FONT_SIZE_HISTORY = cfg.get("tamanho_historico", 28) # tamanho da fonte do histórico
MAX_PARTIAL_CHARS = int(cfg.get("max_partial_chars", 120)) # máximo de caracteres do texto parcial
PARTIAL_UPDATE_MIN_MS = int(cfg.get("partial_update_min_ms", 80)) # intervalo mínimo entre atualizações do texto parcial
HISTORY_MAX_LINES = int(cfg.get("history_max_lines", 200)) # máximo de linhas no histórico
PARTIAL_RESET_MS = int(cfg.get("partial_reset_ms", 3000)) # tempo para resetar o texto parcial (ms)

# widget de histórico (scrollable)
class TranscriptHistory(GridLayout):
    def __init__(self, **kwargs):
        kwargs.setdefault('padding', 10) 
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.spacing = 10
        self.bind(minimum_height=self.setter('height')) # auto ajusta height ao conteúdo
        self.lines = []
        # controle de conversas (persistência)
        self._private = False
        self.current_conversation = None
        # pasta onde salvar conversas (criada no diretório de trabalho atual)
        self._convos_dir = os.path.join(os.getcwd(), "conversations")
        try:
            os.makedirs(self._convos_dir, exist_ok=True)
        except Exception:
            pass
        # inicia primeira conversa
        self.start_new_conversation()

    # adiciona linha ao histórico, removendo a mais antiga se necessário
    def add_line(self, text):
        # cria label com altura variável (size_hint_y=None) e permite quebra de linha via text_size
        lbl = Label(
            text=text,
            size_hint_y=None,
            halign='left',
            valign='middle',
            text_size=(self.width, None),
            font_size=FONT_SIZE_HISTORY,
            color=TEXT_COLOR_GRAY,
        )

        # quando a largura mudar, atualiza text_size para forçar rewrap do texto
        def _on_width(inst, w):
            inst.text_size = (w, None)
        lbl.bind(width=_on_width)

        # quando texture_size for calculado, ajusta a altura do label para o height do texto renderizado
        def _on_texture_size(inst, ts):
            try:
                inst.height = ts[1]
            except Exception:
                pass
        lbl.bind(texture_size=_on_texture_size)

        self.add_widget(lbl)
        # força uma atualização do texture_size no próximo frame para definir a altura inicial corretamente
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: _on_texture_size(lbl, lbl.texture_size), 0)
        self.lines.append(lbl)
        # registra também no objeto de conversa atual
        try:
            if self.current_conversation is not None:
                entry = {
                    "text": text,
                    "timestamp": int(time.time())
                }
                self.current_conversation.setdefault("lines", []).append(entry)
                # salva imediatamente se não for privado
                try:
                    if not self._private:
                        self._save_current_conversation()
                except Exception:
                    pass
        except Exception:
            pass

    # limpa todo o histórico
    def clear_all(self):
        for w in list(self.lines):
            try:
                self.remove_widget(w)
            except Exception:
                pass
        self.lines = []

    # marca o modo privado (quando True não grava conversas em disco)
    def set_private(self, flag: bool):
        try:
            self._private = bool(flag)
        except Exception:
            self._private = False

    # inicia uma nova conversa — finaliza a anterior gravando (se pública)
    def start_new_conversation(self, private: bool = False):
        # finaliza a conversa atual (garante que esteja salva se pública)
        try:
            # se existir e pública, salvamos (já tem been saved on add_line but ensure)
            if self.current_conversation is not None and not getattr(self, "_private", False):
                try:
                    self._save_current_conversation()
                except Exception:
                    pass
        except Exception:
            pass

        # cria nova conversa em memória
        try:
            now = datetime.utcnow()
            conv_id = now.strftime("%Y%m%d_%H%M%S")
            self.current_conversation = {
                "id": conv_id,
                "created_at": now.isoformat() + "Z",
                "lines": [],
                "private": bool(private)
            }
            # atualiza flag privada
            self._private = bool(private)
            # define caminho de arquivo para esta conversa (sempre sobrescrevemos)
            self.current_conversation["_file"] = os.path.join(self._convos_dir, f"conversation_{conv_id}.json")
        except Exception:
            self.current_conversation = {"id": "unknown", "created_at": "", "lines": [], "private": bool(private)}

    # salva o estado corrente da conversa em disco (sobrescreve)
    def _save_current_conversation(self):
        try:
            if not self.current_conversation:
                return
            # se marcado privado, não salvar
            if getattr(self, "_private", False):
                return
            # prepare payload sem campos internos
            payload = {
                "id": self.current_conversation.get("id"),
                "created_at": self.current_conversation.get("created_at"),
                "private": False,
                "lines": self.current_conversation.get("lines", [])
            }
            path = self.current_conversation.get("_file") or os.path.join(self._convos_dir, f"conversation_{payload['id']}.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except Exception:
                # fallback: tenta salvar em cwd
                try:
                    alt = os.path.join(os.getcwd(), f"conversation_{payload['id']}.json")
                    with open(alt, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
        except Exception:
            pass

    # finaliza a conversa atual (salva se pública) e começa outra
    def finalize_and_start_new(self, private_next: bool = False):
        try:
            # garantir que atual seja salva (se pública)
            try:
                if self.current_conversation and not getattr(self, "_private", False):
                    self._save_current_conversation()
            except Exception:
                pass
            # limpa UI
            self.clear_all()
            # inicia nova conversa com a flag private_next
            self.start_new_conversation(private=private_next)
        except Exception:
            pass
