# main.py
import os
import threading
import sys
import time
import traceback
from kivy.app import App
from kivy.clock import Clock
from ui.waiting_screen import WaitingScreen
from ui.ui_config import init_window_settings, UI_TEXTS, ICON_PATHS

# Variável de teste: definir True para pular a conexão BLE e iniciar direto a UI/transcriber.
# Mude para False em produção.
SKIP_BLE = True 

# tenta importar o BLE server (pode falhar em ambientes sem BLE)
try:
    from ble_server import start_ble_server_in_thread
    BLE_AVAILABLE = True
except Exception:
    BLE_AVAILABLE = False

BASE_DIR = os.path.dirname(__file__)

# Configurações do Transcriber
cfg = {
    "model_path": "modelLarge",
    "sample_rate": 16000,
    "blocksize": 800,
    "frame_ms": 30,
    "use_vad": True,
    "vad_mode": 2,
    "device": None
}

# Eventos de sincronização entre threads
ble_connected_event = threading.Event()
ble_stop_event = None

def on_ble_start():
    """Chamado pela thread BLE quando o app no celular escreveu "START"."""
    print("[MAIN] BLE START recebido")
    ble_connected_event.set()

class WaitingApp(App):
    """Aplicativo Kivy que mostra tela de espera de conexão."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.waiting_screen = None
        self.should_transition = False
        self.transcriber_instance = None
        self.ble_service_ref = None
        self.setup_complete = threading.Event()
        self.transition_event = threading.Event()
    
    def build(self):
        """Constrói a tela de espera."""
        init_window_settings()
        self.title = UI_TEXTS['app_title']
        self.icon = ICON_PATHS['app_icon']
        self.waiting_screen = WaitingScreen()
        
        # Inicia thread de setup em background
        setup_thread = threading.Thread(target=self._background_setup, daemon=True)
        setup_thread.start()
        
        return self.waiting_screen
    
    def _background_setup(self):
        """Executa setup em background (carrega model, inicia BLE, etc)."""
        try:
            # Aguarda um pouco para UI iniciar
            time.sleep(0.5)
            
            # Atualiza mensagem
            Clock.schedule_once(lambda dt: self.update_message(
                "Carregando..."
            ))
            
            # Importa e inicializa o Transcriber (carrega o model)
            from transcriber import Transcriber
            self.transcriber_instance = Transcriber(cfg)
            
            # Atualiza mensagem
            Clock.schedule_once(lambda dt: self.update_message(
                "Aguardando conexão Bluetooth..."
            ))
            
            # Sinaliza que setup está completo
            self.setup_complete.set()
            
            # Aguarda evento de transição
            self.transition_event.wait()
            
            # Quando receber sinal de transição, para o app
            Clock.schedule_once(lambda dt: self.stop(), 0)
            
        except Exception as e:
            print(f"[WAITING_APP] Erro no setup em background: {e}")
            traceback.print_exc()
    
    def on_stop(self):
        """Garante que o processo seja encerrado ao fechar a janela."""
        # Se não for transição, encerra processo
        if not self.should_transition:
            print("[WAITING_APP] Janela fechada, encerrando processo...")
            os._exit(0)
    
    def update_message(self, message):
        """Atualiza mensagem na tela de espera."""
        if self.waiting_screen:
            self.waiting_screen.update_message(message)
    
    def transition_to_transcriber(self, ble_service_ref):
        """Sinaliza que deve transicionar para tela de transcrição."""
        self.ble_service_ref = ble_service_ref
        self.should_transition = True
        self.transition_event.set()

def apply_settings_to_ui(app, env_module):
    """Aplica as configurações de env nas widgets da UI existentes"""
    try:
        
        if not hasattr(app, 'layout'):
            print(f"[APPLY_UI] App sem layout ainda")
            return
        
        layout = app.layout
        
        # Atualiza o label parcial
        if hasattr(layout, 'transcription_manager'):
            tm = layout.transcription_manager
            
            # Atualiza partial label
            if hasattr(tm, 'partial_label'):
                tm.partial_label.font_size = env_module.FONT_SIZE_PARTIAL
                tm.partial_label.font_name = env_module.FONT_NAME
                tm.partial_label.color = env_module.TEXT_COLOR
                tm.partial_label.line_height = env_module.LINE_HEIGHT
            
            # Atualiza labels do histórico
            if hasattr(tm, 'history') and hasattr(tm.history, 'lines'):
                for label in tm.history.lines:
                    label.font_size = env_module.FONT_SIZE_HISTORY
                    label.font_name = env_module.FONT_NAME
                    label.color = env_module.TEXT_COLOR
                    label.line_height = env_module.LINE_HEIGHT
        
        # Atualiza cor de fundo do layout principal
        if hasattr(layout, 'bg_color'):
            layout.bg_color.rgba = env_module.BACKGROUND_COLOR
        
    except Exception as e:
        print(f"[APPLY_UI] Erro ao aplicar settings na UI: {e}")
        traceback.print_exc()

def run():
    global ble_stop_event
    
    # Variável para armazenar referência do BLE service
    ble_service_ref = None
    
    # Variável para armazenar referência do app Kivy (para aplicar settings)
    app_ref = {'instance': None}
    
    # Variável para armazenar referência ao TranscriptHistory
    transcript_history_ref = {'instance': None}
    
    # Cria o WaitingApp (roda na thread principal)
    waiting_app = WaitingApp()
    
    # Thread para configurar BLE em background
    def background_ble_and_wait():
        global ble_stop_event
        nonlocal ble_service_ref
        
        # Aguarda o setup do transcriber completar
        waiting_app.setup_complete.wait()
        print("[MAIN] Setup completo, model carregado")
        
        if SKIP_BLE:
            print("[MAIN] MODO DE TESTE: pulando BLE")
            ble_stop_event = threading.Event()
            time.sleep(1)
            ble_connected_event.set()
        else:
            # inicia o BLE server numa thread (vai chamar on_ble_start/stop) se disponível
            if BLE_AVAILABLE:
                # Callbacks para o BLE
                def get_device_info():
                    if transcript_history_ref['instance'] is not None:
                        info = transcript_history_ref['instance'].get_device_info_for_bluetooth()
                        return info
                    return None
                    
                def set_device_name(name):
                    if transcript_history_ref['instance'] is not None:
                        return transcript_history_ref['instance'].update_device_name(name)
                    return False
                    
                def get_conversations():
                    """Retorna lista RESUMIDA de conversas FINALIZADAS (id, created_at, start_ts, end_ts)."""
                    import json
                    conversations = []
                    try:
                        transcripts_dir = os.path.join(BASE_DIR, "transcripts")
                        if os.path.exists(transcripts_dir):
                            files_with_time = []
                            for file in os.listdir(transcripts_dir):
                                if file.endswith(".json"):
                                    file_path = os.path.join(transcripts_dir, file)
                                    try:
                                        # Lê o arquivo para verificar flag 'finalized'
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            data = json.load(f)
                                        
                                        # Verifica se conversa está finalizada
                                        is_finalized = data.get('finalized', False)
                                        if not is_finalized:
                                            conv_id = data.get('conversation_id', file)
                                            continue
                                        
                                        # Verifica se há linhas (conversa não vazia)
                                        if not data.get('lines'):
                                            print(f"[MAIN] Pulando conversa vazia: {data.get('conversation_id', 'unknown')}")
                                            continue
                                        
                                        mtime = os.path.getmtime(file_path)
                                        files_with_time.append((file_path, mtime))
                                    except Exception as e:
                                        print(f"[MAIN] Erro ao processar {file}: {e}")
                            
                            # ordena mais recentes primeiro e limita a 5
                            files_with_time.sort(key=lambda x: x[1], reverse=True)
                            for file_path, _ in files_with_time[:5]:
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        # Retorna apenas metadados mínimos para evitar MTU overflow
                                        conversations.append({
                                            'conversation_id': data.get('conversation_id', ''),
                                            'created_at': data.get('created_at', ''),
                                        })
                                except Exception as e:
                                    print(f"[MAIN] Erro ao ler {file_path}: {e}")
                    except Exception as e:
                        print(f"[MAIN] Erro ao listar conversas: {e}")
                    return conversations

                def get_conversation_by_id(conv_id: str):
                    """Retorna conversa completa ou chunk específico dela."""
                    import json
                    try:
                        transcripts_dir = os.path.join(BASE_DIR, "transcripts")
                        file_path = os.path.join(transcripts_dir, f"{conv_id}.json")
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            lines = data.get('lines', [])
                            total_lines = len(lines)
                            
                            # Define tamanho do chunk (4 linhas x 40 chars = 492 bytes, MTU-safe)
                            CHUNK_SIZE = 4
                            
                            # Calcula número total de chunks necessários
                            total_chunks = (total_lines + CHUNK_SIZE - 1) // CHUNK_SIZE if total_lines > 0 else 1
                            
                            # Retorna metadados da conversa indicando que precisa ser baixada em chunks
                            result = {
                                'conversation_id': data.get('conversation_id', ''),
                                'created_at': data.get('created_at', ''),
                                'finalized': data.get('finalized', False),
                                'total_lines': total_lines,
                                'total_chunks': total_chunks,
                                'chunk_size': CHUNK_SIZE,
                                'requires_chunking': total_chunks > 1,
                            }
                            
                            return result
                            
                    except Exception as e:
                        print(f"[MAIN] Erro ao carregar conversa {conv_id}: {e}")
                    return None
                
                def get_conversation_chunk(conv_id: str, chunk_index: int):
                    """Retorna um chunk específico de uma conversa."""
                    import json
                    try:
                        transcripts_dir = os.path.join(BASE_DIR, "transcripts")
                        file_path = os.path.join(transcripts_dir, f"{conv_id}.json")
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            
                            lines = data.get('lines', [])
                            CHUNK_SIZE = 4
                            
                            # Calcula início e fim do chunk
                            start_idx = chunk_index * CHUNK_SIZE
                            end_idx = min(start_idx + CHUNK_SIZE, len(lines))
                            
                            chunk_lines = lines[start_idx:end_idx]
                            
                            result = {
                                'conversation_id': data.get('conversation_id', ''),
                                'chunk_index': chunk_index,
                                'lines': chunk_lines,
                            }
                        
                            return result
                            
                    except Exception as e:
                        print(f"[MAIN] Erro ao carregar chunk {chunk_index} de {conv_id}: {e}")
                    return None

                def delete_conversation(conv_id: str) -> bool:
                    try:
                        transcripts_dir = os.path.join(BASE_DIR, "transcripts")
                        file_path = os.path.join(transcripts_dir, f"{conv_id}.json")
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            print(f"[MAIN] Conversa {conv_id} deletada do dispositivo.")
                            return True
                    except Exception as e:
                        print(f"[MAIN] Erro ao deletar conversa {conv_id}: {e}")
                    return False
                
                def set_settings(settings_dict):
                    """Callback que recebe configurações de legendas do app e aplica na UI"""
                    try:
                        
                        # Importa módulo env para modificar variáveis
                        import env
                        
                        # Converte cores de hex para tupla RGBA normalizada (0-1)
                        def hex_to_rgba(hex_color):
                            hex_color = hex_color.lstrip('#')
                            if len(hex_color) == 6:
                                r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                                return (r/255.0, g/255.0, b/255.0, 1.0)
                            return (0.168, 0.168, 0.168, 1.0)  # fallback
                        
                        # Normaliza chaves para lowercase (compatibilidade caso ble_server envie uppercase)
                        settings_normalized = {k.lower(): v for k, v in settings_dict.items()}
                        
                        # Atualiza variáveis de configuração em memória
                        if 'textcolor' in settings_normalized:
                            env.TEXT_COLOR = hex_to_rgba(settings_normalized['textcolor'])
                        
                        if 'bgcolor' in settings_normalized:
                            env.BACKGROUND_COLOR = hex_to_rgba(settings_normalized['bgcolor'])
                        
                        if 'fontsize' in settings_normalized:
                            font_size = float(settings_normalized['fontsize'])
                            env.FONT_SIZE = font_size
                            env.FONT_SIZE_PARTIAL = font_size
                            env.FONT_SIZE_HISTORY = int(font_size * 0.65)
                        
                        if 'fontweight' in settings_normalized:
                            weight = int(settings_normalized['fontweight'])
                            env.FONT_WEIGHT = weight
                            # Registra o novo peso se necessário
                            env.FONT_NAME = env.register_font_weight(weight)
                        
                        if 'lineheight' in settings_normalized:
                            env.LINE_HEIGHT = float(settings_normalized['lineheight'])
                        
                        if 'fontfamily' in settings_normalized:
                            family = settings_normalized['fontfamily']
                            env.FONT_FAMILY = family
                            # Reregistra a fonte com a nova família
                            font_file = env.get_font_file(family, env.FONT_WEIGHT)
                            if font_file:
                                from kivy.core.text import LabelBase
                                env.FONT_NAME = family
                                LabelBase.register(name=env.FONT_NAME, fn_regular=font_file)
                            else:
                                print(f"[MAIN]   - ⚠️ Fonte {family} não encontrada, mantendo atual")
                        
                        # Aplica as configurações na UI do Kivy se o app já estiver rodando
                        if app_ref['instance'] is not None:
                            Clock.schedule_once(lambda dt: apply_settings_to_ui(app_ref['instance'], env), 0.1)
                        else:
                            print(f"[MAIN] ℹApp não iniciado ainda - settings serão usados ao criar widgets")
                        
                    except Exception as e:
                        print(f"[MAIN] Erro ao aplicar settings: {e}")
                        traceback.print_exc()
                
                # Inicia o servidor BLE com os callbacks
                ble_stop_event, _, ble_service_ref = start_ble_server_in_thread(
                    on_start_cb=on_ble_start, 
                    on_stop_cb=None,
                    device_info_cb=get_device_info,
                    set_device_name_cb=set_device_name,
                    get_conversations_cb=get_conversations,
                    get_conversation_by_id_cb=get_conversation_by_id,
                    get_conversation_chunk_cb=get_conversation_chunk,
                    delete_conversation_cb=delete_conversation,
                    set_settings_cb=set_settings,
                )
                print("Aguardando conexão Bluetooth, conecte pelo app Sonoris no celular...")
            else:
                print("[MAIN] BLE não disponível/encontrado. Ative SKIP_BLE=True para pular o BLE em ambiente de teste.")
                ble_stop_event = threading.Event()
        
        # Aguarda conexão BLE
        ble_connected_event.wait()
        print("[MAIN] Conexão estabelecida!")
        
        # Atualiza mensagem
        Clock.schedule_once(lambda dt: waiting_app.update_message("Conectado!\n\nIniciando transcrição..."))
        time.sleep(0.5)
        
        # Sinaliza transição
        waiting_app.transition_to_transcriber(ble_service_ref)
    
    # Inicia thread BLE
    ble_thread = threading.Thread(target=background_ble_and_wait, daemon=True)
    ble_thread.start()
    
    # Roda o WaitingApp na thread principal (bloqueante)
    waiting_app.run()
    
    # Após WaitingApp encerrar, inicia o TranscriberApp
    print("[MAIN] WaitingApp encerrado, iniciando TranscriberApp...")
    
    from ui import TranscriberApp
    
    # Cria o TranscriberApp com o transcriber já carregado
    app = TranscriberApp(
        transcriber=waiting_app.transcriber_instance,
        auto_start=True,
        ble_service_ref=waiting_app.ble_service_ref
    )
    
    # Salva referência do app para permitir aplicação de settings
    app_ref['instance'] = app
    
    # Aguarda o app iniciar e então salva referência ao TranscriptHistory para uso no BLE
    def set_transcript_history_ref(dt):
        if hasattr(app, 'layout') and hasattr(app.layout, 'history'):
            transcript_history_ref['instance'] = app.layout.history
    Clock.schedule_once(set_transcript_history_ref, 1)
    
    # Roda o TranscriberApp
    app.run()
    
    # Após fechar, limpa recursos
    try:
        waiting_app.transcriber_instance.stop()
    except:
        pass
    
    print("[MAIN] Aplicação encerrada")

if __name__ == "__main__":
    run()
