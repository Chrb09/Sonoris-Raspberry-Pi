# widgets/icon_button.py
import os
import json

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
TEXT_COLOR_GRAY = parse_color(cfg.get("color_gray", None), default=(0.168, 0.168, 0.168, 1))
FONT_SIZE_HISTORY = cfg.get("tamanho_historico", 28) # tamanho da fonte do histórico
MAX_PARTIAL_CHARS = int(cfg.get("max_partial_chars", 240)) # máximo de caracteres do texto parcial
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
        self.bind(minimum_height=self.setter('height')) # auto ajusta height ao conteúdo
        self.lines = []

    # adiciona linha ao histórico, removendo a mais antiga se necessário
    def add_line(self, text):
        lbl = Label(text=text, size_hint_y=None, height=FONT_SIZE_HISTORY*1.6, halign='left', valign='middle',
                    text_size=(self.width, None), font_size=FONT_SIZE_HISTORY, color=TEXT_COLOR_GRAY)
        
        lbl.bind(width=lambda inst, w: inst.setter('text_size')(inst, (w, None))) # ajusta text_size ao width
        self.add_widget(lbl) 
        self.lines.append(lbl)

    # limpa todo o histórico
    def clear_all(self):
        for w in list(self.lines):
            try:
                self.remove_widget(w)
            except Exception:
                pass
        self.lines = []
