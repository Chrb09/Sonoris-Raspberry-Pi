# widgets/divider.py
from kivy.uix.widget import Widget
from kivy.properties import ListProperty, NumericProperty, OptionProperty, ObjectProperty, BooleanProperty
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle

# ------------------------------
# Divider
# ------------------------------

class Divider(Widget):
    orientation = OptionProperty('horizontal') # horizontal - arrasta verticalmente
    thickness = NumericProperty(dp(6)) # espessura do divisor (altura para horizontal, largura para vertical)
    length = NumericProperty(dp(150)) # comprimento do divisor (largura para horizontal, altura para vertical)
    color = ListProperty([1, 1, 1, 1]) # cor do divisor

    target_widget = ObjectProperty(None, allownone=True) # widget que será redimensionado

    # limites de altura aplicados ao target_widget
    min_height = NumericProperty(98)
    max_height = NumericProperty(132)
    dragging = BooleanProperty(False)

    def __init__(self, divider_color=(1,1,1,1), target_widget=None,
                 min_height=98, max_height=132, **kwargs):
        # permite passar size_hint/width/height por kwargs se quiser sobrescrever
        super().__init__(**kwargs)

        self.color = list(divider_color)
        self.target_widget = target_widget
        self.min_height = min_height
        self.max_height = max_height

        # configura tamanho inicial baseado na orientação (horizontal)
        if self.orientation == 'horizontal':
            # width acompanha parent, height fixa (thickness)
            self.size_hint_y = None
            self.height = self.thickness

            # comprimento (largura) definido pela propriedade length
            self.size_hint_x = None
            self.width = self.length

        with self.canvas:
            self._color_instr = Color(*self.color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[5])

        # atualiza retângulo e cor ao mudar propriedades
        self.bind(pos=self._update_rect, size=self._update_rect, color=self._update_color)

        # variáveis para controle de arraste
        self._last_touch_y = None
        self._last_touch_x = None

    # atualiza retângulo
    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    # atualiza cor
    def _update_color(self, *args):
        self._color_instr.rgba = self.color

    # eventos de toque para arrastar o divisor
    def on_touch_down(self, touch):
        if not self.get_root_window():
            return False
        if self.collide_point(*touch.pos):
            # inicia arraste
            self.dragging = True
            self._last_touch_y = touch.y
            self._last_touch_x = touch.x
            # consome o touch para não propagar para widgets abaixo
            return True
        return super().on_touch_down(touch)
    
    # arrasta o divisor
    def on_touch_move(self, touch):
        if not self.dragging:
            return super().on_touch_move(touch)

        # só processa se for o mesmo touch
        if self._last_touch_y is None:
            return True

        dy = touch.y - self._last_touch_y

        # se existe target, altera sua altura (para horizontal)
        if self.orientation == 'horizontal' and self.target_widget is not None:
            new_height = self.target_widget.height + dy
            # clamp entre min e max
            if new_height < self.min_height:
                new_height = self.min_height
            if new_height > self.max_height:
                new_height = self.max_height

            # aplica nova altura
            self.target_widget.height = new_height

            # atualiza última posição
            self._last_touch_y = touch.y

        elif self.orientation == 'vertical' and self.target_widget is not None:
            dx = touch.x - self._last_touch_x
            new_width = self.target_widget.width + dx
            if new_width < self.min_height:  
                new_width = self.min_height
            if new_width > self.max_height:
                new_width = self.max_height
            self.target_widget.width = new_width
            self._last_touch_x = touch.x

        return True
    
    # finaliza arraste
    def on_touch_up(self, touch):
        if self.dragging:
            self.dragging = False
            self._last_touch_y = None
            self._last_touch_x = None
            return True
        return super().on_touch_up(touch)
