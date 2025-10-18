# widgets/toolbar.py
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.properties import NumericProperty

# ------------------------------
# Toolbar
# ------------------------------

class Toolbar(BoxLayout):
    def __init__(self, bg_color=(0.168, 0.168, 0.168, 1), min_height=None, max_height=None, **kwargs):
        # a toolbar precisa ter size_hint_y=None para podermos controlar height diretamente
        kwargs.setdefault('orientation', 'horizontal')
        kwargs.setdefault('size_hint', (1, None))
        kwargs.setdefault('padding', 10)
        super().__init__(**kwargs)

        # sobrescreve limites se fornecidos
        if min_height is not None:
            self.min_height = min_height
        if max_height is not None:
            self.max_height = max_height

        # desenha fundo com Rectangle
        with self.canvas.before:
            self._bg_color_instr = Color(*bg_color)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
