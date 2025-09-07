# ble_server.py
# ble_server_fixed.py (trecho relevante)
import asyncio
import threading
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
from bluez_peripheral.gatt.descriptor import descriptor, DescriptorFlags as DescFlags
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.util import get_message_bus

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"
CCCD_UUID     = "00002902-0000-1000-8000-00805f9b34fb"  # client characteristic config

class ControlService(Service):
    def __init__(self, on_start_cb=None, on_stop_cb=None):
        # passe a UUID com hífens
        super().__init__(SERVICE_UUID, True)
        self._value = b""
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb
        self._subscribed = False

    @characteristic(CHAR_UUID, CharFlags.READ | CharFlags.WRITE | CharFlags.NOTIFY)
    def control(self, options):
        # leitura -> retorna bytes
        return self._value

    @control.setter
    def control(self, value, options):
        # escrita vinda do central (app)
        try:
            txt = bytes(value).decode('utf-8').strip()
        except Exception:
            txt = ""
        print("[BLE] write received:", txt)
        self._value = value

        if txt.upper() == "START":
            if callable(self.on_start_cb):
                self.on_start_cb()
        elif txt.upper() == "STOP":
            if callable(self.on_stop_cb):
                self.on_stop_cb()

    # Descriptor CCCD (0x2902) — expõe a config de notificação
    @descriptor(CCCD_UUID, DescFlags.READ | DescFlags.WRITE)
    def cccd(self, options):
        # valor padrão: notifications desativadas
        # quando central escreve 0x0001 -> significa subscribe
        # retornamos o valor atual (guardamos em _subscribed se necessário)
        return b'\x00\x00'

    # método helper para notificar (se precisar)
    def notify_value(self, bus, value_bytes):
        try:
            # setar valor interno e emitir properties changed via bluez_peripheral
            self._value = value_bytes
            self.Notify(self.path, {"Value": self._value})
        except Exception as e:
            print("[BLE] erro ao notificar:", e)

# código de advertising (tolerante a assinaturas diferentes)
async def _ble_main(on_start_cb, on_stop_cb, stop_event: threading.Event):
    bus = await get_message_bus()
    svc = ControlService(on_start_cb=on_start_cb, on_stop_cb=on_stop_cb)
    await svc.register(bus)

    # criar advertisement (tenta um padrão compatível)
    try:
        advert = Advertisement("SonorisRPi", [SERVICE_UUID], appearance=0, timeout=0, discoverable=True)
    except TypeError:
        advert = Advertisement("SonorisRPi", [SERVICE_UUID], 0, 0)
    await advert.register(bus)
    print("[BLE] Advertising:", SERVICE_UUID)

    while not stop_event.is_set():
        await asyncio.sleep(0.5)

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
