import asyncio
import threading
import time
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
from bluez_peripheral.gatt.descriptor import descriptor, DescriptorFlags as DescFlags
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.util import get_message_bus

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"

class ConnectService(Service):
    def __init__(self, on_start_cb=None, on_stop_cb=None):
        super().__init__(SERVICE_UUID, True)
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb

    @characteristic(CHAR_UUID, CharFlags.WRITE | CharFlags.WRITE_WITHOUT_RESPONSE)
    def connect(self, options):
        pass

    @connect.setter
    def connect(self, value, options):
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
    service = ConnectService(on_start_cb=on_start_cb, on_stop_cb=on_stop_cb)
    await service.register(bus)

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
