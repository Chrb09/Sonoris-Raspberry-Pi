"""
Gerenciador de estado para a interface do usuário.
Este módulo contém classes para gerenciar os diferentes estados da interface.
"""

class UIState:
    """
    Classe para gerenciar o estado global da interface do usuário.
    Centraliza o controle de modos como pausado e privado.
    """
    
    def __init__(self):
        # Estado inicial
        self.is_paused = False
        self.private_mode = False
        self.observers = []
    
    def register_observer(self, observer):
        """Registra um observador para receber notificações de mudança de estado."""
        if observer not in self.observers:
            self.observers.append(observer)
    
    def unregister_observer(self, observer):
        """Remove um observador da lista de notificações."""
        if observer in self.observers:
            self.observers.remove(observer)
    
    def _notify_observers(self, changed_property, old_value, new_value):
        """Notifica os observadores sobre a mudança de estado."""
        for observer in self.observers:
            if hasattr(observer, 'on_state_changed'):
                observer.on_state_changed(changed_property, old_value, new_value)
    
    @property
    def is_paused(self):
        """Estado de pausa atual."""
        return self._is_paused
    
    @is_paused.setter
    def is_paused(self, value):
        old_value = getattr(self, '_is_paused', False)
        self._is_paused = value
        if old_value != value:
            self._notify_observers('is_paused', old_value, value)
    
    @property
    def private_mode(self):
        """Estado do modo privado atual."""
        return self._private_mode
    
    @private_mode.setter
    def private_mode(self, value):
        old_value = getattr(self, '_private_mode', False)
        self._private_mode = value
        if old_value != value:
            self._notify_observers('private_mode', old_value, value)
    
    def toggle_pause(self):
        """Alterna o estado de pausa."""
        self.is_paused = not self.is_paused
        return self.is_paused
    
    def enable_private_mode(self):
        """Ativa o modo privado."""
        self.private_mode = True
        return True
    
    def disable_private_mode(self):
        """Desativa o modo privado."""
        self.private_mode = False
        return True