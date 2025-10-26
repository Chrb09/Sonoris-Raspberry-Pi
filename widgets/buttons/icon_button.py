# widgets/icon_button.py
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.graphics import Color, RoundedRectangle
from widgets.image_canvas import ImageCanvas
from env import FONT_NAME_SEMIBOLD

# ------------------------------
# IconButton
# ------------------------------

# botão com ícone e rótulo
class IconButton(ButtonBehavior, BoxLayout):
    icon_src = StringProperty('') # caminho da imagem do ícone
    text = StringProperty('') # rótulo abaixo do ícone
    font_size = NumericProperty(20) # tamanho do rótulo
    # espaçamento vertical entre o ícone e o rótulo (em pixels)
    label_spacing = NumericProperty(6)

    img_tint = ListProperty([1,1,1,1]) 
    img_tint_down = ListProperty([1,1,1,0.8]) # leve feedback

    def __init__(self, icon_src='', text='', image_size=(70, 70), label_height=20, radius=10, label_spacing=None, **kwargs):
        super().__init__(orientation='vertical', size_hint=(None, None), **kwargs)
        self.icon_src = icon_src
        # usa diretamente o texto passado (sem lógica de "collapsed")
        label_text = text or ''
        self.font_size = kwargs.get('font_size', self.font_size)
        # permite sobrescrever label_spacing via argumento; se None, usa valor da propriedade
        if label_spacing is not None:
            self.label_spacing = label_spacing
        # use BoxLayout.spacing para separar os widgets verticalmente
        self.spacing = self.label_spacing
        # mantém spacing em sincronia caso a propriedade seja alterada depois
        self.bind(label_spacing=lambda inst, val: setattr(self, "spacing", val))

        # desenha fundo com RoundedRectangle
        img_w, img_h = image_size
        total_w = img_w
        total_h = img_h + label_height + self.label_spacing
        
        self.size = (total_w, total_h) # tamanho fixo baseado na imagem e label

        # imagem
        self._image_canvas = ImageCanvas(source=self.icon_src, overlay_color=self.img_tint, radius=radius, size_hint=(None, None), size=(img_w, img_h))

        # label (rótulo)
        self._label = Label(text=label_text, size_hint=(None, None), size=(img_w, label_height), font_size=self.font_size, markup=True, halign='center', valign='middle', font_name=FONT_NAME_SEMIBOLD)
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

        # binds: centraliza horizontalmente os filhos quando o tamanho/posição mudarem,
        # e atualiza cor da imagem quando img_tint mudar.
        self.bind(pos=self._update_children_pos, size=self._update_children_pos,
                  img_tint=self._update_image_tint)
         
        # estado inicial
        self._update_image_tint()

    def _update_children_pos(self, *args):
        # centraliza horizontalmente os filhos (BoxLayout cuida do posicionamento vertical e do spacing)
        try:
            img_w, img_h = self._image_canvas.size
            lbl_w, lbl_h = self._label.size
            img_x = self.x + max(0, (self.width - img_w) / 2)
            lbl_x = self.x + max(0, (self.width - lbl_w) / 2)
            self._image_canvas.x = img_x
            self._label.x = lbl_x
        except Exception:
            pass

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