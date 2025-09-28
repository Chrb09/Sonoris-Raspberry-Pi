# widgets/icon_button.py
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.graphics import Color, RoundedRectangle

# ------------------------------
# IconButton
# ------------------------------

# botão com ícone e rótulo
class IconButton(ButtonBehavior, BoxLayout):
    text = StringProperty('') # rótulo abaixo do ícone
    font_size = NumericProperty(20) # tamanho do rótulo
    # name = StringProperty(text) 

    icon_src = StringProperty('') # caminho da imagem do ícone
    bg_color = ListProperty([1,1,1,1]) 
    bg_color_down = ListProperty([1,1,1,0.8]) # leve feedback

    collapsed = BooleanProperty(False)

    def __init__(self, icon_src='', text='', **kwargs):
        super().__init__(orientation='vertical', size_hint=(None, None), **kwargs)
        self.icon_src = icon_src
        self._original_text = text  # salva o texto original
        self.collapsed = False

        # desenha fundo com RoundedRectangle
        with self.canvas.before:
            self.size = (54, 54)
            self._color_instr = Color(*self.bg_color)
            self._rect = RoundedRectangle(source=self.icon_src, pos=self.pos)

        # imagem
        # self._image = Image(source=self.icon_src, size_hint=(1, 1), allow_stretch=True, keep_ratio=True)
        # self._image_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        
        # label (rótulo)
        self._label = Label(text=self._original_text, size_hint=(1, 1),
                            font_size=self.font_size, markup=True,
                            halign='center', valign='middle')
        self._label.bind(size=lambda inst, val: inst.setter('text_size')(inst, val))

        # self.add_widget(self._image)
        self.add_widget(self._label)

        # binds para atualizar rect quando mover/trocar tamanho e quando mudar cores
        self.bind(pos=self._update_rect, size=self._update_rect,
                  collapsed=self.update_state)
        
        # estado inicial
        self.update_state()

    def update_state(self, *args):
        self._label.text = "" if self.collapsed else self._original_text

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    # TODO ao clicar deve mudar a imagem, n o fundo
    def _update_image(self, *args):
        if self.state == 'down':
            self._color_instr.rgba = self.bg_color_down
        else:
            self._color_instr.rgba = self.bg_color

    # feedback visual: altera cor ao pressionar
    def on_press(self):
        self._color_instr.rgba = self.bg_color_down

    # restaura cor ao soltar
    def on_release(self):
        # restaura cor normal e propaga evento on_release normal (você pode bindar)
        self._color_instr.rgba = (1, 1, 1, 1)
