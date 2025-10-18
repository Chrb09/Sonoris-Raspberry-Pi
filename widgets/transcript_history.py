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

    # limpa todo o histórico
    def clear_all(self):
        for w in list(self.lines):
            try:
                self.remove_widget(w)
            except Exception:
                pass
        self.lines = []
