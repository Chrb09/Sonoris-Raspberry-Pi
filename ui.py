# ui.py
import json
import os
import sys
from tokenize import group   
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from widgets import IconButton, Toolbar, TranscriptHistory
from kivy.uix.anchorlayout import AnchorLayout

from transcriber import Transcriber

# TODO deixar o botão funcional
# TODO otimizar o codigo
# TODO melhorar o design

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
TEXT_COLOR = parse_color(cfg.get("color_white100", None), default=(1,1,1,1))
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

# ------------------------------
# Widgets e Layouts
# ------------------------------

# layout principal
class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', padding=0, spacing=6, **kwargs)
        
        toolbar_color = parse_color(cfg.get("color_background300", None), default=(0.14,0.14,0.14,1))
        toolbar = Toolbar(bg_color=toolbar_color, height=132)
        
        # botão texto (manter limpar histórico)
        icons_dir = os.path.join(BASE_DIR, "assets", "icons") # caminho dos ícones
        plus_path = os.path.join(icons_dir, "plus.png")
        resume_path = os.path.join(icons_dir, "resume.png")
        
        # botão nova conversa    
        plus_btn = IconButton(icon_src=plus_path, text="Nova conversa", size=(158,86))
        plus_btn.name = "btn_plus"
        plus_btn.bind(on_release=lambda inst: print("clicou", inst.name))
        plus_btn.bind(on_release=self._on_clear_history)

        # botão retomar conversa
        resume_btn = IconButton(icon_src=resume_path, text="Retomar", size=(158,86))
        resume_btn.name = "btn_resume"
        resume_btn.bind(on_release=lambda inst: print("clicou", inst.name))
        resume_btn.bind(on_release=self._on_clear_history)
        
        group = BoxLayout(orientation='horizontal', size_hint=(None, 1), spacing=16)
        group.add_widget(IconButton(icon_src=plus_path, text="Nova conversa", size=(158,86)))
        group.add_widget(IconButton(icon_src=resume_path, text="Retomar", size=(158,86)))

        # centraliza grupo
        anchor = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(1, 1))
        anchor.add_widget(group)
        toolbar.add_widget(anchor)

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