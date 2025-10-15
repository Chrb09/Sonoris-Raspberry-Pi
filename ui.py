# ui.py 
from email.mime import text
import os
import sys
import json
from turtle import title

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.core.text import LabelBase
from transcriber import Transcriber
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle

from widgets import Divider, Toolbar, IconButton, TranscriptHistory, toolbar
from widgets.transcript_history import FONT_SIZE_HISTORY, MAX_PARTIAL_CHARS, PARTIAL_RESET_MS, FONT_SIZE_PARTIAL
from env import FONT_NAME, TEXT_COLOR, WHITE_COLOR, BLUE_COLOR, icons_dir
from widgets.buttons.common_button import CommonButton
from utils.helpers import enable_private_and_close

# TODO deixar o botão funcional
# TODO otimizar o codigo
# TODO melhorar o design
# TODO adicionar todas as imagens dos botões
# TODO adicionar os widgets
# TODO consertar o erro do parse_color que não está retornando a cor correta
# TODO scroll do divider não funciona MUITO BEM na tela lcd

Window.size = (720, 480) # tamanho inicial da janela
# Window.fullscreen = 'auto' # fullscreen automático
Window.clearcolor = WHITE_COLOR

# ------------------------------
# Testes de Configuração
# ------------------------------

print("\nTESTE DE CONFIGURAÇÕES DE UI \n------------------------------")

