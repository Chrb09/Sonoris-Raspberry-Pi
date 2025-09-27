# widgets/icon_button.py
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.graphics import Color, RoundedRectangle

# ------------------------------
# IconButton
# ------------------------------

# botão com ícone e rótulo
class IconButton(ButtonBehavior, BoxLayout):
    """
    Botão composto: ícone em cima + rótulo embaixo.
    Propriedades úteis:
      - icon_src (str): caminho da imagem do ícone
      - text (str): rótulo abaixo do ícone
      - bg_color (list): cor de fundo normal [r,g,b,a] (0..1)
      - bg_color_down (list): cor de fundo quando pressionado
      - font_size (num): tamanho do rótulo
      - name (str): identificador arbitrário para seu uso
    """
    icon_src = StringProperty('') # caminho da imagem do ícone
    text = StringProperty('') # rótulo abaixo do ícone
    bg_color = ListProperty([0, 0, 0, 0])         # padrão transparente
    bg_color_down = ListProperty([0, 0, 0, 0.08]) # leve feedback
    font_size = NumericProperty(20) # tamanho do rótulo
    name = StringProperty('') 

    # construtor
    def __init__(self, icon_src='', text='', size=(72, 72), **kwargs):
        super().__init__(orientation='vertical', size_hint=(None, None), **kwargs)
        self.size = size
        self.icon_src = icon_src
        self.text = text

        # desenha fundo com RoundedRectangle
        with self.canvas.before:
            self._bg_color_instr = Color(*self.bg_color)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])

        # widgets internos

        # imagem
        self._image = Image(source=self.icon_src, size_hint=(1, 0.66),
                            allow_stretch=True, keep_ratio=True)
        # label (rótulo)
        self._label = Label(text=self.text, size_hint=(1, 0.34),
                            font_size=self.font_size, markup=True, halign='center', valign='middle')
        self._label.bind(size=lambda inst, val: inst.setter('text_size')(inst, val))

        # fonte global se existir (FONT_NAME)
        try:
            from kivy.core.text import LabelBase
            # se já registrou FONT_NAME em outro lugar, a variável global pode existir
            if 'FONT_NAME' in globals() and globals().get('FONT_NAME'):
                self._label.font_name = globals().get('FONT_NAME')
        except Exception:
            pass

        self.add_widget(self._image)
        self.add_widget(self._label)

        # binds para atualizar rect quando mover/trocar tamanho e quando mudar cores
        self.bind(pos=self._update_rect, size=self._update_rect,
                  bg_color=self._update_bg, bg_color_down=self._update_bg)

    def _update_rect(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    # TODO ao clicar deve mudar a imagem, n o fundo
    
    # atualiza cor de fundo
    def _update_bg(self, *args):
        # por padrão usa bg_color; quando pressionado, on_press muda instrucao
        self._bg_color_instr.rgba = self.bg_color

    # feedback visual: altera cor ao pressionar
    def on_press(self):
        self._bg_color_instr.rgba = self.bg_color_down

    # restaura cor ao soltar
    def on_release(self):
        # restaura cor normal e propaga evento on_release normal (você pode bindar)
        self._bg_color_instr.rgba = self.bg_color
