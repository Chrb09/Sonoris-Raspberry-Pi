from kivy.metrics import dp
from widgets.buttons.common_button import CommonButton
from env import BLUE_COLOR, WHITE_COLOR

class PillButton(CommonButton):
    def __init__(self, text="", on_release=None, **kwargs):
        kwargs.setdefault("font_size", dp(24))
        kwargs.setdefault("radius", dp(25))
        kwargs.setdefault("height", dp(50))
        kwargs.setdefault("size_hint", (None, None))  # largura ajustada ao texto

        super().__init__(text=text, on_release=on_release, **kwargs)
        # cores específicas para PillButton
        self.bg_color = WHITE_COLOR
        self.color = BLUE_COLOR  # cor do texto

        # ajusta largura automaticamente ao tamanho do texto + padding
        self.bind(texture_size=lambda inst, val: setattr(self, "width", inst.texture_size[0] + dp(40)))