import asyncio
import threading
import time
import json
from bluez_peripheral.gatt.service import Service
from bluez_peripheral.gatt.characteristic import characteristic, CharacteristicFlags as CharFlags
from bluez_peripheral.gatt.descriptor import descriptor, DescriptorFlags as DescFlags
from bluez_peripheral.advert import Advertisement
from bluez_peripheral.util import get_message_bus

SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
CHAR_UUID    = "12345678-1234-5678-1234-56789abcdef1"
DEVICE_INFO_UUID = "12345678-1234-5678-1234-56789abcdef2"
DEVICE_NAME_UUID = "12345678-1234-5678-1234-56789abcdef3"
CONVERSATIONS_UUID = "12345678-1234-5678-1234-56789abcdef4"

class ConnectService(Service):
    def __init__(self, on_start_cb=None, on_stop_cb=None, device_info_cb=None, set_device_name_cb=None, get_conversations_cb=None):
        super().__init__(SERVICE_UUID, True)
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb
        self.device_info_cb = device_info_cb
        self.set_device_name_cb = set_device_name_cb
        self.get_conversations_cb = get_conversations_cb
        self._device_info = {"device_name": "Sonoris Device", "total_active_time": 0, "total_conversations": 0}

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
    
    @characteristic(DEVICE_INFO_UUID, CharFlags.READ | CharFlags.NOTIFY)
    def device_info(self, options):
        # Obtém informações atualizadas do dispositivo se disponível
        if callable(self.device_info_cb):
            self._device_info = self.device_info_cb() or self._device_info
        
        # Converte para JSON e depois para bytes
        try:
            info_json = json.dumps(self._device_info)
            return bytes(info_json, 'utf-8')
        except Exception as e:
            print(f"[BLE] Erro ao enviar info do dispositivo: {e}")
            return bytes("{}", 'utf-8')
    
    @characteristic(DEVICE_NAME_UUID, CharFlags.WRITE | CharFlags.WRITE_WITHOUT_RESPONSE)
    def device_name(self, options):
        pass
    
    @device_name.setter
    def device_name(self, value, options):
        try:
            name = bytes(value).decode('utf-8').strip()
            if name and callable(self.set_device_name_cb):
                success = self.set_device_name_cb(name)
                print(f"[BLE] Nome do dispositivo atualizado para: '{name}' (sucesso: {success})")
        except Exception as e:
            print(f"[BLE] Erro ao definir nome do dispositivo: {e}")
    
    @characteristic(CONVERSATIONS_UUID, CharFlags.READ | CharFlags.NOTIFY)
    def conversations(self, options):
        # Obtém lista de conversas se disponível
        conversations_data = []
        if callable(self.get_conversations_cb):
            conversations_data = self.get_conversations_cb() or []
        
        # Converte para JSON e depois para bytes
        try:
            conv_json = json.dumps(conversations_data)
            return bytes(conv_json, 'utf-8')
        except Exception as e:
            print(f"[BLE] Erro ao enviar conversas: {e}")
            return bytes("[]", 'utf-8')

async def _ble_main(on_start_cb, on_stop_cb, device_info_cb=None, set_device_name_cb=None, get_conversations_cb=None, stop_event: threading.Event=None):
    bus = await get_message_bus()
    service = ConnectService(
        on_start_cb=on_start_cb, 
        on_stop_cb=on_stop_cb,
        device_info_cb=device_info_cb,
        set_device_name_cb=set_device_name_cb,
        get_conversations_cb=get_conversations_cb
    )
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

def start_ble_server_in_thread(on_start_cb, on_stop_cb, device_info_cb=None, set_device_name_cb=None, get_conversations_cb=None):
    stop_event = threading.Event()

    def target():
        try:
            asyncio.run(_ble_main(
                on_start_cb, 
                on_stop_cb, 
                device_info_cb, 
                set_device_name_cb, 
                get_conversations_cb,
                stop_event
            ))
        except Exception as e:
            print("[BLE] exceção no loop async:", e)

    th = threading.Thread(target=target, daemon=True)
    th.start()
    return stop_event, th
