# ui.py 
import os
import json
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.metrics import dp
from kivy.core.text import LabelBase

from transcriber import Transcriber
from widgets.divider import Divider
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
TEXT_COLOR = parse_color(cfg.get("color_background", None), default=(1,1,1,1))
BACKGROUND_COLOR = parse_color(cfg.get("color_background", None), default=(0,0,0,1))
TOOLBAR_COLOR = parse_color(cfg.get("color_blue", None), default=(0.168, 0.168, 0.168, 1))

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

Window.clearcolor = BACKGROUND_COLOR

# ------------------------------
# Testes de Configuração
# ------------------------------

print("\nTESTE DE CONFIGURAÇÕES DE UI \n------------------------------")

print("DEBUG: FONT_NAME =", FONT_NAME, type(FONT_NAME)) # teste de fonte
print("DEBUG: BACKGROUND_COLOR =", BACKGROUND_COLOR, type(BACKGROUND_COLOR)) # teste de cor de fundo da janela
print("DEBUG: TOOLBAR_COLOR =", TOOLBAR_COLOR, type(TOOLBAR_COLOR)) # teste de cor da toolbar

print("------------------------------\n")

# ------------------------------
# Widgets e Layouts
# ------------------------------

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        # toolbar
        toolbar = Toolbar(orientation='vertical', bg_color=TOOLBAR_COLOR, height=132, min_height=98, max_height=132)
        divider = Divider(orientation='horizontal', divider_color=TEXT_COLOR, target_widget=toolbar, min_height=toolbar.min_height, max_height=toolbar.max_height)
        
        anchor_div = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(1, None), height=20)
        anchor_div.add_widget(divider)
        toolbar.add_widget(anchor_div)

        # botões na toolbar
        icons_dir = os.path.join(BASE_DIR, "assets", "icons") # caminho dos ícones
        self.plus_btn = IconButton(icon_src=os.path.join(icons_dir, "plus.png"), text='[b][/b]')
        self.pause_btn = IconButton(icon_src=os.path.join(icons_dir, "pause.png"), text='[b][/b]')

        self.plus_btn.bind(on_release=lambda inst: print("Clicou no plus_btn")) # TODO funcionalidade
        self.pause_btn.bind(on_release=lambda inst: print("Clicou no pause_btn")) # TODO funcionalidade

        button_group = BoxLayout(orientation='horizontal', size_hint=(None, None), spacing=18)
        button_group.width = self.plus_btn.width + self.pause_btn.width
        button_group.height = max(self.plus_btn.height, self.pause_btn.height) # define altura do grupo de botões
 
        button_group.add_widget(self.plus_btn)
        button_group.add_widget(self.pause_btn)

        # centraliza o grupo
        anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(1, 1))
        anchor.add_widget(button_group)
        toolbar.add_widget(anchor) # adiciona o grupo à toolbar

        self.add_widget(toolbar)
        
        toolbar.bind(height=self.on_toolbar_resize) # bind para ajustar botões ao redimensionar a toolbar

    # TODO arrumar esse método para que funcione
    def on_toolbar_resize(self, toolbar, value):
        """
        Esconde o texto dos botões quando a toolbar estiver no min_height.
        Atualiza de forma segura dependendo da implementação do IconButton.
        """
        collapsed = (value <= toolbar.min_height)

        def set_button_text(btn, text_when_shown, hide_when_collapsed=True):
            print("DEBUG: Setting button text for", btn, "collapsed =", collapsed)
            try:
                # verifica se tem atributo 'label' (um Label)
                if hasattr(btn, "label") and getattr(btn, "label") is not None:
                    # btn.label é um Label
                    btn.label.text = "" if collapsed and hide_when_collapsed else text_when_shown
                    print("DEBUG: Used btn.label.text for button text")
                    return
            except Exception:
                pass
            try:
                # verifica se tem atributo 'text' (um string)
                if hasattr(btn, "text"):
                    btn.text = "" if collapsed and hide_when_collapsed else text_when_shown
                    print("DEBUG: Used btn.text for button text")
                    return
            except Exception:
                pass
            try:
                # fallback: altera opacity
                btn.opacity = 0 if collapsed else 1
                print("DEBUG: Fallback opacity used for button text")
            except Exception:
                pass

        # textos desejados quando não colapsado
        set_button_text(self.plus_btn, "[b]Nova conversa[/b]")
        print("DEBUG: Toolbar resized to", value, "collapsed =", collapsed)

        
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