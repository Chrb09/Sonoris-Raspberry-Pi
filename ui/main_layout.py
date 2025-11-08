"""
Layout principal da aplicação.
Este módulo contém a classe de layout principal que integra todos os componentes.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.graphics import Color, Rectangle

from ui.ui_config import truncate_partial, UI_TEXTS
from ui.toolbar_components import ToolbarManager
from ui.transcript_components import TranscriptionManager
from ui.dialogs import PrivateDialog
from ui.ui_state_manager import UIState
import env

class MainLayout(BoxLayout):
    """
    Layout principal da aplicação.
    Integra todos os componentes da interface.
    """
    
    def __init__(self, transcriber, ble_service_ref=None, **kwargs):
        """
        Inicializa o layout principal.
        
        Args:
            transcriber: Instância do gerenciador de transcrição
            ble_service_ref: Referência ao BLE service para envio de transcrições
            **kwargs: Argumentos adicionais para o BoxLayout
        """
        super().__init__(orientation='vertical', **kwargs)
        
        # Define a cor de fundo
        with self.canvas.before:
            self.bg_color = Color(*env.BACKGROUND_COLOR)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        # Vincula a atualização do retângulo quando o layout mudar de tamanho/posição
        self.bind(pos=self._update_bg_rect, size=self._update_bg_rect)
        
        # Armazena referência ao transcriber
        self.transcriber = transcriber
        self.ble_service_ref = ble_service_ref
        
        # Gerenciador de estado da UI
        self.ui_state = UIState()
        
        # Gerenciador de transcrições
        self.transcription_manager = TranscriptionManager(ui_state=self.ui_state, ble_service_ref=ble_service_ref)
        scroll, partial_scroll = self.transcription_manager.get_components()
        self.scroll = scroll
        self.partial_scroll = partial_scroll
        self.history = self.transcription_manager.history
        
        # Adiciona componentes de transcrição ao layout
        self.add_widget(self.scroll)
        self.add_widget(self.partial_scroll)
        
        # Gerenciador da barra de ferramentas
        self.toolbar_manager = ToolbarManager(self, self.ui_state)
        toolbar = self.toolbar_manager.create_toolbar()
        
        # Botões da toolbar - para acesso conveniente
        self.pause_btn = self.toolbar_manager.pause_btn
        self.private_btn = self.toolbar_manager.private_btn
        
        # Registra eventos para botões da toolbar
        self.toolbar_manager.bind_button_events(
            self._update_pause_state,
            self.show_private_popup
        )
        
        # Adiciona toolbar ao layout
        self.add_widget(toolbar)
        
        # Estados UI salvos (para restaurar após pausa)
        self._saved_partial_props = None
        self._saved_scroll_props = None
    
    def _update_bg_rect(self, *args):
        """Atualiza o retângulo de fundo quando o layout muda de tamanho."""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def set_partial(self, text):
        """
        Atualiza o texto parcial.
        
        Args:
            text: Texto a ser exibido como transcrição parcial
        """
        self.transcription_manager.set_partial(text)
    
    def add_final(self, text):
        """
        Adiciona uma linha finalizada ao histórico e limpa o parcial.
        
        Args:
            text: Texto finalizado a ser adicionado ao histórico
        """
        self.transcription_manager.add_final(text)
    
    def _on_clear_history(self, instance):
        """
        Limpa o histórico de transcrições e reseta o parcial.
        
        Args:
            instance: Instância do widget que disparou o evento
        """
        self.transcription_manager.clear_history()
    
    def _update_pause_state(self, instance):
        """
        Callback para o botão pausar/retomar.
        
        Args:
            instance: Instância do botão que disparou o evento
        """
        # Obtém o parent do button_group como anchor_parent
        anchor_parent = getattr(self.toolbar_manager.button_group, "parent", None)
        
        # Mostra a vista de pausa na toolbar
        self.toolbar_manager.show_pause_view(anchor_parent, self._on_clear_history)
    
    def _show_categories(self, instance):
        """
        Mostra categorias de resposta rápidas.
        
        Args:
            instance: Instância do botão que disparou o evento
        """
        print("Clicou no response_btn - mostrar categorias de resposta")
        
        # Obtém o parent do button_group como anchor_parent
        anchor_parent = getattr(self.toolbar_manager.button_group, "parent", None)
        
        # Mostra a vista de categorias na toolbar
        self.toolbar_manager.show_categories_view(anchor_parent)
    
    def show_private_popup(self, instance):
        """
        Mostra popup de ativação do modo privado.
        
        Args:
            instance: Instância do botão que disparou o evento
        """
        # Não faz nada se o modo privado já estiver ativo
        if self.ui_state.private_mode:
            return
        
        print("Clicou no private_btn - mostrar popup de privacidade")
        
        # Cria e exibe o diálogo de privacidade
        dialog = PrivateDialog(
            on_confirm=self.enable_private_and_close,
            on_dismiss=None
        )
        dialog.show()
        self.private_dialog = dialog
    
    def enable_private_and_close(self):
        """Ativa o modo privado e fecha o popup."""
        print("Ativando modo privado e fechando popup")
        self.transcription_manager.clear_history()
        self.ui_state.enable_private_mode()
    
    def _disable_private_mode(self):
        """Desativa o modo privado."""
        self.ui_state.disable_private_mode()
    
    def _save_ui_state_for_pause(self):
        """Salva o estado dos componentes de UI antes de pausar."""
        saved_state = self.transcription_manager.save_ui_state()
        self._saved_partial_props = saved_state.get('partial')
        self._saved_scroll_props = saved_state.get('scroll')
        
        # Aplica o estado visual de pausa
        self.transcription_manager.apply_paused_state()
    
    def _restore_ui_state_after_pause(self):
        """Restaura o estado dos componentes de UI após despausar."""
        saved_state = {
            'partial': self._saved_partial_props,
            'scroll': self._saved_scroll_props
        }
        self.transcription_manager.restore_ui_state(saved_state)
        
        # Limpa estados salvos
        self._saved_partial_props = None
        self._saved_scroll_props = None