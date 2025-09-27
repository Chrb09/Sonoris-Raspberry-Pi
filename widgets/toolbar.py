# widgets/toolbar.py
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle

# ------------------------------
# Toolbar
# ------------------------------

# BoxLayout com fundo desenhado com canvas
class Toolbar(BoxLayout):
    def __init__(self, bg_color=(0.168, 0.168, 0.168, 1), **kwargs):
        super().__init__(orientation='horizontal', size_hint=(1, None), padding=10, **kwargs)

        # desenha fundo com RoundedRectangle
        with self.canvas.before:
            self._bg_color_instr = Color(*bg_color) # cor de fundo
            self._bg_rect = Rectangle(pos=self.pos, size=self.size) 

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
