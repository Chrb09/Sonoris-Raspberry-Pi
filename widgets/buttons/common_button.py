# widgets/common_button.py
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.properties import ListProperty, NumericProperty, StringProperty, ObjectProperty
from kivy.graphics import Color, RoundedRectangle
from env import FONT_NAME_BOLD

class CommonButton(Button):
    bg_color = ListProperty([0.231, 0.510, 0.965, 1])  # azul padrão
    txt_color = ListProperty([1, 1, 1, 1])  # branco padrão
    height = NumericProperty(dp(65))
    radius = NumericProperty(dp(14))

    def __init__(self, text="", on_release=None, **kwargs):
        kwargs.setdefault("markup", True)
        kwargs.setdefault("height", dp(65))
        kwargs.setdefault("size_hint", (1, None))

        super().__init__(text=f"[b]{text}[/b]", **kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # transparente
        self.color = self.txt_color # cor do texto
        self.font_size = dp(30)
        self.font_name = FONT_NAME_BOLD  # Usa fonte Bold para botões

        # desenha fundo arredondado
        with self.canvas.before:
            Color(*self.bg_color)
            self._rounded_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])

        self.bind(pos=self._update_rect, size=self._update_rect) # atualiza rounded rect ao mudar pos/size
        self.bind(bg_color=self._update_bg_color) # atualiza cor do fundo quando bg_color mudar

        if on_release is not None:
            try:
                self.bind(on_release=on_release)
            except Exception:
                self.extra_callback = on_release
        
    # atualiza posição e tamanho do rounded rect
    def _update_rect(self, *args):
        try:
            self._rounded_rect.pos = self.pos
            self._rounded_rect.size = self.size
            # garantir que radius reflita propriedade
            self._rounded_rect.radius = [self.radius]
        except Exception:
            pass

    # atualiza cor do fundo
    def _update_bg_color(self, instance, value):
        try:
            # remove/limpa e recria (simples e robusto)
            self.canvas.before.clear()
            with self.canvas.before:
                Color(*self.bg_color)
                self._rounded_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        except Exception:
            pass
