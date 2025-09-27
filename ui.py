# ui.py 
import os
import json
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, Rectangle
from kivy.core.text import LabelBase
from kivy.uix.label import Label
from kivy.uix.button import Button

from transcriber import Transcriber
from widgets.toolbar import Toolbar
from widgets.icon_button import IconButton
from utils.colors import parse_color

# TODO deixar o botão funcional
# TODO otimizar o codigo
# TODO melhorar o design
# TODO adicionar todas as imagens dos botões
# TODO adicionar os widgets
# TODO consertar o erro do parse_color que não está retornando a cor correta

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
BACKGROUND_COLOR = parse_color(cfg.get("color_background", None), default=(0,0,0,1))
TOOLBAR_COLOR = parse_color(cfg.get("color_gray300", None), default=(0.168, 0.168, 0.168, 1))

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

Window.clearcolor = BACKGROUND_COLOR

# ------------------------------
# Testes de Configuração
# ------------------------------

print("\nTESTE DE CONFIGURAÇÕES DE UI \n------------------------------")

print("DEBUG: BACKGROUND_COLOR =", BACKGROUND_COLOR, type(BACKGROUND_COLOR)) # teste de cor de fundo da janela
print("DEBUG: TOOLBAR_COLOR =", TOOLBAR_COLOR, type(TOOLBAR_COLOR)) # teste de cor da toolbar

print("------------------------------\n")

# ------------------------------
# Widgets e Layouts
# ------------------------------

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', padding=0, spacing=6, **kwargs)

        # toolbar
        toolbar = Toolbar(bg_color=TOOLBAR_COLOR, height=132)

        icons_dir = os.path.join(BASE_DIR, "assets", "icons") # caminho dos ícones

        self.add_widget(toolbar)
        
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