import kivy
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, ListProperty
from kivy.graphics import Color, RoundedRectangle

# ------------------------------
# ImageCanvas
# ------------------------------

# Widget que desenha uma imagem (RoundedRectangle) no seu canvas.
# Tem uma 'overlay_color' que tinge a imagem (multiplicador).
class ImageCanvas(Widget):
    source = StringProperty('')
    overlay_color = ListProperty([1, 1, 1, 1])  # cor multiplicadora (1,1,1,1 = original)

    def __init__(self, source='', radius=10, **kwargs):
        super().__init__(**kwargs)
        if source:
            self.source = source
        self._radius = radius

        # desenha no canvas do próprio widget
        with self.canvas:
            self._color = Color(*self.overlay_color)
            self._rect = RoundedRectangle(source=self.source, pos=self.pos, size=self.size, radius=[self._radius])

        # atualiza quando mudar
        self.bind(pos=self._update_rect, size=self._update_rect,
                  source=self._update_source, overlay_color=self._update_color)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _update_source(self, instance, value):
        self._rect.source = value

    def _update_color(self, instance, value):
        self._color.rgba = value