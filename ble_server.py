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
        # passe a UUID como string (com hífens está OK)
        super().__init__(SERVICE_UUID, True)
        self._value = b""
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb
        self._notifying = False

    @characteristic(CHAR_UUID, CharFlags.READ | CharFlags.WRITE | CharFlags.NOTIFY)
    def control(self, options):
        # retorno de leitura: bytes
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
                # callback para iniciar transcrição / UI
                self.on_start_cb()
            self._notifying = True
        elif txt.upper() == "STOP":
            if callable(self.on_stop_cb):
                self.on_stop_cb()
            self._notifying = False

    # helper para notificar (quando quiser enviar dados ao cliente)
    def notify(self, bus, value_bytes):
        """
        Atualiza o valor interno e emite PropertiesChanged para notificar clientes.
        (bluez-peripheral usa o mecanismo DBus — depende da versão da lib.)
        """
        try:
            self._value = bytes(value_bytes)
            # A forma exata de notificar pode variar pela versão da lib.
            # Esta chamada tenta usar o helper Notify se disponível:
            try:
                # Alguns exemplos usam self.Notify(self.path, {"Value": self._value})
                # mas a API pode variar; deixamos um print para depuração.
                self.Notify(self.path, {"Value": self._value})
            except Exception:
                # fallback: apenas logue (ou implemente outro método conforme a versão da lib)
                print("[BLE] notify fallback — valor definido, mas notify explícito falhou")
        except Exception as e:
            print("[BLE] erro no notify:", e)

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
