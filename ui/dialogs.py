"""
Módulo de diálogos e popups da interface.
Contém classes para criar e gerenciar popups utilizados na interface.
"""

from kivy.uix.popup import Popup
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.clock import Clock

from widgets.buttons.common_button import CommonButton
from ui.ui_config import ICON_PATHS, UI_TEXTS
from env import TEXT_COLOR, FONT_NAME_SEMIBOLD, FONT_NAME_REGULAR, LINE_HEIGHT

class PrivateDialog:
    """Diálogo para ativação do modo privado."""
    
    def __init__(self, on_confirm=None, on_dismiss=None):
        """
        Inicializa o diálogo de modo privado.
        
        Args:
            on_confirm: Callback quando o usuário confirma
            on_dismiss: Callback quando o usuário cancela
        """
        self.on_confirm = on_confirm
        self.on_dismiss = on_dismiss
        self.popup = None
        
    def show(self):
        """Cria e exibe o diálogo."""
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        box = BoxLayout(orientation='vertical', padding=(24, 20), spacing=15)
        # Usa uma largura fixa, que será ajustada automaticamente para não ultrapassar a largura da janela
        box.width = dp(680)
        box.height = dp(300)  # altura inicial

        # Ícone
        icon = Image(source=ICON_PATHS['lock'], 
                    size_hint=(None, None), 
                    size=(dp(70), dp(70)), 
                    allow_stretch=True, 
                    keep_ratio=True)
        icon_anchor = AnchorLayout(size_hint=(1, 1))
        icon_anchor.add_widget(icon)
        box.add_widget(icon_anchor)

        # Título
        title = Label(
            text=UI_TEXTS['private_popup_title'], 
            color=TEXT_COLOR, 
            font_size=40, 
            size_hint=(1, None), 
            halign='center', 
            valign='middle', 
            markup=True,
            font_name=FONT_NAME_SEMIBOLD,  # Título usa SemiBold
            line_height=LINE_HEIGHT
        )
        title.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        title.bind(texture_size=lambda inst, ts: setattr(inst, "height", ts[1] if ts[1] > 0 else dp(36)))
        box.add_widget(title)

        # Subtítulo
        subtitle = Label(
            text=UI_TEXTS['private_popup_subtitle'], 
            color=TEXT_COLOR, 
            font_size=26, 
            size_hint=(1, None), 
            halign='center', 
            valign='middle', 
            markup=True,
            font_name=FONT_NAME_REGULAR,  # Subtítulo usa Regular
            line_height=LINE_HEIGHT
        )
        subtitle.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        subtitle.bind(texture_size=lambda inst, ts: setattr(inst, "height", ts[1] if ts[1] > 0 else dp(28)))
        box.add_widget(subtitle)

        # Botões
        confirm_btn = CommonButton(text=UI_TEXTS['yes_btn'])
        negative_btn = CommonButton(text=UI_TEXTS['no_btn'])

        btn_box = BoxLayout(orientation='horizontal', spacing=15, size_hint=(1, None))
        btn_box.add_widget(confirm_btn)
        btn_box.add_widget(negative_btn)
        box.add_widget(btn_box)

        # Popup principal
        popup = Popup(
            title='',
            content=anchor,
            size_hint=(1, 1),
            auto_dismiss=False,
            separator_height=0,
            background='',
            background_color=(1, 1, 1, 1),  # branco
        )
        
        # Ajusta altura do box após renderização
        Clock.schedule_once(lambda dt: setattr(
            box,
            "height",
            sum((child.height + box.spacing) for child in box.children)
            + ((box.padding[1] + box.padding[3]) if isinstance(box.padding, (list, tuple)) else (box.padding * 2))
            + 10
        ), 0)
        
        anchor.add_widget(box)

        self.popup = popup  # guarda referência para fechar depois
        confirm_btn.bind(on_release=self._on_confirm)
        negative_btn.bind(on_release=self._on_dismiss)

        popup.open()
    
    def _on_confirm(self, *_):
        """Callback para confirmação."""
        if callable(self.on_confirm):
            self.on_confirm()
        self.popup.dismiss()
    
    def _on_dismiss(self, *_):
        """Callback para cancelamento."""
        if callable(self.on_dismiss):
            self.on_dismiss()
        self.popup.dismiss()