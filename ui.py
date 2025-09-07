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

from transcriber import Transcriber

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# UI config (reads from config.json)
FONT_NAME = cfg.get("fonte", None)
FONT_SIZE_PARTIAL = cfg.get("tamanho_parcial", 28)
FONT_SIZE_HISTORY = cfg.get("tamanho_historico", 20)
BACKGROUND_COLOR = tuple(cfg.get("cor_fundo", [0,0,0,1]))
TEXT_COLOR = tuple(cfg.get("cor_texto", [1,1,1,1]))
MAX_PARTIAL_CHARS = int(cfg.get("max_partial_chars", 240))
PARTIAL_UPDATE_MIN_MS = int(cfg.get("partial_update_min_ms", 80))
HISTORY_MAX_LINES = int(cfg.get("history_max_lines", 200))
PARTIAL_RESET_MS = int(cfg.get("partial_reset_ms", 3000))

if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

Window.clearcolor = BACKGROUND_COLOR

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

class TranscriptHistory(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        self.lines = []

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

class MainLayout(BoxLayout):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(orientation='vertical', padding=8, spacing=6, **kwargs)

        # toolbar
        toolbar = BoxLayout(size_hint=(1, None), height=40, spacing=6)
        btn_clear = Button(text="Limpar histórico", size_hint=(None, 1), width=160)
        btn_clear.bind(on_release=self._on_clear_history)
        toolbar.add_widget(btn_clear)
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

class TranscriberApp(App):
    def __init__(self, transcriber: Transcriber, **kwargs):
        super().__init__(**kwargs)
        self.transcriber = transcriber
        self.layout = None
        self._auto_start = auto_start

    def build(self):
        self.title = "Sonoris - Transcrição"
        self.layout = MainLayout(self.transcriber)
        return self.layout

    def on_start(self):
        # register callbacks (wrap to schedule on UI thread)
        def on_partial(p):
            Clock.schedule_once(lambda dt, p=p: self.layout.set_partial(_truncate_partial(p)))

        def on_final(f):
            Clock.schedule_once(lambda dt, f=f: self.layout.add_final(f))

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
