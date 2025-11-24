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
SKIP_BLE = False

# tenta importar o BLE server (pode falhar em ambientes sem BLE)
try:
    from ble_server import start_ble_server_in_thread
    BLE_AVAILABLE = True
except Exception:
    BLE_AVAILABLE = False

# REMOVED top-level imports of Transcriber/TranscriberApp to avoid Kivy creating a window at import time
# from transcriber import Transcriber
# from ui import TranscriberApp

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
ble_disconnected_event = threading.Event()
ble_stop_event = None  # será o stop_event retornado pelo BLE thread (ou criado em modo skip)

def on_ble_start():
    """
    Chamado pela thread BLE quando o app no celular escreveu "START".
    """
    print("[MAIN] BLE START recebido")
    ble_connected_event.set()
    ble_disconnected_event.clear()

def on_ble_stop():
    """
    Chamado pela thread BLE quando o app no celular escreveu "STOP".
    Também é acionado se quiser encerrar a sessão.
    """
    print("[MAIN] BLE STOP recebido")
    ble_disconnected_event.set()
    ble_connected_event.clear()

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
                "Aguardando conexão Bluetooth...\n\nCarregando modelo de reconhecimento..."
            ))
            
            # Importa e inicializa o Transcriber (carrega o model)
            from transcriber import Transcriber
            self.transcriber_instance = Transcriber(cfg)
            
            # Atualiza mensagem
            Clock.schedule_once(lambda dt: self.update_message(
                "Aguardando conexão Bluetooth...\n\nModelo carregado!\nConecte pelo app Sonoris no celular"
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
        print(f"[APPLY_UI] 🎨 Aplicando settings nos widgets...")
        
        if not hasattr(app, 'layout'):
            print(f"[APPLY_UI] ⚠️ App sem layout ainda")
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
                print(f"[APPLY_UI]   ✓ Partial label atualizado")
            
            # Atualiza labels do histórico
            if hasattr(tm, 'history') and hasattr(tm.history, 'lines'):
                for label in tm.history.lines:
                    label.font_size = env_module.FONT_SIZE_HISTORY
                    label.font_name = env_module.FONT_NAME
                    label.color = env_module.TEXT_COLOR
                    label.line_height = env_module.LINE_HEIGHT
                print(f"[APPLY_UI]   ✓ {len(tm.history.lines)} labels do histórico atualizados")
        
        # Atualiza cor de fundo do layout principal
        if hasattr(layout, 'bg_color'):
            layout.bg_color.rgba = env_module.BACKGROUND_COLOR
            print(f"[APPLY_UI]   ✓ Cor de fundo atualizada: {env_module.BACKGROUND_COLOR}")
        
        print(f"[APPLY_UI] ✓ Settings aplicados com sucesso!")
    except Exception as e:
        print(f"[APPLY_UI] ❌ Erro ao aplicar settings na UI: {e}")
        import traceback
        traceback.print_exc()

def run():
    global ble_stop_event

    # Variável para armazenar referência do BLE service
    ble_service_ref = None
    
    # Variável para armazenar referência do app Kivy (para aplicar settings)
    app_ref = {'instance': None}
    
    # Cria o WaitingApp
    waiting_app = WaitingApp()
    
    # Thread para iniciar BLE e aguardar conexão em background
    def background_ble_setup():
        global ble_stop_event
        nonlocal ble_service_ref
        
        # Aguarda setup completo (model carregado)
        waiting_app.setup_complete.wait()
        
        if SKIP_BLE:
            print("[MAIN] MODO DE TESTE ATIVADO: pulando BLE e iniciando UI/transcriber diretamente.")
            ble_stop_event = threading.Event()
            time.sleep(1)
            ble_connected_event.set()
        else:
            # inicia o BLE server numa thread (vai chamar on_ble_start/stop) se disponível
            if BLE_AVAILABLE:
                # Variáveis para referência do callback
                transcript_history_ref = {'instance': None}
            
            # Callbacks para o BLE
            def get_device_info():
                if transcript_history_ref['instance'] is not None:
                    return transcript_history_ref['instance'].get_device_info_for_bluetooth()
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
                                        print(f"[MAIN] Pulando conversa não finalizada: {conv_id}")
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
                print(f"[MAIN] get_conversations retornando {len(conversations)} conversação(ões) FINALIZADAS")
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
                        
                        print(f"[MAIN] Conversa {conv_id}: {total_lines} linhas, {total_chunks} chunk(s)")
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
                        
                        print(f"[MAIN] Enviando chunk {chunk_index} de {conv_id}: {len(chunk_lines)} linhas")
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
                    print(f"[MAIN] 🎨 Aplicando configurações de legendas: {settings_dict}")
                    
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
                        print(f"[MAIN]   - TEXT_COLOR: {env.TEXT_COLOR}")
                    
                    if 'bgcolor' in settings_normalized:
                        env.BACKGROUND_COLOR = hex_to_rgba(settings_normalized['bgcolor'])
                        print(f"[MAIN]   - BACKGROUND_COLOR: {env.BACKGROUND_COLOR}")
                    
                    if 'fontsize' in settings_normalized:
                        font_size = float(settings_normalized['fontsize'])
                        env.FONT_SIZE = font_size
                        env.FONT_SIZE_PARTIAL = font_size
                        env.FONT_SIZE_HISTORY = int(font_size * 0.65)
                        print(f"[MAIN]   - FONT_SIZE: {env.FONT_SIZE} (history: {env.FONT_SIZE_HISTORY})")
                    
                    if 'fontweight' in settings_normalized:
                        weight = int(settings_normalized['fontweight'])
                        env.FONT_WEIGHT = weight
                        # Registra o novo peso se necessário
                        env.FONT_NAME = env.register_font_weight(weight)
                        print(f"[MAIN]   - FONT_WEIGHT: {env.FONT_WEIGHT} -> {env.FONT_NAME}")
                    
                    if 'lineheight' in settings_normalized:
                        env.LINE_HEIGHT = float(settings_normalized['lineheight'])
                        print(f"[MAIN]   - LINE_HEIGHT: {env.LINE_HEIGHT}")
                    
                    if 'fontfamily' in settings_normalized:
                        family = settings_normalized['fontfamily']
                        env.FONT_FAMILY = family
                        # Reregistra a fonte com a nova família
                        font_file = env.get_font_file(family, env.FONT_WEIGHT)
                        if font_file:
                            from kivy.core.text import LabelBase
                            env.FONT_NAME = family
                            LabelBase.register(name=env.FONT_NAME, fn_regular=font_file)
                            print(f"[MAIN]   - FONT_FAMILY: {family} -> {font_file}")
                        else:
                            print(f"[MAIN]   - ⚠️ Fonte {family} não encontrada, mantendo atual")
                    
                    # Aplica as configurações na UI do Kivy se o app já estiver rodando
                    if app_ref['instance'] is not None:
                        from kivy.clock import Clock
                        Clock.schedule_once(lambda dt: apply_settings_to_ui(app_ref['instance'], env), 0.1)
                        print(f"[MAIN] ✓ Configurações agendadas para aplicação na UI")
                    else:
                        print(f"[MAIN] ℹ️ App não iniciado ainda - settings serão usados ao criar widgets")
                    
                except Exception as e:
                    print(f"[MAIN] ❌ Erro ao aplicar settings: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Inicia o servidor BLE com os callbacks
            ble_stop_event, _, ble_service_ref = start_ble_server_in_thread(
                on_start_cb=on_ble_start, 
                on_stop_cb=on_ble_stop,
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

    try:
        while True:
            # espera até o celular enviar "START" (ou até que SKIP_BLE já tenha setado o evento)
            ble_connected_event.wait()
            print("[MAIN] Conexão detectada (ou modo teste): iniciando UI de transcrição")
            
            # Atualiza mensagem de espera
            waiting_app.update_message("Conectado!\n\nIniciando transcrição...")
            time.sleep(0.5)

            # --- LAZY IMPORT: só importar TranscriberApp depois que a conexão foi estabelecida ---
            from ui import TranscriberApp
            # ------------------------------------------------------------------------------

            # Sinaliza transição para app de transcrição
            waiting_app.transition_to_transcriber(transcriber, ble_service_ref)
            
            # Aguarda o waiting_app parar
            kivy_thread.join()
            
            # Agora cria e roda o app de transcrição
            # cria app Kivy (auto_start True faz com que o transcriber seja iniciado no on_start do Kivy)
            app = TranscriberApp(transcriber=transcriber, auto_start=True, ble_service_ref=ble_service_ref)
            
            # Salva referência do app para permitir aplicação de settings
            app_ref['instance'] = app
            
            # Aguarda o app iniciar e então salva referência ao TranscriptHistory para uso no BLE
            from kivy.clock import Clock
            def set_transcript_history_ref(dt):
                if hasattr(app, 'layout') and hasattr(app.layout, 'history'):
                    if 'transcript_history_ref' in globals():
                        transcript_history_ref['instance'] = app.layout.history
                        print("[MAIN] TranscriptHistory referenciado para uso com BLE")
            Clock.schedule_once(set_transcript_history_ref, 1)

            # starta uma thread que vigia a desconexão e força o app a parar se necessário
            def watcher():
                # espera que ble_disconnected_event seja setado
                ble_disconnected_event.wait()
                print("[MAIN] watcher: BLE desconectado, parando app...")
                try:
                    from kivy.clock import Clock
                    Clock.schedule_once(lambda dt: app.stop(), 0)
                except Exception as e:
                    print("[MAIN] erro ao parar app:", e)

            w = threading.Thread(target=watcher, daemon=True)
            w.start()

            # roda o Kivy (bloqueante) — quando app.stop() for chamado, run() retorna e continuamos
            app.run()

            # após app.stop() retornar, garantir que transcriber foi parado
            try:
                transcriber.stop()
            except Exception:
                pass

            # --- AQUI: comportamento após fechar a UI ---
            if SKIP_BLE:
                # modo de teste: encerrar completamente (não reiniciar)
                print("[MAIN] SKIP_BLE ativo — encerrando execucao apos sessao de teste.")
                break

            # Em execução normal com BLE, limpa eventos e volta a aguardar nova conexão
            ble_connected_event.clear()
            ble_disconnected_event.clear()
            print("[MAIN] Sessão finalizada. Voltando a aguardar conexão BLE...")
            
            # Recria o transcriber para nova sessão (já carrega o model)
            transcriber = Transcriber(cfg)
            
            # Recria o waiting app para nova sessão
            waiting_app = WaitingApp()
            kivy_thread = threading.Thread(target=lambda: waiting_app.run(), daemon=False)
            kivy_thread.start()
            time.sleep(0.5)
            waiting_app.update_message("Aguardando conexão Bluetooth...\n\nConecte pelo app Sonoris no celular")
    except KeyboardInterrupt:
        print("Encerrando por KeyboardInterrupt...")
    finally:
        # solicitar parada do BLE thread (se existir)
        if ble_stop_event:
            try:
                ble_stop_event.set()
            except Exception:
                pass

if __name__ == "__main__":
    run()
