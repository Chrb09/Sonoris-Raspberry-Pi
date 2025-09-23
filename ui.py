# ui.py
import json
import os
import time
import sys   
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty, ListProperty, NumericProperty

from transcriber import Transcriber

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# util: carrega cor de várias formas
def _clamp(v, lo=0.0, hi=1.0):
    try:
        fv = float(v)
    except Exception:
        return lo
    return max(lo, min(hi, fv))

def parse_color(raw, default=(0,0,0,1)):
    if raw is None:
        return default
    # hex string
    if isinstance(raw, str):
        s = raw.strip().lstrip('#')
        if len(s) == 6:
            try:
                r = int(s[0:2], 16)/255.0
                g = int(s[2:4], 16)/255.0
                b = int(s[4:6], 16)/255.0
                return (r, g, b, 1.0)
            except Exception:
                return default
        if len(s) == 8:
            try:
                r = int(s[0:2], 16)/255.0
                g = int(s[2:4], 16)/255.0
                b = int(s[4:6], 16)/255.0
                a = int(s[6:8], 16)/255.0
                return (r, g, b, a)
            except Exception:
                return default
        return default

    # list/tuple
    if isinstance(raw, (list, tuple)):
        vals = list(raw)
        if len(vals) == 3:
            vals.append(1)
        out = []
        for v in vals[:4]:
            try:
                fv = float(v)
            except Exception:
                fv = 0.0
            if fv > 1.0:
                fv = fv / 255.0
            out.append(_clamp(fv))
        while len(out) < 4:
            out.append(1.0)
        return tuple(out)

    return default

# configurações de UI (config.json)
FONT_NAME = cfg.get("fonte", None)
FONT_SIZE_PARTIAL = cfg.get("tamanho_parcial", 28)
FONT_SIZE_HISTORY = cfg.get("tamanho_historico", 20)
BACKGROUND_COLOR = parse_color(cfg.get("color_background500", None), default=(0,0,0,1))
TEXT_COLOR = parse_color(cfg.get("color_white", None), default=(1,1,1,1))
MAX_PARTIAL_CHARS = int(cfg.get("max_partial_chars", 240))
PARTIAL_UPDATE_MIN_MS = int(cfg.get("partial_update_min_ms", 80))
HISTORY_MAX_LINES = int(cfg.get("history_max_lines", 200))
PARTIAL_RESET_MS = int(cfg.get("partial_reset_ms", 3000))

# configurações globais do kivy

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

Window.clearcolor = BACKGROUND_COLOR

# limita tamanho do texto parcial
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

