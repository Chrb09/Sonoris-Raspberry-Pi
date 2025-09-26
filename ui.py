# ui.py 
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout

from transcriber import Transcriber
from utils.config import BACKGROUND_COLOR

# TODO deixar o botão funcional
# TODO otimizar o codigo
# TODO melhorar o design

# ------------------------------
# Configurações Globais do Kivy
# ------------------------------

def _normalize_color(c):
    if not c:
        return (0,0,0,1)
    # aceita tupla/lista de 3 ou 4 valores, em 0-255 ou 0-1
    vals = list(c)
    if len(vals) == 3:
        vals.append(1)
    # se algum valor > 1, assumimos 0-255 e normalizamos
    if any(v > 1 for v in vals):
        vals = [v / 255.0 for v in vals]
    return tuple(vals)

Window.clearcolor = _normalize_color(BACKGROUND_COLOR)

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
        self.title = "Sonoris - Transcrição"
        self.layout = MainLayout(self.transcriber)
        return self.layout