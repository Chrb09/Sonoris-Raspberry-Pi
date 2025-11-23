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
    def __init__(self, transcriber: Transcriber, auto_start=True, ble_service_ref=None, **kwargs):
        """
        Inicializa o aplicativo.
        
        Args:
            transcriber: Instância do transcriber para processar áudio
            auto_start: Se True, inicia o transcriber automaticamente
            ble_service_ref: Referência ao BLE service para envio de transcrições
            **kwargs: Argumentos adicionais para o App
        """
        super().__init__(**kwargs)
        self.transcriber = transcriber
        self.layout = None 
        self._auto_start = auto_start
        self.ble_service_ref = ble_service_ref

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
        self.layout = MainLayout(self.transcriber, ble_service_ref=self.ble_service_ref)
        return self.layout

    def on_start(self):
        """Inicializa o aplicativo e configura callbacks do transcriber."""
        # Buffer para rastrear o texto já processado
        processed_length = {'value': 0}
        
        # Limite de caracteres por linha (mesmo do transcript_history.py)
        MAX_LINE_CHARS = 40
        
        # Atualiza o texto parcial
        def on_partial(p):
            nonlocal processed_length
            
            # Se o texto atual ultrapassar o limite, quebra e envia para o histórico
            if len(p) > MAX_LINE_CHARS:
                # Encontra o último espaço antes do limite para quebra mais natural
                break_point = MAX_LINE_CHARS
                last_space = p[:MAX_LINE_CHARS].rfind(' ')
                if last_space > int(MAX_LINE_CHARS * 0.6):  # Se houver espaço em pelo menos 60% do limite
                    break_point = last_space
                
                # Texto que vai para o histórico
                line_to_save = p[:break_point].strip()
                # Texto que continua no parcial
                remaining_text = p[break_point:].strip()
                
                # Adiciona ao histórico
                if line_to_save:
                    Clock.schedule_once(lambda dt, line=line_to_save: self.layout.add_final(line))
                    # Atualiza o comprimento processado
                    processed_length['value'] = len(p) - len(remaining_text)
                
                # Limpa completamente o parcial e mostra apenas o texto restante
                def update_partial(dt):
                    self.layout.set_partial('')  # Limpa completamente
                    Clock.schedule_once(lambda dt2: self.layout.set_partial(remaining_text), 0.05)
                Clock.schedule_once(update_partial, 0.01)
            else:
                # Texto cabe no limite, mostra normalmente
                Clock.schedule_once(lambda dt, p=p: self.layout.set_partial(p))

        # Adiciona linha finalizada no histórico
        def on_final(f):
            # Reseta o contador quando finaliza
            processed_length['value'] = 0
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
            
        # Atualiza o tempo ativo no DeviceInfo
        try:
            if hasattr(self.layout, 'history') and hasattr(self.layout.history, 'device_info'):
                self.layout.history.device_info.update_active_time()
        except Exception as e:
            print(f"Erro ao atualizar tempo ativo: {e}")