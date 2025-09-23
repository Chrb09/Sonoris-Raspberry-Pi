# main.py
import json
import os
import threading
import sys

# Variável de teste: definir True para pular a conexão BLE e iniciar direto a UI/transcriber.
# Mude para False em produção.
SKIP_BLE = True

# tenta importar o BLE server (pode falhar em ambientes sem BLE)
try:
    from ble_server import start_ble_server_in_thread
    BLE_AVAILABLE = True
except Exception:
    BLE_AVAILABLE = False

from transcriber import Transcriber
from ui import TranscriberApp

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

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
            ble_stop_event, _ = start_ble_server_in_thread(on_start_cb=on_ble_start, on_stop_cb=on_ble_stop)
            print("Aguardando conexão BLE. Abra o app e envie 'START' para iniciar.")
        else:
            print("[MAIN] BLE não disponível/encontrado. Ative SKIP_BLE=True para pular o BLE em ambiente de teste.")
            ble_stop_event = threading.Event()

    try:
        while True:
            # espera até o celular enviar "START" (ou até que SKIP_BLE já tenha setado o evento)
            ble_connected_event.wait()
            print("[MAIN] Conexão detectada (ou modo teste): iniciando Transcriber + UI")

            # cria instâncias
            transcriber = Transcriber(cfg)

            # cria app Kivy (auto_start True faz com que o transcriber seja iniciado no on_start do Kivy)
            app = TranscriberApp(transcriber=transcriber, auto_start=True)

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