print("DEBUG: FONT_NAME =", FONT_NAME, type(FONT_NAME)) # teste de fonte
print("DEBUG: BACKGROUND_COLOR =", WHITE_COLOR, type(WHITE_COLOR)) # teste de cor de fundo da janela
print("DEBUG: TOOLBAR_COLOR =", BLUE_COLOR, type(BLUE_COLOR)) # teste de cor da toolbar

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
        toolbar = Toolbar(orientation='vertical', bg_color=BLUE_COLOR, height=200, min_height=150, max_height=200)
        divider = Divider(orientation='horizontal', divider_color=WHITE_COLOR, target_widget=toolbar, min_height=toolbar.min_height, max_height=toolbar.max_height)

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
        self.response_btn.bind(on_release=self._show_categories)
        self.private_btn.bind(on_release=self.show_private_popup)

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
        # toolbar.bind(height=self.on_toolbar_resize) # bind para ajustar botões ao redimensionar a toolbar

        # salva a ordem original left->right para uso por outras funções
        try:
            # children está invertido (visual left->right = reversed(children))
            self._original_button_order = list(reversed(list(self.button_group.children)))
        except Exception:
            # fallback: compor manualmente se necessário
            order = []
            for name in ("plus_btn", "pause_btn", "response_btn", "private_btn"):
                if hasattr(self, name):
                    order.append(getattr(self, name))
            self._original_button_order = order

        # estado para esconder/mostrar
        self._hidden_buttons = []
        self._buttons_hidden = False

    def show_private_popup(self, instance):
        print("Clicou no private_btn - mostrar popup de privacidade")

        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        box = BoxLayout(orientation='vertical', padding=(24, 20), spacing=15)
        box.width = min(dp(680), Window.width * 0.95)
        box.height = dp(300)  # altura inicial, será ajustada depois

        icon = Image(source=os.path.join(icons_dir, "lock.png"), size_hint=(None, None), size=(dp(70), dp(70)), allow_stretch=True, keep_ratio=True)
        icon_anchor = AnchorLayout(size_hint=(1, 1))
        icon_anchor.add_widget(icon)
        box.add_widget(icon_anchor)

        # cria título e subtítulo
        title = Label(text="[b]Deseja ativar o modo privado?[/b]", color=TEXT_COLOR, font_size=40, size_hint=(1, None), halign='center', valign='middle', markup=True)
        title.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        title.bind(texture_size=lambda inst, ts: setattr(inst, "height", ts[1] if ts[1] > 0 else dp(36)))
        box.add_widget(title)

        subtitle = Label(text="As transcrições não serão salvas até você iniciar \n uma nova conversa.", color=TEXT_COLOR, font_size=26, size_hint=(1, None), halign='center', valign='middle', markup=True)
        subtitle.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        subtitle.bind(texture_size=lambda inst, ts: setattr(inst, "height", ts[1] if ts[1] > 0 else dp(28)))
        box.add_widget(subtitle)

        

        # cria botões
        confirm_btn = CommonButton(text="Sim")
        negative_btn = CommonButton(text="Não")

        btn_box = BoxLayout(orientation='horizontal', spacing=15, size_hint=(1, None))
        btn_box.add_widget(confirm_btn)
        btn_box.add_widget(negative_btn)
        box.add_widget(btn_box)

        popup = Popup(
        title='',
        content=anchor,
        size_hint=(1,1),
        auto_dismiss=False,
        separator_height=0,
        background = '',
        background_color = WHITE_COLOR,
        )
        Clock.schedule_once(lambda dt: setattr(
            box,
            "height",
            sum((child.height + box.spacing) for child in box.children)
            + ((box.padding[1] + box.padding[3]) if isinstance(box.padding, (list, tuple)) else (box.padding * 2))
            + 10
        ), 0)
        anchor.add_widget(box)

        self.popup = popup # guarda referência para fechar depois
        confirm_btn.bind(on_release=lambda *_: enable_private_and_close(self))
        negative_btn.bind(on_release=lambda *_: self.popup.dismiss())

        popup.open()
    
    # mostra categorias de resposta rápidas
    def _show_categories(self, instance):
        print("Clicou no response_btn - mostrar categorias de resposta")
        categories = ["Positiva", "Negativa", "Neutras", "Perguntas"]

        local_original = getattr(self, "_original_button_order", None)
        if not local_original:
            # fallback: calcula localmente sem atribuir a self._original_button_order
            local_original = list(reversed(list(self.button_group.children)))

        # limpa a toolbar primeiro
        try:
            current_children = list(self.button_group.children)
        except Exception:
            current_children = []
        # salvamos as instâncias removidas para referência (inverte para left->right se necessário)
        self._hidden_buttons = list(reversed(current_children))
        # limpa
        try:
            self.button_group.clear_widgets()
        except Exception:
            for ch in current_children:
                try:
                    self.button_group.remove_widget(ch)
                except Exception:
                    pass

        back_btn = IconButton(icon_src=os.path.join(icons_dir, "back.png"), text='[b]Voltar[/b]')
        back_btn.bind(on_release=lambda *_: _restore_original())
        
        # restaura a barra original
        def _restore_original(*_args):
            # limpa tudo primeiro
            try:
                self.button_group.clear_widgets()
            except Exception:
                for c in list(self.button_group.children):
                    try:
                        self.button_group.remove_widget(c)
                    except Exception:
                        pass

            # re-adiciona os widgets na ordem original
            for w in self._original_button_order:
                # evita adicionar widgets que foram destruídos
                try:
                    if w not in self.button_group.children:
                        self.button_group.add_widget(w)
                except Exception:
                    # se falhar, tenta adicionar uma nova instância simples (fallback)
                    try:
                        from kivy.uix.button import Button
                        self.button_group.add_widget(Button(text="??"))
                    except Exception:
                        pass

        try:
            self.button_group.add_widget(back_btn)
        except Exception:
            try:
                # se falhar, tenta adicionar sem index
                self.button_group.add_widget(back_btn)
            except Exception:
                pass

        # função para criar botões estilo "pill"
        def PillButton(text, on_release_callback):
            btn = Button(
                text=f"[b]{text}[/b]",
                markup=True,
                size_hint=(None, None),
                height=dp(45),
                background_normal='',  # remove background image para usar background_color
                background_down='',    
                background_color=(0, 0, 0, 0),
                color=BLUE_COLOR,
                font_size=dp(24)
            )
            # desenha o fundo arredondado com a cor TOOLBAR_COLOR
            with btn.canvas.before:
                Color(*WHITE_COLOR)
                btn._rounded_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[dp(25)])
            # atualiza o rounded rect quando o botão mudar de pos/size
            btn.bind(pos=lambda inst, val: setattr(inst._rounded_rect, "pos", inst.pos))
            btn.bind(size=lambda inst, val: setattr(inst._rounded_rect, "size", inst.size))
            btn.bind(texture_size=lambda inst, val: setattr(inst, "width", inst.texture_size[0] + dp(40)))

            btn.bind(on_release=on_release_callback)
            return btn

        # TODO cria e adiciona categorias 
        for categoryname in categories:
            category_btn = PillButton(text=f"[b]{categoryname}[/b]", on_release_callback=lambda *_: print(f"Clicou na categoria {categoryname}"))

            # bind do clique: chama handler se existir
            if hasattr(self, "_on_quick_reply_selected"):
                category_btn.bind(on_release=lambda inst, c=categoryname: self._on_quick_reply_selected(c))
            elif hasattr(self, "handle_quick_reply"):
                category_btn.bind(on_release=lambda inst, c=categoryname: self.handle_quick_reply(c))
            else:
                category_btn.bind(on_release=lambda inst, c=categoryname: print("else clicou na categoria", c))

            try:
                self.button_group.add_widget(category_btn)
            except Exception:
                # fallback simples
                try:
                    self.button_group.add_widget(category_btn)
                except Exception:
                    pass

    
    # botão de toggle pausar/retomar 
    # TODO padronizar com os demais botoes
    def _update_pause_state(self, instance):
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
            new_btn = IconButton(icon_src=self.resume_icon, text="[b]Retomar[/b]")

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
