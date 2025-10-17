# widgets/icon_button.py
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.graphics import Color, RoundedRectangle
from widgets.image_canvas import ImageCanvas

# ------------------------------
# IconButton
# ------------------------------

# botão com ícone e rótulo
class IconButton(ButtonBehavior, BoxLayout):
    icon_src = StringProperty('') # caminho da imagem do ícone
    text = StringProperty('') # rótulo abaixo do ícone
    font_size = NumericProperty(20) # tamanho do rótulo
    collapsed = BooleanProperty(False)

    img_tint = ListProperty([1,1,1,1]) 
    img_tint_down = ListProperty([1,1,1,0.8]) # leve feedback

    def __init__(self, icon_src='', text='', image_size=(70, 70), label_height=20, radius=10, **kwargs):
        super().__init__(orientation='vertical', size_hint=(None, None), **kwargs)
        self.icon_src = icon_src
        self._original_text = text or '' # salva o texto original
        self.font_size = kwargs.get('font_size', self.font_size)

        # desenha fundo com RoundedRectangle
        img_w, img_h = image_size
        total_w = img_w
        total_h = img_h + label_height
        
        self.size = (total_w, total_h) # tamanho fixo baseado na imagem e label

        # imagem
        self._image_canvas = ImageCanvas(source=self.icon_src, overlay_color=self.img_tint, radius=radius, size_hint=(None, None), size=(img_w, img_h))

        # label (rótulo)
        self._label = Label(text=self._original_text, size_hint=(None, None), size=(img_w, label_height), font_size=self.font_size, markup=True, halign='center', valign='middle')
        self._label.bind(size=lambda inst, val: inst.setter('text_size')(inst, val))

        self.add_widget(self._image_canvas)
        self.add_widget(self._label)

        # garante que o image canvas comece com a fonte correta
        try:
            self._image_canvas.source = self.icon_src
        except Exception:
            pass
        
        # quando icon_src mudar, atualiza a source do image canvas (bind sem criar função nomeada)
        self.bind(icon_src=lambda inst, val: setattr(getattr(self, "_image_canvas", None), "source", val))

        # binds para atualizar rect quando mover/trocar tamanho e quando mudar cores
        self.bind(pos=self._update_children_pos, size=self._update_children_pos,
                  collapsed=self._update_collapsed,
                  img_tint=self._update_image_tint)
        
        # estado inicial
        self._update_collapsed()
        self._update_image_tint()

    def _update_children_pos(self, *args):
        # assegura que image canvas e label estejam alinhados e com tamanhos corretos
        img_w, img_h = self._image_canvas.size
        lbl_w, lbl_h = self._label.size

        # centraliza ambos horizontalmente no IconButton
        # pos_hint não usado; calculamos posições relativas para layout consistente
        # posição do image canvas será (self.x, self.y + label_height)
        label_height = lbl_h
        self._image_canvas.pos = (self.x, self.y + label_height)
        self._label.pos = (self.x, self.y)

    # atualiza estado (colapsado ou não)
    def _update_collapsed(self, *args):
        self._label.text = "" if self.collapsed else self._original_text

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    # feedback visual: altera cor ao pressionar
    def _update_image_tint(self, *args):
        try:
            self._image_canvas.overlay_color = self.img_tint
        except Exception:
            pass

    # feedback visual: altera cor ao pressionar
    def on_press(self):
        self._image_canvas.overlay_color = self.img_tint_down

    # restaura cor ao soltar
    def on_release(self):
        self._image_canvas.overlay_color = self.img_tint