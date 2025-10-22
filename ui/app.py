"""
Módulo da aplicação principal da interface do usuário.
Este módulo contém a classe TranscriberApp que inicializa a aplicação Kivy e gerencia o ciclo de vida.
"""

import os
import sys
from kivy.app import App
from kivy.clock import Clock
from transcriber import Transcriber
from ui.main_layout import MainLayout
from ui.ui_config import truncate_partial, init_window_settings, UI_TEXTS, ICON_PATHS

class TranscriberApp(App):
    def __init__(self, transcriber: Transcriber, auto_start=True, **kwargs):
        """
        Inicializa o aplicativo.
        
        Args:
            transcriber: Instância do transcriber para processar áudio
            auto_start: Se True, inicia o transcriber automaticamente
            **kwargs: Argumentos adicionais para o App
        """
        super().__init__(**kwargs)
        self.transcriber = transcriber
        self.layout = None 
        self._auto_start = auto_start

    def build(self):
        """
        Constrói a interface do aplicativo.
        
        Returns:
            Layout principal da aplicação
        """
        # Inicializa as configurações da janela
        init_window_settings()
        
        self.title = UI_TEXTS['app_title']
        self.icon = ICON_PATHS['app_icon']
        self.layout = MainLayout(self.transcriber)
        return self.layout

    def on_start(self):
        """Inicializa o aplicativo e configura callbacks do transcriber."""
        # Atualiza o texto parcial
        def on_partial(p):
            Clock.schedule_once(lambda dt, p=p: self.layout.set_partial(truncate_partial(p)))

        # Adiciona linha finalizada no histórico
        def on_final(f):
            Clock.schedule_once(lambda dt, f=f: self.layout.add_final(f))

        # Mostra erro no terminal
        def on_error(e):
            print("Transcriber error:", e, file=sys.stderr)

        # Configura callbacks no transcriber
        self.transcriber.set_callbacks(
            on_partial=on_partial,
            on_final=on_final,
            on_error=on_error
        )

        # Inicia transcriber apenas se auto_start for true
        if self._auto_start:
            self.transcriber.start()

    def on_stop(self):
        """Finaliza o aplicativo graciosamente."""
        # Para o transcriber graciosamente
        try:
            self.transcriber.stop()
        except Exception:
            pass