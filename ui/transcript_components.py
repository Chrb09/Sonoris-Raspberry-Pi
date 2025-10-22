"""
Componentes relacionados à transcrição e histórico de texto.
Este módulo contém classes e funções para gerenciar a exibição de transcrições.
"""

from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock

from widgets.transcript_history import TranscriptHistory
from widgets.transcript_history import TranscriptHistory, FONT_SIZE_HISTORY, MAX_PARTIAL_CHARS, PARTIAL_RESET_MS, FONT_SIZE_PARTIAL
from ui.ui_config import truncate_partial, UI_TEXTS, TEXT_COLOR

class TranscriptionManager:
    """
    Gerencia a exibição e o histórico de transcrições.
    """
    
    def __init__(self, ui_state=None):
        """Inicializa o gerenciador de transcrições."""
        self._partial_reset_ev = None
        self.ui_state = ui_state
        
        # Cria componentes de UI para transcrição
        self._setup_ui_components()
        
        # Registra como observador do ui_state
        if self.ui_state:
            self.ui_state.register_observer(self)
    
    def _setup_ui_components(self):
        """Configura os componentes de UI para transcrição."""
        # Histórico de transcrição (scrollable)
        history_height = int(FONT_SIZE_HISTORY * 6)
        self.scroll = ScrollView(
            size_hint=(1, None),
            height=history_height,
            do_scroll_x=False,
            do_scroll_y=True
        )
        self.history = TranscriptHistory()
        self.scroll.add_widget(self.history)
        
        # Texto parcial
        self.partial_label = Label(
            text=UI_TEXTS['waiting_text'],
            size_hint=(1, 1),
            halign='center',
            valign='middle',
            text_size=(None, None),
            font_size=FONT_SIZE_PARTIAL,
            color=TEXT_COLOR
        )
        self.partial_label.bind(size=self._update_partial_text_size)
    
    def get_components(self):
        """
        Retorna os componentes de UI para uso no layout principal.
        
        Returns:
            Tupla com (scroll_view, partial_label)
        """
        return self.scroll, self.partial_label
    
    def set_partial(self, text):
        """
        Atualiza o texto parcial.
        
        Args:
            text: Texto a ser exibido como transcrição parcial
        """
        self.partial_label.text = text
        
        # Reseta o timer se já houver um agendado
        if self._partial_reset_ev:
            try:
                self._partial_reset_ev.cancel()
            except Exception:
                pass
            self._partial_reset_ev = None

        # Agenda reset se o texto não for vazio ou "Aguardando..."
        txt = (text or "").strip()
        if txt and txt.lower() != UI_TEXTS['waiting_text'].lower() and PARTIAL_RESET_MS > 0:
            self._partial_reset_ev = Clock.schedule_once(
                lambda dt: self._reset_partial(),
                PARTIAL_RESET_MS / 1000.0
            )
    
    def _reset_partial(self):
        """Limpa o texto parcial e restaura para "Aguardando..."."""
        self._partial_reset_ev = None
        self.partial_label.text = UI_TEXTS['waiting_text']
    
    def add_final(self, text):
        """
        Adiciona uma linha finalizada ao histórico e limpa o parcial.
        
        Args:
            text: Texto finalizado a ser adicionado ao histórico
        """
        sanitized = text.strip().capitalize() if text else ""
        if sanitized:
            self.history.add_line(sanitized)
            Clock.schedule_once(lambda dt: self.scroll.scroll_to(self.history.lines[-1]))
        
        # Limpa o parcial após adicionar final
        Clock.schedule_once(lambda dt: self.set_partial(UI_TEXTS['waiting_text']), 0.01)
    
    def clear_history(self):
        """Limpa o histórico de transcrições e reseta o parcial."""
        self.history.clear_all()
        self._reset_partial()
        
    def on_state_changed(self, property_name, old_value, new_value):
        """Lida com mudanças no estado da UI."""
        if property_name == 'private_mode':
            # Atualiza o modo privado no histórico de transcrição
            if hasattr(self, 'history'):
                self.history.set_private_mode(new_value)
    
    def _update_partial_text_size(self, inst, val):
        """
        Atualiza text_size do label parcial para quebra automática.
        
        Args:
            inst: Instância do widget
            val: Novo valor
        """
        inst.text_size = (inst.width - 40, inst.height)
    
    def save_ui_state(self):
        """
        Salva o estado atual dos componentes de UI (para pausa).
        
        Returns:
            Dicionário com estados salvos dos componentes
        """
        # Salva (size_hint, height, opacity) para o label parcial
        try:
            partial_size_hint = tuple(self.partial_label.size_hint)
        except Exception:
            partial_size_hint = getattr(self.partial_label, "size_hint", (1, 1))
        
        try:
            partial_height = getattr(self.partial_label, "height", None)
        except Exception:
            partial_height = None
        
        try:
            partial_opacity = getattr(self.partial_label, "opacity", 1)
        except Exception:
            partial_opacity = 1
        
        # Salva propriedades do ScrollView
        try:
            scroll_size_hint = tuple(self.scroll.size_hint)
        except Exception:
            scroll_size_hint = getattr(self.scroll, "size_hint", (1, None))
        
        try:
            scroll_height = getattr(self.scroll, "height", None)
        except Exception:
            scroll_height = None
        
        return {
            'partial': {
                'size_hint': partial_size_hint,
                'height': partial_height,
                'opacity': partial_opacity
            },
            'scroll': {
                'size_hint': scroll_size_hint,
                'height': scroll_height
            }
        }
    
    def apply_paused_state(self):
        """
        Aplica o estado visual de pausa nos componentes de UI.
        Oculta o label parcial e expande o histórico.
        """
        # Oculta partial_label sem deixar espaço
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

        # Faz o history ScrollView ocupar o espaço restante
        try:
            self.scroll.size_hint = (1, 1)
            # Limpa height override para permitir size_hint tomar efeito
            try:
                self.scroll.height = None
            except Exception:
                pass
        except Exception:
            pass
    
    def restore_ui_state(self, saved_state):
        """
        Restaura o estado dos componentes de UI a partir de um estado salvo.
        
        Args:
            saved_state: Dicionário com estados salvos (retornado por save_ui_state)
        """
        if not saved_state:
            return
        
        # Restaura partial_label
        if 'partial' in saved_state:
            partial_state = saved_state['partial']
            try:
                self.partial_label.size_hint = partial_state.get('size_hint', (1, 1))
            except Exception:
                pass
            
            try:
                height = partial_state.get('height')
                if height is not None:
                    self.partial_label.height = height
            except Exception:
                pass
            
            try:
                self.partial_label.opacity = partial_state.get('opacity', 1)
            except Exception:
                pass
        
        # Restaura scroll/history
        if 'scroll' in saved_state:
            scroll_state = saved_state['scroll']
            try:
                self.scroll.size_hint = scroll_state.get('size_hint', (1, None))
            except Exception:
                pass
            
            try:
                height = scroll_state.get('height')
                if height is not None:
                    self.scroll.height = height
            except Exception:
                pass