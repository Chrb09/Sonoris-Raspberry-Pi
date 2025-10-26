"""
Componentes e gerenciamento da barra de ferramentas.
Este módulo contém classes para gerenciar os botões e comportamentos da barra de ferramentas.
"""

import os
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.clock import Clock

from widgets import IconButton, Toolbar
from widgets.buttons.pill_button import PillButton
from ui.ui_config import ICON_PATHS, UI_TEXTS

class ToolbarManager:
    """
    Gerencia os estados e componentes da barra de ferramentas.
    """
    
    def __init__(self, main_layout, ui_state):
        """
        Inicializa o gerenciador de barra de ferramentas.
        
        Args:
            main_layout: Referência ao layout principal
            ui_state: Gerenciador de estado da UI
        """
        self.main_layout = main_layout
        self.ui_state = ui_state
        self.ui_state.register_observer(self)
        
        # Botões da toolbar
        self.pause_btn = IconButton(icon_src=ICON_PATHS['pause'], text=UI_TEXTS['pause_btn'])
        self.pause_btn.name = "btn_pause"
        
        # Cria private_btn com aparência baseada no estado atual
        init_private_icon = ICON_PATHS['private02'] if self.ui_state.private_mode else ICON_PATHS['private01']
        init_private_text = UI_TEXTS['private_active_btn'] if self.ui_state.private_mode else UI_TEXTS['private_inactive_btn']
        self.private_btn = IconButton(icon_src=init_private_icon, text=init_private_text)
        
        # Container para os botões da toolbar
        self.button_group = BoxLayout(orientation='horizontal', spacing=60, size_hint=(None, None))
        
        # Configurações iniciais da toolbar
        self._setup_toolbar()
    
    def _setup_toolbar(self):
        """Configura a barra de ferramentas inicial."""
        # Calcula altura do button_group
        self.button_group.height = max(
            getattr(self.private_btn, "height", 60),
            getattr(self.pause_btn, "height", 60)
        )
        self.button_group.width = 200  # largura fixa inicial
        
        # Guarda largura original para poder restaurar depois
        self._original_button_group_width = self.button_group.width
        
        # Adiciona botões ao grupo
        self.button_group.add_widget(self.pause_btn)
        self.button_group.add_widget(self.private_btn)
        
        # Salva a ordem original left->right para uso por outras funções
        try:
            # children está invertido (visual left->right = reversed(children))
            self._original_button_order = list(reversed(list(self.button_group.children)))
        except Exception:
            # fallback: compoe manualmente
            order = []
            for name in ("plus_btn", "pause_btn", "private_btn"):
                if hasattr(self, name):
                    order.append(getattr(self, name))
            self._original_button_order = order
        
        # Estado para esconder/mostrar
        self._hidden_buttons = []
        self._buttons_hidden = False
        
        # Aplica aparência correta ao private_btn
        self._apply_private_mode_to_btn()
    
    def create_toolbar(self):
        """Cria e retorna o widget Toolbar completo."""
        toolbar = Toolbar(
            orientation='vertical',
            bg_color=(0.231, 0.510, 0.965, 1),  # azul
            height=140,
            min_height=140,
            max_height=140
        )
        
        # Centraliza o grupo de botões
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        anchor.add_widget(self.button_group)
        toolbar.add_widget(anchor)
        
        return toolbar
    
    def bind_button_events(self, pause_callback, private_callback):
        """
        Associa eventos aos botões da barra de ferramentas.
        
        Args:
            pause_callback: Função para o botão de pausar/retomar
            private_callback: Função para o botão de modo privado
        """
        self.pause_btn.bind(on_release=pause_callback)
        # Somente liga o handler de popup se o modo privado não estiver ativo
        if not self.ui_state.private_mode:
            self.private_btn.bind(on_release=private_callback)
        else:
            try:
                self.private_btn.disabled = True
                self.private_btn.opacity = 0.8
            except Exception:
                pass
    
    def _apply_private_mode_to_btn(self):
        """Aplica ícone/texto de acordo com o modo privado."""
        try:
            btn = self.private_btn
            if not btn:
                return
            # Decide valores
            if self.ui_state.private_mode:
                icon = ICON_PATHS['private02']
                txt = UI_TEXTS['private_active_btn']
            else:
                icon = ICON_PATHS['private01']
                txt = UI_TEXTS['private_inactive_btn']

            # Aplica no widget principal (IconButton)
            try:
                btn.icon_src = icon
            except Exception:
                pass
            try:
                btn.text = txt
            except Exception:
                pass
            # Força markup se suportado
            try:
                btn.markup = True
            except Exception:
                pass

            # Ativa/desativa interação (quando privado = True, desabilita clique)
            try:
                disabled = bool(self.ui_state.private_mode)
                btn.disabled = disabled
                # Pequena alteração visual quando desabilitado
                btn.opacity = 0.8 if disabled else 1.0
            except Exception:
                pass
        except Exception:
            pass
    
    def on_state_changed(self, property_name, old_value, new_value):
        """
        Callback para quando o estado da UI muda.
        
        Args:
            property_name: Nome da propriedade alterada
            old_value: Valor anterior
            new_value: Novo valor
        """
        if property_name == 'private_mode':
            self._apply_private_mode_to_btn()
 
    def show_pause_view(self, anchor_parent, on_clear_history=None):
        """
        Mostra a vista de pausa na barra de ferramentas.
        
        Args:
            anchor_parent: Layout pai dos botões
            on_clear_history: Callback para limpar histórico
        """
        local_original = getattr(self, "_original_button_order", None)
        if not local_original:
            local_original = list(reversed(list(self.button_group.children)))

        # Salva as instâncias removidas para referência (left->right)
        try:
            current_children = list(self.button_group.children)
        except Exception:
            current_children = []
        self._hidden_buttons = list(reversed(current_children))

        # Função que restaura a toolbar original
        def _restore_original(*_args):
            # Atualiza estado e tenta reiniciar o transcriber
            try:
                if hasattr(self.main_layout, "transcriber") and self.main_layout.transcriber:
                    self.main_layout.transcriber.start()
            except Exception as e:
                print("Erro ao iniciar transcriber ao restaurar:", e)

            self.ui_state.is_paused = False
            
            # Restaura a toolbar
            self._restore_toolbar(local_original, anchor_parent)
            
            # Assegura que pause_btn referencia o botão atual
            try:
                for w in self._original_button_order:
                    if getattr(w, "name", "") == "btn_pause" or w is getattr(self, "pause_btn", None):
                        self.pause_btn = w
                        break
            except Exception:
                pass
            
            # Restaura partial_label e scroll/history (se houver propriedades salvas)
            self.main_layout._restore_ui_state_after_pause()
            
            return True

        # Se já estamos pausados, apenas restaurar
        if self.ui_state.is_paused:
            _restore_original()
            return _restore_original

        # Entrar em estado pausado
        print("pausado")
        try:
            if hasattr(self.main_layout, "transcriber") and self.main_layout.transcriber:
                self.main_layout.transcriber.stop()
        except Exception as e:
            print("Erro ao pausar transcriber:", e)

        # Salva e oculta partial_label e ajusta história
        self.main_layout._save_ui_state_for_pause()

        # Limpa a toolbar atual
        self._clear_button_group()

        # Cria botão de 'Retomar' que usa _restore_original
        resume_btn = IconButton(icon_src=ICON_PATHS['resume'], text=UI_TEXTS['resume_btn'])
        try:
            resume_btn.bind(on_release=lambda *_: _restore_original())
        except Exception:
            pass

        # Cria botão 'Nova conversa' e associa limpar histórico
        try:
            plus_btn = IconButton(icon_src=ICON_PATHS['plus'], text=UI_TEXTS['new_conversation_btn'])
            plus_btn.name = "plus_btn"
            # Ao clicar, chama _on_clear_history, desativa modo privado e depois restaura a toolbar original
            if callable(on_clear_history):
                plus_btn.bind(on_release=lambda inst: (
                    on_clear_history(inst),
                    self.ui_state.disable_private_mode(),
                    _restore_original()
                ))
            # Guarda referência para possível uso futuro
            self.plus_btn = plus_btn
        except Exception:
            plus_btn = None

        # Adiciona resume_btn e plus_btn à toolbar de pausa
        try:
            self.button_group.add_widget(resume_btn)
            if plus_btn:
                self.button_group.add_widget(plus_btn)
        except Exception:
            try:
                self.button_group.add_widget(resume_btn)
            except Exception:
                pass

        # Ajusta a largura do grupo para centralizar os botões
        self._adjust_paused_button_group(resume_btn, plus_btn)

        # Marca estado pausado
        self.ui_state.is_paused = True

        # Atualiza referência do pause_btn para o novo botão de resume (mantém consistência)
        self.pause_btn = resume_btn
        
        return _restore_original
    
    def _adjust_paused_button_group(self, resume_btn, plus_btn=None):
        """Ajusta a largura do grupo para centralizar os botões na vista de pausa."""
        try:
            new_children = [w for w in (resume_btn, plus_btn) if w is not None]
            # Largura padrão caso o widget ainda não tenha largura definida
            default_btn_w = dp(100)
            spacing = getattr(self.button_group, "spacing", 60) or 0
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
            # Fallback: mantém a largura original
            try:
                self.button_group.width = getattr(self, "_original_button_group_width", self.button_group.width)
            except Exception:
                pass
    
    def _clear_button_group(self):
        """Limpa todos os widgets do button_group."""
        try:
            self.button_group.clear_widgets()
        except Exception:
            for ch in list(self.button_group.children):
                try:
                    self.button_group.remove_widget(ch)
                except Exception:
                    pass
    
    def _restore_toolbar(self, original_order, parent_anchor):
        """
        Restaura a toolbar para seu estado original.
        
        Args:
            original_order: Lista de widgets na ordem original
            parent_anchor: Layout pai para ajustar alinhamento
        """
        # Limpa tudo primeiro
        self._clear_button_group()

        # Re-adiciona os widgets na ordem original
        for w in original_order or self._original_button_order:
            try:
                if w not in self.button_group.children:
                    self.button_group.add_widget(w)
            except Exception:
                try:
                    from kivy.uix.button import Button
                    self.button_group.add_widget(Button(text="??"))
                except Exception:
                    pass

        # Restaura alinhamento do AnchorLayout pai para centralizado
        try:
            if parent_anchor and hasattr(parent_anchor, "anchor_x"):
                parent_anchor.anchor_x = "center"
        except Exception:
            pass

        # Restaura largura/altura do grupo de botões
        try:
            # Restaura size_hint e width salvos
            if hasattr(self, "_saved_button_group_size_hint") and self._saved_button_group_size_hint is not None:
                self.button_group.size_hint = self._saved_button_group_size_hint
            else:
                self.button_group.size_hint = (None, None)
            if getattr(self, "_saved_button_group_width", None) is not None:
                self.button_group.width = self._saved_button_group_width
            else:
                self.button_group.width = getattr(self, "_original_button_group_width", self.button_group.width)
            self.button_group.spacing = 60
        except Exception:
            pass

        # Aplica aparência do private_btn após restaurar widgets
        try:
            self._apply_private_mode_to_btn()
        except Exception:
            pass