# botão com ícone e rótulo
class IconButton(ButtonBehavior, BoxLayout):
    """
    Botão composto: ícone em cima + rótulo embaixo.
    Propriedades úteis:
      - icon_src (str): caminho da imagem do ícone
      - text (str): rótulo abaixo do ícone
      - bg_color (list): cor de fundo normal [r,g,b,a] (0..1)
      - bg_color_down (list): cor de fundo quando pressionado
      - font_size (num): tamanho do rótulo
      - name (str): identificador arbitrário para seu uso
    """
    icon_src = StringProperty('') # caminho da imagem do ícone
    text = StringProperty('') # rótulo abaixo do ícone
    bg_color = ListProperty([0, 0, 0, 0])         # padrão transparente
    bg_color_down = ListProperty([0, 0, 0, 0.08]) # leve feedback
    font_size = NumericProperty(12) # tamanho do rótulo
    name = StringProperty('') 

    # construtor
    def __init__(self, icon_src='', text='', size=(72, 72), **kwargs):
        super().__init__(orientation='vertical', size_hint=(None, None), **kwargs)
        self.size = size
        self.icon_src = icon_src
        self.text = text

        # desenha fundo com RoundedRectangle (podemos trocar por Rectangle)
        with self.canvas.before:
            self._bg_color_instr = Color(*self.bg_color)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

        # widgets internos
        # imagem
        self._image = Image(source=self.icon_src, size_hint=(1, 0.66),
                            allow_stretch=True, keep_ratio=True)
        # label (rótulo)
        self._label = Label(text=self.text, size_hint=(1, 0.34),
                            font_size=self.font_size, halign='center', valign='middle')
        self._label.bind(size=lambda inst, val: inst.setter('text_size')(inst, val))

        # aplica fonte global se existir (se você tiver FONT_NAME)
        try:
            from kivy.core.text import LabelBase
            # se já registrou FONT_NAME em outro lugar, a variável global pode existir
            if 'FONT_NAME' in globals() and globals().get('FONT_NAME'):
                self._label.font_name = globals().get('FONT_NAME')
        except Exception:
            pass

        self.add_widget(self._image)
        self.add_widget(self._label)

        # binds para atualizar rect quando mover/trocar tamanho e quando mudar cores
        self.bind(pos=self._update_rect, size=self._update_rect,
                  bg_color=self._update_bg, bg_color_down=self._update_bg)

    def _update_rect(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _update_bg(self, *args):
        # por padrão usa bg_color; quando pressionado, on_press muda instrucao
        self._bg_color_instr.rgba = self.bg_color

    # feedback visual: altera cor ao pressionar
    def on_press(self):
        self._bg_color_instr.rgba = self.bg_color_down

    def on_release(self):
        # restaura cor normal e propaga evento on_release normal (você pode bindar)
        self._bg_color_instr.rgba = self.bg_color

# ------------------------------
# Widgets e Layouts
# ------------------------------

# widget de histórico (scrollable)
class TranscriptHistory(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        self.lines = []

    # adiciona linha ao histórico, removendo a mais antiga se necessário
    def add_line(self, text):
        lbl = Label(text=text, size_hint_y=None, height=FONT_SIZE_HISTORY*1.6, halign='left', valign='middle',
                    text_size=(self.width, None), font_size=FONT_SIZE_HISTORY, color=TEXT_COLOR)
        lbl.bind(width=lambda inst, w: inst.setter('text_size')(inst, (w, None)))
        self.add_widget(lbl)
        self.lines.append(lbl)
        if len(self.lines) > HISTORY_MAX_LINES:
            old = self.lines.pop(0)
            self.remove_widget(old)

    def clear_all(self):
        for w in list(self.lines):
            try:
                self.remove_widget(w)
            except Exception:
                pass
        self.lines = []

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', padding=8, spacing=6, **kwargs)
        
        toolbar = BoxLayout(size_hint=(1, None), height=40, spacing=10, padding=[6,6,6,6])
        
        # botão texto (manter limpar histórico)
        icons_dir = os.path.join(BASE_DIR, "assets", "icons")
        plus_path = os.path.join(icons_dir, "plus.png")

        # TODO deixar o botão funcional
        # TODO arrumar posição do botão
        
        # botão nova conversa    
        plus_btn = IconButton(icon_src=plus_path, text="Nova conversa", size=(72,84))
        plus_btn.name = "btn_plus"
        plus_btn.bind(on_release=lambda inst: print("clicou", inst.name))
        plus_btn.bind(on_release=self._on_clear_history)
        toolbar.add_widget(plus_btn)

        #
        # espaço flexível
        toolbar.add_widget(Label(text="", size_hint=(1,1)))
        self.add_widget(toolbar)

        # history
        self.scroll = ScrollView(size_hint=(1, 0.65))
        self.history = TranscriptHistory()
        self.scroll.add_widget(self.history)
        self.add_widget(self.scroll)

        # partial label
        self.partial_label = Label(text="Aguardando...", size_hint=(1, 0.25), halign='center', valign='middle',
                                   text_size=(None, None), font_size=FONT_SIZE_PARTIAL, color=TEXT_COLOR)
        self.partial_label.bind(size=self._update_partial_text_size)
        self.add_widget(self.partial_label)

        self._partial_reset_ev = None

        # keep transcriber reference so we can start/stop from UI if needed
        self.transcriber = transcriber

    def _update_partial_text_size(self, inst, val):
        inst.text_size = (inst.width - 20, inst.height)

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

    def _reset_partial(self):
        self._partial_reset_ev = None
        self.partial_label.text = "Aguardando..."

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
        self.title = "Sonoris - Transcrição"
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