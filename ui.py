# ui.py 
import os
import sys
import json

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase
from transcriber import Transcriber
from kivy.uix.label import Label
from kivy.clock import Clock

from widgets import Divider, Toolbar, IconButton, TranscriptHistory, toolbar
from widgets.transcript_history import FONT_SIZE_HISTORY, MAX_PARTIAL_CHARS, PARTIAL_RESET_MS, FONT_SIZE_PARTIAL
from utils.colors import parse_color

# TODO deixar o botão funcional
# TODO otimizar o codigo
# TODO melhorar o design
# TODO adicionar todas as imagens dos botões
# TODO adicionar os widgets
# TODO consertar o erro do parse_color que não está retornando a cor correta
# TODO scroll do divider não funciona MUITO BEM na tela lcd

# ------------------------------
# Configurações Globais do Kivy
# ------------------------------

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# configurações de UI (config.json)
FONT_NAME = cfg.get("fonte", None) 
TEXT_COLOR = parse_color(cfg.get("color_black", None), default=(1,1,1,1))
BACKGROUND_COLOR = parse_color(cfg.get("color_background", None), default=(1,1,1,1))
TOOLBAR_COLOR = parse_color(cfg.get("color_blue", None), default=(0.168, 0.168, 0.168, 1))
icons_dir = os.path.join(BASE_DIR, "assets", "icons") # caminho dos ícones

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))

Window.size = (720, 480) # tamanho inicial da janela
# Window.fullscreen = 'auto' # fullscreen automático
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

