# ble_server.py
import asyncio
import threading
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
from bluez_peripheral.advert import Advertisment
from bluez_peripheral.util import get_message_bus

# UUIDs (troque se quiser)
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"

class ControlService(Service):
    def __init__(self, on_start_cb=None, on_stop_cb=None):
        super().__init__(SERVICE_UUID.replace('-', ''), True)  # primary service
        self._value = b""
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb
        self._notifying = False

    @characteristic(CHAR_UUID.replace('-', ''), CharFlags.READ | CharFlags.WRITE | CharFlags.NOTIFY)
    def control(self, options):
        # leitura retorna o último valor escrito
        return self._value

    # setter é chamado quando o central escreve na característica
    @control.setter
    def control(self, value, options):
        try:
            txt = bytes(value).decode('utf-8').strip()
        except Exception:
            txt = ""
        print("[BLE] write received:", txt)
        self._value = value

        # handshake simples: START / STOP
        if txt.upper() == "START":
            if callable(self.on_start_cb):
                # chamar callback (pode ser thread-safe)
                self.on_start_cb()
            self._notifying = True
        elif txt.upper() == "STOP":
            if callable(self.on_stop_cb):
                self.on_stop_cb()
            self._notifying = False

async def _ble_main(on_start_cb, on_stop_cb, stop_event: threading.Event):
    bus = await get_message_bus()
    svc = ControlService(on_start_cb=on_start_cb, on_stop_cb=on_stop_cb)
    await svc.register(bus)

    advert = Advertisment("SonorisRPi", [SERVICE_UUID], 0, 0)
    await advert.register(bus)
    print("[BLE] Advertising service:", SERVICE_UUID)

    # fica rodando até stop_event ser setado
    while not stop_event.is_set():
        await asyncio.sleep(0.5)

    # limpar (desregistrar) se necessário
    try:
        await advert.unregister()
    except Exception:
        pass
    try:
        await svc.unregister()
    except Exception:
        pass
    print("[BLE] stopped")

def start_ble_server_in_thread(on_start_cb, on_stop_cb):
    """
    Inicia o BLE server em uma thread separada.
    Retorna (stop_event, thread) para controle.
    """
    stop_event = threading.Event()

    def _target():
        try:
            asyncio.run(_ble_main(on_start_cb, on_stop_cb, stop_event))
        except Exception as e:
            print("[BLE] exceção no loop async:", e)

    th = threading.Thread(target=_target, daemon=True)
    th.start()
    return stop_event, th
