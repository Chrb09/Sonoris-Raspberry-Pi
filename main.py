# main.py
import json
import os
import time
import threading

from ble_server import start_ble_server_in_thread
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
ble_stop_event = None  # será o stop_event retornado pelo BLE thread

def on_ble_start():
    """
    Chamado pela thread BLE quando o app no celular escreveu "START".
    """
    print("[MAIN] BLE START recebido")
    # sinaliza que podemos iniciar UI/transcriber
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
    # se a UI estiver rodando, nós a encerramos (a lógica para encerrar a UI fica abaixo)

def run():
    global ble_stop_event

    # inicia o BLE server numa thread (vai chamar on_ble_start/stop)
    ble_stop_event, _ = start_ble_server_in_thread(on_start_cb=on_ble_start, on_stop_cb=on_ble_stop)

    print("Aguardando conexão BLE. Abra o app e envie 'START' para iniciar.")
    try:
        while True:
            # espera até o celular enviar "START"
            ble_connected_event.wait()
            print("[MAIN] Conexão detectada: iniciando Transcriber + UI")

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
                    # chamar stop de forma segura na thread principal do Kivy
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

            # limpa eventos e volta a aguardar nova conexão
            ble_connected_event.clear()
            ble_disconnected_event.clear()
            print("[MAIN] Sessão finalizada. Voltando a aguardar conexão BLE...")
    except KeyboardInterrupt:
        print("Encerrando por KeyboardInterrupt...")
    finally:
        # solicitar parada do BLE thread
        if ble_stop_event:
            ble_stop_event.set()

if __name__ == "__main__":
    run()
