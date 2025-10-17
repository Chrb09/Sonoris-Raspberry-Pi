# ui.py 
import os
import sys

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from transcriber import Transcriber
from kivy.uix.label import Label
from kivy.clock import Clock

from widgets import Toolbar, IconButton, TranscriptHistory
from widgets.transcript_history import FONT_SIZE_HISTORY, MAX_PARTIAL_CHARS, PARTIAL_RESET_MS, FONT_SIZE_PARTIAL
from env import FONT_NAME, TEXT_COLOR, WHITE_COLOR, BLUE_COLOR, icons_dir
from widgets.buttons.common_button import CommonButton
from widgets.buttons.pill_button import PillButton

# TODO otimizar o codigo
# TODO adicionar os widgets
# TODO consertar o erro do parse_color que não está retornando a cor correta

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

        # novo estado de modo privado (persistente enquanto a instância existir)
        self.private_mode = False

        # histórico de transcrição (scrollable)
        history_height = int(FONT_SIZE_HISTORY * 6)
        self.scroll = ScrollView(size_hint=(1, None), height=history_height, do_scroll_x=False, do_scroll_y=True)
        self.history = TranscriptHistory()
        self.scroll.add_widget(self.history)
        self.add_widget(self.scroll)

        # texto parcial
        self.partial_label = Label(text="Aguardando...", size_hint=(1, 1), halign='center', valign='middle', text_size=(None, None), font_size=FONT_SIZE_PARTIAL, color=TEXT_COLOR)
        self.partial_label.bind(size=self._update_partial_text_size)
        self.add_widget(self.partial_label)

        # toolbar
        toolbar = Toolbar(orientation='vertical', bg_color=BLUE_COLOR, height=140, min_height=140, max_height=140)

        self.is_paused = False
        self.pause_icon = os.path.join(icons_dir, "pause.png")
        self.resume_icon = os.path.join(icons_dir, "resume.png")

        # botões na toolbar
        self.pause_btn = IconButton(icon_src=self.pause_icon, text="[b]Pausar[/b]")
        self.pause_btn.name = "btn_pause"
        self.response_btn = IconButton(icon_src=os.path.join(icons_dir, "response.png"), text='[b]Respostas[/b]')
        # cria private_btn com aparência baseada em self.private_mode
        init_private_icon = os.path.join(icons_dir, "private02.png") if self.private_mode else os.path.join(icons_dir, "private01.png")
        init_private_text = "[b]Privado[/b]" if self.private_mode else "[b]Privado?[/b]"
        self.private_btn = IconButton(icon_src=init_private_icon, text=init_private_text)

        # eventos dos botões
        self.pause_btn.bind(on_release=self._update_pause_state)
        self.response_btn.bind(on_release=self._show_categories)
        # somente liga o handler de popup se o modo privado não estiver ativo
        if not self.private_mode:
            self.private_btn.bind(on_release=self.show_private_popup)
        else:
            try:
                self.private_btn.disabled = True
                self.private_btn.opacity = 0.8
            except Exception:
                pass

        button_group = BoxLayout(orientation='horizontal', spacing=40, size_hint=(None, None))
        self.button_group = button_group

        button_group.height = max(
            getattr(self.response_btn, "height", 60),
            getattr(self.private_btn, "height", 60),
            getattr(self.pause_btn, "height", 60)
        )
        button_group.width = 300 # largura fixa inicial
        # guarda largura original para poder restaurar depois (usado por _restore_original)
        self._original_button_group_width = button_group.width

        # adiciona botões ao grupo
        button_group.add_widget(self.pause_btn)
        button_group.add_widget(self.response_btn)
        button_group.add_widget(self.private_btn)

        # centraliza o grupo
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        anchor.add_widget(button_group)
        toolbar.add_widget(anchor)

        self.add_widget(toolbar)
        # toolbar.bind(height=self.on_toolbar_resize)

        # salva a ordem original left->right para uso por outras funções
        try:
            # children está invertido (visual left->right = reversed(children))
            self._original_button_order = list(reversed(list(self.button_group.children)))
        except Exception:
            # fallback: compoe manualmente
            order = []
            for name in ("plus_btn", "pause_btn", "response_btn", "private_btn"):
                if hasattr(self, name):
                    order.append(getattr(self, name))
            self._original_button_order = order

        # estado para esconder/mostrar
        self._hidden_buttons = []
        self._buttons_hidden = False

        # aplica aparência correta ao private_btn (caso tenha sido alterado antes)
        try:
            self._apply_private_mode_to_btn()
        except Exception:
            pass

    # novo: aplica ícone/texto de acordo com self.private_mode
    def _apply_private_mode_to_btn(self):
        try:
            btn = getattr(self, "private_btn", None)
            if not btn:
                 return
             # decide valores
            if getattr(self, "private_mode", False):
                 icon = os.path.join(icons_dir, "private02.png")
                 txt = "[b]Privado[/b]"
            else:
                 icon = os.path.join(icons_dir, "private01.png")
                 txt = "[b]Privado?[/b]"


            # aplica no widget principal (IconButton)
            try:
                 btn.icon_src = icon
            except Exception:
                 pass
            try:
                 btn.text = txt
            except Exception:
                 pass
             # força markup se suportado
            try:
                 btn.markup = True
            except Exception:
                 pass

            # ativa/desativa interação (quando privado = True, desabilita clique)
            try:
                disabled = bool(getattr(self, "private_mode", False))
                btn.disabled = disabled
                # pequena alteração visual quando desabilitado
                btn.opacity = 0.8 if disabled else 1.0
            except Exception:
                pass

             # atualiza qualquer Label filho (caso o IconButton use um Label interno)
            try:
                for child in getattr(btn, "children", []):
                    try:
                        if isinstance(child, Label):
                            child.text = txt
                            try:
                                child.markup = True
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

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

    def enable_private_and_close(self, context_self):
        print ("Ativando modo privado e fechando popup")
        # ativa modo privado
        try:
            context_self.private_mode = True
        except Exception as e:
            print("Erro ao ativar private_mode:", e)

        # atualiza ícone do botão private_btn para private02.png
        try:
            context_self._apply_private_mode_to_btn()
        except Exception as e:
            # fallback direto: atualiza icon e texto no botão e em labels filhos
            try:
                btn = getattr(context_self, 'private_btn', None)
                if btn:
                    try:
                        btn.icon_src = os.path.join(icons_dir, "private02.png")
                    except Exception:
                        pass
                    try:
                        btn.text = "[b]Privado[/b]"
                    except Exception:
                        pass
                    try:
                        btn.markup = True
                    except Exception:
                        pass
                    try:
                        btn.disabled = True
                        btn.opacity = 0.8
                    except Exception:
                        pass
                    try:
                        for child in getattr(btn, "children", []):
                            try:
                                if isinstance(child, Label):
                                    child.text = "[b]Privado[/b]"
                                    try:
                                        child.markup = True
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                print("Erro ao atualizar o private_btn:", e)

        # fecha popup
        try:
            context_self.popup.dismiss()
        except Exception as e:
            print("Erro ao fechar popup:", e)

    def show_private_popup(self, instance):
        # não faz nada se o modo privado já estiver ativo (botão deve estar desativado)
        if getattr(self, "private_mode", False):
            return
        print("Clicou no private_btn - mostrar popup de privacidade")

        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        box = BoxLayout(orientation='vertical', padding=(24, 20), spacing=15)
        box.width = min(dp(680), Window.width * 0.95)
        box.height = dp(300)  # altura inicial

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
        confirm_btn.bind(on_release=lambda *_: self.enable_private_and_close(self))
        negative_btn.bind(on_release=lambda *_: self.popup.dismiss())

        popup.open()
    
    # mostra categorias de resposta rápidas
    def _show_categories(self, instance):
        print("Clicou no response_btn - mostrar categorias de resposta")
        # mapa de categorias -> lista de respostas rápidas (editar/expandir conforme necessário)
        QUICK_REPLIES = {
            "Positiva": [
                "Excelente!", "Muito bom!", "Aprovado.", "Perfeito, obrigado."
            ],
            "Negativa": [
                "Não atende.", "Rejeitado.", "Problema grave.", "Rever por favor."
            ],
            "Neutras": [
                "Notado.", "Ok.", "Recebido.", "Sem alterações."
            ],
            "Perguntas": [
                "Pode explicar mais?", "Qual o prazo?", "Quem será responsável?", "Onde encontro isso?"
            ]
        }
        categories = list(QUICK_REPLIES.keys())
 
        local_original = getattr(self, "_original_button_order", None)
        if not local_original:
            # fallback: calcula localmente sem atribuir a self._original_button_order
            local_original = list(reversed(list(self.button_group.children)))
 
        # salva state atual para restaurar depois
        try:
            self._saved_button_group_size_hint = tuple(self.button_group.size_hint)
        except Exception:
            self._saved_button_group_size_hint = getattr(self, "_original_button_group_size_hint", None)
        try:
            self._saved_button_group_width = getattr(self.button_group, "width", None)
        except Exception:
            self._saved_button_group_width = None

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

        try:
            self.button_group.spacing = 15
        except Exception:
            pass

        # força alinhamento à esquerda: altera o AnchorLayout pai do button_group
        parent_anchor = getattr(self.button_group, "parent", None)
        try:
            if parent_anchor and hasattr(parent_anchor, "anchor_x"):
                parent_anchor.anchor_x = "left"
        except Exception:
            pass

        back_btn = IconButton(icon_src=os.path.join(icons_dir, "back.png"), text='[b]Voltar[/b]')
        try:
            back_btn.size_hint_x = None
            back_btn.width = dp(100)
        except Exception:
            pass
        # controla view atual (categories | replies). Usamos dict para closure mutável.
        current_view = {"view": None}

        # ação única do botão "Voltar": decide para onde ir dependendo da view atual
        def back_action(*_args):
            try:
                if current_view.get("view") == "replies":
                    show_categories_view()
                else:
                    _restore_original()
            except Exception:
                try:
                    _restore_original()
                except Exception:
                    pass

        # bind único do botão voltar
        try:
            back_btn.bind(on_release=back_action)
        except Exception:
            pass
        
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
            for w in getattr(self, "_original_button_order", local_original):
                try:
                    if w not in self.button_group.children:
                        self.button_group.add_widget(w)
                except Exception:
                    try:
                        from kivy.uix.button import Button
                        self.button_group.add_widget(Button(text="??"))
                    except Exception:
                        pass

            # restaura alinhamento do AnchorLayout pai para centralizado
            try:
                if parent_anchor and hasattr(parent_anchor, "anchor_x"):
                    parent_anchor.anchor_x = "center"
            except Exception:
                pass

            # restaura largura/altura do grupo de botões para centralização original
            try:
                # restaura size_hint e width salvos
                if hasattr(self, "_saved_button_group_size_hint") and self._saved_button_group_size_hint is not None:
                    self.button_group.size_hint = self._saved_button_group_size_hint
                else:
                    self.button_group.size_hint = (None, None)
                if getattr(self, "_saved_button_group_width", None) is not None:
                    self.button_group.width = self._saved_button_group_width
                else:
                    self.button_group.width = getattr(self, "_original_button_group_width", self.button_group.width)
                self.button_group.spacing = 40
            except Exception:
                pass

            # aplica aparência do private_btn após restaurar widgets (mantém persistência)
            try:
                self._apply_private_mode_to_btn()
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
        # --- nova lógica: colocar as categorias dentro de um ScrollView horizontal ---
        try:
            # expandir button_group para ocupar espaço restante (preencher até a outra borda)
            try:
                self.button_group.size_hint = (1, None)
                # usa largura do pai como referência, fallback para Window.width
                target_width = getattr(parent_anchor, "width", None) or Window.width
                self.button_group.width = target_width
            except Exception:
                pass

            # ScrollView que ocupará o espaço restante da button_group
            cat_scroll = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint=(1, None), height=self.button_group.height)
            # BoxLayout interno com largura dinâmica (size_hint_x=None) para permitir rolagem
            inner = BoxLayout(orientation='horizontal', size_hint_x=None, height=self.button_group.height, spacing=10)
            # manter a largura do inner igual ao mínimo necessário (soma das larguras dos filhos)
            try:
                inner.bind(minimum_width=inner.setter('width'))
            except Exception:
                # fallback simples: não faz bind se propriedade não existir
                pass

            cat_scroll.add_widget(inner)

            # adiciona o ScrollView ao grupo (depois do back_btn)
            try:
                self.button_group.add_widget(cat_scroll)
            except Exception:
                try:
                    self.button_group.add_widget(cat_scroll)
                except Exception:
                    pass
        except Exception as e:
            print("Erro ao criar scroll para categorias:", e)

        # local functions to swap views
        def show_categories_view(*_args):
            # popula 'inner' com botões de categoria
            try:
                # limpa filhos do inner
                for c in list(inner.children):
                    try:
                        inner.remove_widget(c)
                    except Exception:
                        pass
            except Exception:
                pass

            # marca view atual
            try:
                current_view["view"] = "categories"
            except Exception:
                pass

             # cria botões de categoria
            for categoryname in categories:
                resp_list = QUICK_REPLIES.get(categoryname, [])
                try:
                    btn = PillButton(text=f"{categoryname}", pos_hint={'center_y': 0.5})
                    btn.size_hint_x = None
                    btn.width = dp(140)
                except Exception:
                    btn = PillButton(text=f"{categoryname}")
                # armazena respostas no botão (opcional)
                try:
                    btn.responses = list(resp_list)
                except Exception:
                    pass
                # ao clicar abre view de respostas da categoria
                try:
                    btn.bind(on_release=lambda inst, c=categoryname, r=resp_list: show_replies_view(c, r))
                except Exception:
                    btn.bind(on_release=lambda inst, c=categoryname, r=resp_list: print("abrir respostas para", c))
                try:
                    inner.add_widget(btn)
                except Exception:
                    try:
                        inner.add_widget(btn)
                    except Exception:
                        pass

        def show_replies_view(categoryname, resp_list):
            # popula 'inner' com botões de respostas rápidas para a categoria selecionada
            try:
                for c in list(inner.children):
                    try:
                        inner.remove_widget(c)
                    except Exception:
                        pass
            except Exception:
                pass

            # marca view atual
            try:
                current_view["view"] = "replies"
            except Exception:
                pass

            # se não houver respostas, mostra uma mensagem simples (botão desabilitado)
            if not resp_list:
                try:
                    empty = PillButton(text="(Sem respostas)", size_hint_x=None, width=dp(220))
                    empty.disabled = True
                    inner.add_widget(empty)
                except Exception:
                    pass
                return

            for reply in resp_list:
                try:
                    rbtn = PillButton(text=reply, pos_hint={'center_y': 0.5})
                    rbtn.size_hint_x = None
                    rbtn.width = dp(220)
                except Exception:
                    rbtn = PillButton(text=reply)
                # bind: chama handler de seleção de quick reply, passando categoria e resposta
                if hasattr(self, "_on_quick_reply_selected"):
                    rbtn.bind(on_release=lambda inst, c=categoryname, r=reply: self._on_quick_reply_selected(c, r))
                elif hasattr(self, "handle_quick_reply"):
                    rbtn.bind(on_release=lambda inst, c=categoryname, r=reply: self.handle_quick_reply(c, r))
                else:
                    rbtn.bind(on_release=lambda inst, c=categoryname, r=reply: print("clicou na resposta", r, "da categoria", c))
                try:
                    inner.add_widget(rbtn)
                except Exception:
                    try:
                        inner.add_widget(rbtn)
                    except Exception:
                        pass

        # inicialmente mostra as categorias
        try:
            show_categories_view()
        except Exception as e:
            print("Erro ao mostrar categorias inicialmente:", e)
    
    # botão de toggle pausar/retomar 
    def _update_pause_state(self, instance):
        # nova abordagem: ao pausar, mostramos um layout de "pausa" com um botão de "Retomar"
        # que usa _restore_original para restaurar a toolbar original (mesma lógica de _show_categories).
        local_original = getattr(self, "_original_button_order", None)
        if not local_original:
            local_original = list(reversed(list(self.button_group.children)))

        # salva as instâncias removidas para referência (left->right)
        try:
            current_children = list(self.button_group.children)
        except Exception:
            current_children = []
        self._hidden_buttons = list(reversed(current_children))

        # função que restaura a toolbar original (reutiliza padrão de _show_categories)
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
            for w in getattr(self, "_original_button_order", local_original):
                try:
                    if w not in self.button_group.children:
                        self.button_group.add_widget(w)
                except Exception:
                    try:
                        from kivy.uix.button import Button
                        self.button_group.add_widget(Button(text="??"))
                    except Exception:
                        pass

            # atualiza estado e tenta reiniciar o transcriber
            try:
                if getattr(self, "transcriber", None):
                    self.transcriber.start()
            except Exception as e:
                print("Erro ao iniciar transcriber ao restaurar:", e)

            self.is_paused = False

            # assegura que pause_btn referencia o botão atual (se existir na toolbar original)
            try:
                for w in self._original_button_order:
                    if getattr(w, "name", "") == "btn_pause" or w is getattr(self, "pause_btn", None):
                        self.pause_btn = w
                        break
            except Exception:
                pass

            # restaura largura do button_group para centralizar novamente
            try:
                self.button_group.width = getattr(self, "_original_button_group_width", self.button_group.width)
            except Exception:
                pass

            # --- restaura partial_label ao sair da pausa (se salvamos) ---
            try:
                if hasattr(self, "_saved_partial_props") and self._saved_partial_props:
                    size_hint, height, opacity = self._saved_partial_props
                    try:
                        self.partial_label.size_hint = size_hint
                    except Exception:
                        pass
                    try:
                        if height is not None:
                            self.partial_label.height = height
                    except Exception:
                        pass
                    try:
                        self.partial_label.opacity = opacity if opacity is not None else 1
                    except Exception:
                        pass
                    # limpa o saved state
                    self._saved_partial_props = None
            except Exception:
                pass

            # --- restaura scroll/history ao sair da pausa (se salvamos) ---
            try:
                if hasattr(self, "_saved_scroll_props") and self._saved_scroll_props:
                    s_size_hint, s_height = self._saved_scroll_props
                    try:
                        self.scroll.size_hint = s_size_hint
                    except Exception:
                        pass
                    try:
                        if s_height is not None:
                            self.scroll.height = s_height
                    except Exception:
                        pass
                    self._saved_scroll_props = None
            except Exception:
                pass

            # aplica aparência do private_btn após restaurar widgets (mantém persistência)
            try:
                self._apply_private_mode_to_btn()
            except Exception:
                pass

        # Se já estamos pausados, apenas restaurar
        if getattr(self, "is_paused", False):
            _restore_original()
            return

        # entrar em estado pausado
        print("pausado")
        try:
            if self.transcriber:
                self.transcriber.stop()
        except Exception as e:
            print("Erro ao pausar transcriber:", e)

        # --- salva e oculta partial_label para que desapareça na pausa ---
        try:
            # salva (size_hint, height, opacity)
            try:
                saved_size_hint = tuple(self.partial_label.size_hint)
            except Exception:
                saved_size_hint = getattr(self.partial_label, "size_hint", (1, 1))
            try:
                saved_height = getattr(self.partial_label, "height", None)
            except Exception:
                saved_height = None
            try:
                saved_opacity = getattr(self.partial_label, "opacity", 1)
            except Exception:
                saved_opacity = 1
            self._saved_partial_props = (saved_size_hint, saved_height, saved_opacity)

            # --- salva também propriedades do history ScrollView para restaurar depois ---
            try:
                saved_scroll_size_hint = tuple(self.scroll.size_hint)
            except Exception:
                saved_scroll_size_hint = getattr(self.scroll, "size_hint", (1, None))
            try:
                saved_scroll_height = getattr(self.scroll, "height", None)
            except Exception:
                saved_scroll_height = None
            self._saved_scroll_props = (saved_scroll_size_hint, saved_scroll_height)

            # oculta partial_label sem deixar espaço: size_hint_y=None e height=0, opacity=0
            try:
                self.partial_label.size_hint = (1, None)
            except Exception:
                pass
            try:
                self.partial_label.height = 0
            except Exception:
                pass
            try:
                self.partial_label.opacity = 0
            except Exception:
                pass

            # faz o history ScrollView ocupar o espaço restante (expandir verticalmente)
            try:
                self.scroll.size_hint = (1, 1)
                # limpa height override para permitir size_hint tomar efeito (se possível)
                try:
                    self.scroll.height = None
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass

        # limpa a toolbar atual
        try:
            self.button_group.clear_widgets()
        except Exception:
            for ch in current_children:
                try:
                    self.button_group.remove_widget(ch)
                except Exception:
                    pass

        # cria botão de 'Retomar' que usa _restore_original
        resume_btn = IconButton(icon_src=self.resume_icon, text="[b]Retomar[/b]")
        try:
            resume_btn.bind(on_release=lambda *_: _restore_original())
        except Exception:
            pass

        # cria botão 'Nova conversa' e associa limpar histórico
        try:
            plus_btn = IconButton(icon_src=os.path.join(icons_dir, "plus.png"), text="[b]Nova conversa[/b]")
            plus_btn.name = "plus_btn"
            # ao clicar, chama _on_clear_history, desativa modo privado e depois restaura a toolbar original
            plus_btn.bind(on_release=lambda inst: (self._on_clear_history(inst), self._disable_private_mode(), _restore_original()))
            # guarda referência para possível uso futuro
            self.plus_btn = plus_btn
        except Exception:
            plus_btn = None

        # adiciona resume_btn e plus_btn (se criado) à toolbar de pausa
        try:
            self.button_group.add_widget(resume_btn)
            if plus_btn:
                self.button_group.add_widget(plus_btn)
        except Exception:
            try:
                self.button_group.add_widget(resume_btn)
            except Exception:
                pass

        # Ajusta a largura do grupo para centralizar os dois botões (resume + opcional plus)
        try:
            new_children = [w for w in (resume_btn, plus_btn) if w is not None]
            # largura padrão caso o widget ainda não tenha largura definida
            default_btn_w = dp(100)
            spacing = getattr(self.button_group, "spacing", 40) or 0
            width_sum = 0
            max_h = 0
            for b in new_children:
                bw = getattr(b, "width", None) or default_btn_w
                bh = getattr(b, "height", None) or self.button_group.height
                width_sum += bw
                if bh and bh > max_h:
                    max_h = bh
            n = len(new_children) or 1
            self.button_group.width = int(width_sum + spacing * (n - 1))
            if max_h:
                self.button_group.height = max_h
        except Exception:
            # fallback: mantém a largura original
            try:
                self.button_group.width = getattr(self, "_original_button_group_width", self.button_group.width)
            except Exception:
                pass

        # marca estado pausado
        self.is_paused = True

        # atualiza referência do pause_btn para o novo botão de resume (mantém consistência)
        self.pause_btn = resume_btn
    
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
    
    # desativa o modo privado e restaura o botão private_btn ao estado inicial
    def _disable_private_mode(self):
        try:
            self.private_mode = False
        except Exception:
            pass
        # aplica aparência padrão (icon/text/disabled/opacidade)
        try:
            self._apply_private_mode_to_btn()
        except Exception:
            pass

        # garante que o botão esteja habilitado e com o handler correto
        try:
            btn = getattr(self, "private_btn", None)
            if btn:
                try:
                    btn.disabled = False
                except Exception:
                    pass
                try:
                    btn.opacity = 1.0
                except Exception:
                    pass
                # remove binding antiga (se existir) e rebinda ao handler de popup
                try:
                    btn.unbind(on_release=self.show_private_popup)
                except Exception:
                    pass
                try:
                    btn.bind(on_release=self.show_private_popup)
                except Exception:
                    pass
        except Exception:
            pass

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
        self.icon = os.path.join(icons_dir, "app_icon.png")
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
