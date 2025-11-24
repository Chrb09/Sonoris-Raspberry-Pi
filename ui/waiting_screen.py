"""
Tela de espera de conexão Bluetooth.
Exibe uma mensagem centralizada enquanto aguarda a conexão BLE.
"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.text import LabelBase
import env

class WaitingScreen(BoxLayout):
    """
    Tela simples que exibe mensagem de espera de conexão Bluetooth.
    """
    
    def __init__(self, **kwargs):
        """Inicializa a tela de espera."""
        super().__init__(orientation='vertical', **kwargs)
        
        # Define a cor de fundo (branca)
        with self.canvas.before:
            self.bg_color = Color(1, 1, 1, 1)  # Branco
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        
        # Vincula a atualização do retângulo quando o layout mudar
        self.bind(pos=self._update_bg_rect, size=self._update_bg_rect)
        
        # Cria label centralizado com mensagem de espera
        self.waiting_label = Label(
            text="Carregando...",
            font_size=32,
            font_name=env.FONT_NAME,
            color=(0.2, 0.2, 0.2, 1),  # Cinza escuro
            halign='center',
            valign='middle',
            size_hint=(1, 1)
        )
        
        # Permite quebra de linha no texto
        self.waiting_label.bind(size=self.waiting_label.setter('text_size'))
        
        self.add_widget(self.waiting_label)
    
    def _update_bg_rect(self, *args):
        """Atualiza o retângulo de fundo quando o layout muda de tamanho."""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
    
    def update_message(self, message):
        """
        Atualiza a mensagem exibida na tela.
        
        Args:
            message: Nova mensagem a ser exibida
        """
        self.waiting_label.text = message
