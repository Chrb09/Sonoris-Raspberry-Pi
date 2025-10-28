# main.py
import os
import threading
import sys

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

def run():
    global ble_stop_event

    if SKIP_BLE:
        print("[MAIN] MODO DE TESTE ATIVADO: pulando BLE e iniciando UI/transcriber diretamente.")
        # criar um evento para evitar None no finally e setar conexão como já estabelecida
        ble_stop_event = threading.Event()
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
                """Retorna lista RESUMIDA de conversas (id, created_at, start_ts, end_ts)."""
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
                                    mtime = os.path.getmtime(file_path)
                                    files_with_time.append((file_path, mtime))
                                except Exception as e:
                                    print(f"[MAIN] Erro ao obter mtime de {file}: {e}")
                        # ordena mais recentes primeiro e limita a 5
                        files_with_time.sort(key=lambda x: x[1], reverse=True)
                        for file_path, _ in files_with_time[:5]:
                            try:
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    lines = data.get('lines', [])
                                    start_ts = lines[0]['timestamp'] if lines else data.get('created_at', '')
                                    end_ts = lines[-1]['timestamp'] if len(lines) > 0 else data.get('created_at', '')
                                    conversations.append({
                                        'conversation_id': data.get('conversation_id', ''),
                                        'created_at': data.get('created_at', ''),
                                        'start_ts': start_ts,
                                        'end_ts': end_ts,
                                    })
                            except Exception as e:
                                print(f"[MAIN] Erro ao ler {file_path}: {e}")
                except Exception as e:
                    print(f"[MAIN] Erro ao listar conversas: {e}")
                print(f"[MAIN] get_conversations retornando {len(conversations)} conversação(ões) (resumo)")
                return conversations

            def get_conversation_by_id(conv_id: str):
                import json
                try:
                    transcripts_dir = os.path.join(BASE_DIR, "transcripts")
                    file_path = os.path.join(transcripts_dir, f"{conv_id}.json")
                    if os.path.exists(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            return json.load(f)
                except Exception as e:
                    print(f"[MAIN] Erro ao carregar conversa {conv_id}: {e}")
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
            
            # Inicia o servidor BLE com os callbacks
            ble_stop_event, _ = start_ble_server_in_thread(
                on_start_cb=on_ble_start, 
                on_stop_cb=on_ble_stop,
                device_info_cb=get_device_info,
                set_device_name_cb=set_device_name,
                get_conversations_cb=get_conversations,
                get_conversation_by_id_cb=get_conversation_by_id,
                delete_conversation_cb=delete_conversation,
            )
            print("Aguardando conexão Bluetooth, conecte pelo app Sonoris no celular...")
        else:
            print("[MAIN] BLE não disponível/encontrado. Ative SKIP_BLE=True para pular o BLE em ambiente de teste.")
            ble_stop_event = threading.Event()

    try:
        while True:
            # espera até o celular enviar "START" (ou até que SKIP_BLE já tenha setado o evento)
            ble_connected_event.wait()
            print("[MAIN] Conexão detectada (ou modo teste): iniciando Transcriber + UI")

            # --- LAZY IMPORTS: só importar Transcriber e UI depois que a conexão foi estabelecida ---
            from transcriber import Transcriber
            from ui import TranscriberApp
            # ------------------------------------------------------------------------------

            # cria instâncias
            transcriber = Transcriber(cfg)

            # cria app Kivy (auto_start True faz com que o transcriber seja iniciado no on_start do Kivy)
            app = TranscriberApp(transcriber=transcriber, auto_start=True)
            
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
