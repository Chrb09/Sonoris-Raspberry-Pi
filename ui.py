# ui.py 
import os
import json
from tkinter.ttk import Label

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.core.text import LabelBase

from utils.colors import parse_color
from transcriber import Transcriber

# TODO deixar o botão funcional
# TODO otimizar o codigo
# TODO melhorar o design
# TODO adicionar todas as imagens dos botões
# TODO adicionar os widgets

# ------------------------------
# Configurações Globais do Kivy
# ------------------------------

# configurações do aplicativo
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# configurações de UI (config.json)
FONT_NAME = cfg.get("fonte", None)
TEXT_COLOR = parse_color(cfg.get("color_white100", None), default=(1,1,1,1))
BACKGROUND_COLOR = parse_color(cfg.get("color_background500", None), default=(0,0,0,1))

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

# teste de cor de fundo da janela
print("DEBUG: BACKGROUND_COLOR =", BACKGROUND_COLOR, type(BACKGROUND_COLOR))
Window.clearcolor = BACKGROUND_COLOR

# ------------------------------
# Widgets e Layouts
# ------------------------------

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', padding=0, spacing=6, **kwargs)

# main app do kivy
class TranscriberApp(App):
    def __init__(self, transcriber: Transcriber, auto_start=True, **kwargs):
        super().__init__(**kwargs)
        self.transcriber = transcriber
        self.layout = None
        self._auto_start = auto_start

    # nome do aplicativo
    def build(self):
        self.title = "Transcrição de Voz Sonoris"
        self.layout = MainLayout(self.transcriber)
        return self.layout