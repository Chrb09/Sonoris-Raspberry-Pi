# ble_server.py
import asyncio
import threading
import time
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.util import get_message_bus

# UUIDs — mantenha o mesmo que você usa no Flutter
SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"

class ControlService(Service):
    def __init__(self, on_start_cb=None, on_stop_cb=None):
        super().__init__(SERVICE_UUID, True)
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb

    # --- INÍCIO DA CORREÇÃO ---
    # 1. Remova as flags READ e NOTIFY. Deixe apenas WRITE.
    # 2. Como não há READ, não precisamos mais do getter. A função agora serve apenas para o setter.
    @characteristic(CHAR_UUID, CharFlags.WRITE)
    def control(self, options):
        # Este método getter agora pode ser vazio, pois nunca será chamado sem a flag READ.
        # Algumas versões da biblioteca podem exigir que ele exista, mas não seja usado.
        pass

    @control.setter
    def control(self, value, options):
        # A lógica de escrita permanece a mesma.
        try:
            txt = bytes(value).decode('utf-8').strip().upper()
        except Exception:
            txt = ""
        
        print(f"[BLE] Comando recebido: '{txt}'")

        if txt == "START":
            if callable(self.on_start_cb):
                self.on_start_cb()
        elif txt == "STOP":
            if callable(self.on_stop_cb):
                self.on_stop_cb()

async def _ble_main(on_start_cb, on_stop_cb, stop_event: threading.Event):
    bus = await get_message_bus()
    service = ControlService(on_start_cb=on_start_cb, on_stop_cb=on_stop_cb)
    await service.register(bus)

    # tentativa tolerante para criar Advertisement (cobre variações de API)
    advert = None
    try:
        advert = Advertisement("SonorisRPi", [SERVICE_UUID], appearance=0, timeout=0, discoverable=True)
    except TypeError:
        try:
            advert = Advertisement("SonorisRPi", [SERVICE_UUID], 0, 0)
        except Exception as e:
            print("[BLE] falha ao criar Advertisement:", e)
            raise

    await advert.register(bus)
    print("[BLE] Advert registered - advertising service:", SERVICE_UUID)

    # loop simples até stop_event ser setado
    try:
        while not stop_event.is_set():
            await asyncio.sleep(0.5)
    finally:
        try:
            await advert.unregister()
        except Exception:
            pass
        try:
            await service.unregister()
        except Exception:
            pass
        print("[BLE] stopped")

def start_ble_server_in_thread(on_start_cb, on_stop_cb):
    stop_event = threading.Event()

    def target():
        try:
            asyncio.run(_ble_main(on_start_cb, on_stop_cb, stop_event))
        except Exception as e:
            print("[BLE] exceção no loop async:", e)

    th = threading.Thread(target=target, daemon=True)
    th.start()
    return stop_event, th