# função para truncar texto parcial com reticências
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
        
        self._partial_reset_ev = None
        self.transcriber = transcriber # referência o transcriber
        
        # histórico de transcrição (scrollable)
        history_height = int(FONT_SIZE_HISTORY * 4)
        self.scroll = ScrollView(size_hint=(1, None), height=history_height, do_scroll_x=False, do_scroll_y=True)
        self.history = TranscriptHistory()
        self.scroll.add_widget(self.history)
        self.add_widget(self.scroll)

        # texto parcial
        self.partial_label = Label(text="Aguardando...", size_hint=(1, 1), halign='center', valign='middle', text_size=(None, None), font_size=FONT_SIZE_PARTIAL, color=TEXT_COLOR)
        self.partial_label.bind(size=self._update_partial_text_size)
        self.add_widget(self.partial_label)

        # toolbar
        toolbar = Toolbar(orientation='vertical', bg_color=TOOLBAR_COLOR, height=200, min_height=150, max_height=200)
        divider = Divider(orientation='horizontal', divider_color=BACKGROUND_COLOR, target_widget=toolbar, min_height=toolbar.min_height, max_height=toolbar.max_height)

        # adiciona divisor à toolbar
        anchor_div = AnchorLayout(anchor_x='center', anchor_y='center', size_hint=(1, None), height=20) 
        anchor_div.add_widget(divider)
        toolbar.add_widget(anchor_div)

        self.is_paused = False
        self.pause_icon = os.path.join(icons_dir, "pause.png")
        self.resume_icon = os.path.join(icons_dir, "resume.png")

        # botões na toolbar
        # self.plus_btn = IconButton(icon_src=os.path.join(icons_dir, "plus.png"), text='[b]Nova conversa[/b]')
        self.pause_btn = IconButton(icon_src=self.pause_icon, text="[b]Pausar[/b]")
        self.pause_btn.name = "btn_pause"
        self.response_btn = IconButton(icon_src=os.path.join(icons_dir, "response.png"), text='[b]Respostas[/b]')
        self.private_btn = IconButton(icon_src=os.path.join(icons_dir, "private01.png"), text='[b]Privacidade[/b]')
        
        # eventos dos botões
        # self.plus_btn.bind(on_release=lambda inst: print("Clicou no plus_btn"))
        self.pause_btn.bind(on_release=self._update_pause_state)

        button_group = BoxLayout(orientation='horizontal', spacing=40, size_hint=(None, None))
        self.button_group = button_group

        button_group.height = max(
            getattr(self.response_btn, "height", 60),
            getattr(self.private_btn, "height", 60),
            getattr(self.pause_btn, "height", 60)
        )
        button_group.width = 300 # largura fixa inicial

        # adiciona botões ao grupo
        # button_group.add_widget(self.plus_btn)
        button_group.add_widget(self.pause_btn)
        button_group.add_widget(self.response_btn)
        button_group.add_widget(self.private_btn)

        # centraliza o grupo
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        anchor.add_widget(button_group)
        toolbar.add_widget(anchor)

        self.add_widget(toolbar)
        toolbar.bind(height=self.on_toolbar_resize) # bind para ajustar botões ao redimensionar a toolbar

    # botão de toggle pausar/retomar
    def _update_pause_state(self, instance):
        """
        Alterna o estado de pausa:
         - remove apenas o botão pause atual do group,
         - cria um novo pause/resume button e o adiciona no mesmo índice,
         - mantém demais widgets (evita tela branca).
        """

        idx = None # índice do botão na toolbar
        try:
            # children tem ordem invertida (último adicionado é index 0 na lista children),
            if self.pause_btn in self.button_group.children:
                idx = list(self.button_group.children).index(self.pause_btn)
        except Exception:
            idx = None

        # Remove o botão antigo (se existir)
        try:
            self.button_group.remove_widget(self.pause_btn)

            if not hasattr(self, "plus_btn"): # se não tiver o plus_btn, limpa todos os widgets
                self.button_group.clear_widgets()  # limpa todos os widgets para evitar duplicatas
        except Exception:
            pass

        # Alterna estado e cria novo botão 
        if not getattr(self, "is_paused", False):
            # passar para estado pausado
            print("pausado")
            try:
                if self.transcriber:
                    self.transcriber.stop()
            except Exception as e:
                print("Erro ao pausar transcriber:", e)

            # cria novo botão de 'Retomar'
            try:
                new_btn = IconButton(icon_src=self.resume_icon, text="[b]Retomar[/b]")
            except Exception:
                # fallback para Button simples caso IconButton dê problema
                from kivy.uix.button import Button
                new_btn = Button(text="Retomar")

            self.is_paused = True

            if not hasattr(self, "plus_btn") and self.is_paused == True:  # adiciona botão de nova conversa se não existir
                try:
                    self.plus_btn = IconButton(icon_src=os.path.join(icons_dir, "plus.png"), text="[b]Nova conversa[/b]")
                    self.button_group.add_widget(self.plus_btn)
                except Exception:
                    pass

        # passar para estado retomado
        else:
            print("retomar")
            try:
                if self.transcriber:
                    self.transcriber.start()
            except Exception as e:
                print("Erro ao iniciar transcriber:", e)

            # cria novo botão de 'Pausar'
            try:
                new_btn = IconButton(icon_src=self.pause_icon, text="[b]Pausar[/b]")
            except Exception:
                from kivy.uix.button import Button
                new_btn = Button(text="Pausar")

            self.is_paused = False

        # bind do novo botão
        try:
            new_btn.bind(on_release=self._update_pause_state)
        except Exception:
            pass

        # atualiza referência e insere no mesmo lugar no índice
        self.pause_btn = new_btn
        try:
            if idx is not None: # insere no mesmo índice se possível
                self.button_group.add_widget(self.pause_btn, index=idx)
            else:
                self.button_group.add_widget(self.pause_btn)
        except Exception:
            try:
                self.button_group.add_widget(self.pause_btn)
            except Exception:
                pass
    
    # atualiza text_size do label parcial para quebra automática
    def _update_partial_text_size(self, inst, val):
        inst.text_size = (inst.width - 40, inst.height)

    # adiciona linha final ao histórico e limpa o parcial
    def add_final(self, text):
        sanitized = text.strip().capitalize() if text else ""
        if sanitized:
            self.history.add_line(sanitized)
            Clock.schedule_once(lambda dt: self.scroll.scroll_to(self.history.lines[-1]))
        Clock.schedule_once(lambda dt: self.set_partial("Aguardando..."), 0.01) # limpa o parcial após adicionar final
    
    # atualiza o texto parcial
    def set_partial(self, text):
        self.partial_label.text = text
        # reseta o timer se já houver um agendado
        if self._partial_reset_ev:
            try:
                self._partial_reset_ev.cancel()
            except Exception:
                pass
            self._partial_reset_ev = None

        # agenda reset se o texto não for vazio ou "Aguardando..."
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
    
    # inicializa o aplicativo e callbacks do transcriber
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
