# ui.py 
import os
import json
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.metrics import dp
from kivy.core.text import LabelBase
from kivy.graphics import Color, Line
from transcriber import Transcriber
from widgets.divider import Divider
from widgets.toolbar import Toolbar
from widgets.transcript_history import FONT_SIZE_PARTIAL, MAX_PARTIAL_CHARS, PARTIAL_RESET_MS, TranscriptHistory
from widgets.icon_button import IconButton
from utils.colors import parse_color
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
import sys
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.graphics import Color, Rectangle
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.graphics import Color, RoundedRectangle


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
TEXT_COLOR = parse_color(cfg.get("color_blue", None), default=(1,1,1,1))
BACKGROUND_COLOR = parse_color(cfg.get("color_background", None), default=(1,1,1,1))
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
def _truncate_partial(text):
    if not text:
        return ""
    t = text.strip()
    if len(t) <= MAX_PARTIAL_CHARS:
        return t.capitalize()
    cut = t[:MAX_PARTIAL_CHARS]
    last_space = cut.rfind(' ')
    if last_space > int(MAX_PARTIAL_CHARS * 0.6):
        cut = cut[:last_space]
    return (cut + '…').capitalize()

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        
        # histórico de transcrição (scrollable)
        self.scroll = ScrollView(size_hint=(1, 1))
        self.history = TranscriptHistory()
        self.scroll.add_widget(self.history)
        self.add_widget(self.scroll)

        # texto parcial
        self.partial_label = Label(text="Aguardando...", size_hint=(1, 0.25), halign='center', valign='middle',
                                   text_size=(None, None), font_size=FONT_SIZE_PARTIAL, color=TEXT_COLOR)
        self.partial_label.bind(size=self._update_partial_text_size)
        self.add_widget(self.partial_label)

        self._partial_reset_ev = None

        # keep transcriber reference so we can start/stop from UI if needed
        self.transcriber = transcriber

        # toolbar
        toolbar = Toolbar(orientation='vertical', bg_color=TOOLBAR_COLOR, height=132, min_height=98, max_height=132)
        divider = Divider(orientation='horizontal', divider_color=BACKGROUND_COLOR, target_widget=toolbar, min_height=toolbar.min_height, max_height=toolbar.max_height)
        
        anchor_div = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(1, None), height=20)
        anchor_div.add_widget(divider)
        toolbar.add_widget(anchor_div)

        # botões na toolbar
        icons_dir = os.path.join(BASE_DIR, "assets", "icons") # caminho dos ícones
        self.plus_btn = IconButton(icon_src=os.path.join(icons_dir, "plus.png"), text='[b][/b]')
        self.pause_btn = IconButton(icon_src=os.path.join(icons_dir, "pause.png"), text='[b][/b]')

        self.plus_btn.bind(on_release=lambda inst: print("Clicou no plus_btn")) # TODO funcionalidade
        self.pause_btn.bind(on_release=lambda inst: print("Clicou no pause_btn")) # TODO funcionalidade

        button_group = BoxLayout(orientation='horizontal', spacing=15, size_hint=(None, None))
        button_group.width = self.plus_btn.width + self.pause_btn.width
        button_group.height = max(self.plus_btn.height, self.pause_btn.height) # define altura do grupo de botões

        button_group.add_widget(self.plus_btn)
        button_group.add_widget(self.pause_btn)

        # desenha borda
        # with button_group.canvas.before:
        #    Color(54, 1, 1, 1)  # cor da borda (vermelho para teste)
        #    Line(rectangle=(button_group.x, button_group.y, button_group.width, button_group.height), width=2)

        # centraliza o grupo
        anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(1, 1))
        anchor.add_widget(button_group)
        toolbar.add_widget(anchor) # adiciona o grupo à toolbar

        # desenha borda
        # with anchor.canvas.before:
        #    Color(54, 131, 21, 1)  # cor da borda (vermelho para teste)
        #    Line(rectangle=(anchor.x, anchor.y, anchor.width, anchor.height), width=2)
            
        self.add_widget(toolbar)
        
        toolbar.bind(height=self.on_toolbar_resize) # bind para ajustar botões ao redimensionar a toolbar
    
    def _update_partial_text_size(self, inst, val):
        inst.text_size = (inst.width - 20, inst.height)
    
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

        # UI-callable functions (schedule from callbacks)
    def add_final(self, text):
        sanitized = text.strip().capitalize() if text else ""
        if sanitized:
            self.history.add_line(sanitized)
            Clock.schedule_once(lambda dt: self.scroll.scroll_to(self.history.lines[-1]))
        # reset partial quickly
        Clock.schedule_once(lambda dt: self.set_partial("Aguardando..."), 0.01)

    def set_partial(self, text):
        self.partial_label.text = text
        # cancel previous reset timer
        if self._partial_reset_ev:
            try:
                self._partial_reset_ev.cancel()
            except Exception:
                pass
            self._partial_reset_ev = None

        # schedule reset
        txt = (text or "").strip()
        if txt and txt.lower() != "aguardando..." and PARTIAL_RESET_MS > 0:
            self._partial_reset_ev = Clock.schedule_once(lambda dt: self._reset_partial(), PARTIAL_RESET_MS / 1000.0)

    # reset do texto parcial
    def _reset_partial(self):
        self._partial_reset_ev = None
        self.partial_label.text = "Aguardando..."

    # limpa o histórico e reseta o parcial
    def _on_clear_history(self, instance):
        self.history.clear_all()
        self._reset_partial()

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
    
    def on_start(self):
        # atualiza o texto parcial
        def on_partial(p):
            Clock.schedule_once(lambda dt, p=p: self.layout.set_partial(_truncate_partial(p)))

        # adiciona linha finalizada no histórico
        def on_final(f):
            Clock.schedule_once(lambda dt, f=f: self.layout.add_final(f))

        # mostra erro no terminal
        def on_error(e):
            print("Transcriber error:", e, file=sys.stderr)

        self.transcriber.set_callbacks(on_partial=on_partial, on_final=on_final, on_error=on_error)

        # start transcriber only if auto_start is true
        if self._auto_start:
            self.transcriber.start()

    def on_stop(self):
        # stop transcriber gracefully
        try:
            self.transcriber.stop()
        except Exception:
            pass