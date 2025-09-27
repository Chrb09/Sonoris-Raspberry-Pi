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
BACKGROUND_COLOR = parse_color(cfg.get("color_background", None), default=(0,0,0,1))
TOOLBAR_COLOR = parse_color(cfg.get("color_gray300", None), default=(0.168, 0.168, 0.168, 1))

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

# teste de cor de fundo da janela
print("DEBUG: BACKGROUND_COLOR =", BACKGROUND_COLOR, type(BACKGROUND_COLOR))
Window.clearcolor = BACKGROUND_COLOR

class Toolbar(AnchorLayout):
    def __init__(self, items=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None # altura fixa
        self.height = 100 # altura da toolbar
        self.anchor_x = 'center'
        self.anchor_y = 'bottom'
        
         # fundo da toolbar com canvas.before
        with self.canvas.before:
            Color(*TOOLBAR_COLOR)
            self.rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_rect, size=self._update_rect)
        
        # container horizontal para os itens
        container = BoxLayout(orientation='horizontal', spacing=10, padding=10, size_hint=(None, None))
        container.height = self.height

        # adiciona os itens se houver
        if items:
            for item in items:
                container.add_widget(item)

        # ajusta a largura do container baseado nos filhos
        container.width = sum([child.width for child in container.children]) + container.spacing * (len(container.children)-1)
        self.add_widget(container)

    # atualiza o retângulo do fundo quando a posição ou tamanho mudar
    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# ------------------------------
# Widgets e Layouts
# ------------------------------

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', padding=0, spacing=6, **kwargs)

        toolbar = Toolbar(items=[
            Button(text="Pause", size_hint=(None, 1), width=80),
            Button(text="Resume", size_hint=(None, 1), width=80),
            ])
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