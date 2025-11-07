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
TRANSCRIPTION_STREAM_UUID = "12345678-1234-5678-1234-56789abcdef5"

class ConnectService(Service):
    def __init__(
        self,
        on_start_cb=None,
        on_stop_cb=None,
        device_info_cb=None,
        set_device_name_cb=None,
        get_conversations_cb=None,
        get_conversation_by_id_cb=None,
        delete_conversation_cb=None,
        set_settings_cb=None,
    ):
        super().__init__(SERVICE_UUID, True)
        self.on_start_cb = on_start_cb
        self.on_stop_cb = on_stop_cb
        self.device_info_cb = device_info_cb
        self.set_device_name_cb = set_device_name_cb
        self.get_conversations_cb = get_conversations_cb
        self.get_conversation_by_id_cb = get_conversation_by_id_cb
        self.delete_conversation_cb = delete_conversation_cb
        self.set_settings_cb = set_settings_cb
        self._device_info = {"device_name": "Sonoris Device", "total_active_time": 0, "total_conversations": 0}

        # Estado simples para comandos
        self._last_cmd = "LIST"  # LIST | GET | DEL
        self._last_id = None
        
        # Buffer para stream de transcrições
        self._transcription_buffer = b""

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
        elif txt.startswith("SETTINGS:"):
            # Processa configurações de legendas enviadas pelo app
            try:
                payload = txt.split(":", 1)[1]
                settings = json.loads(payload)
                print(f"[BLE] Settings recebidos: {settings}")
                if callable(self.set_settings_cb):
                    self.set_settings_cb(settings)
                    print(f"[BLE] Settings aplicados com sucesso!")
                else:
                    print(f"[BLE] Aviso: set_settings_cb não definido")
            except Exception as e:
                print(f"[BLE] Erro ao processar SETTINGS: {e}")
        elif txt.startswith("LIST"):
            self._last_cmd = "LIST"
            self._last_id = None
        elif txt.startswith("GET:"):
            self._last_cmd = "GET"
            self._last_id = txt.split(":", 1)[1].strip()
        elif txt.startswith("DEL:"):
            self._last_cmd = "DEL"
            self._last_id = txt.split(":", 1)[1].strip()
            # executa delete imediatamente
            if self._last_id and callable(self.delete_conversation_cb):
                try:
                    ok = self.delete_conversation_cb(self._last_id)
                    print(f"[BLE] Delete conversa '{self._last_id}': {ok}")
                except Exception as e:
                    print(f"[BLE] Erro ao deletar conversa '{self._last_id}': {e}")
            # após deletar, volta para LIST
            self._last_cmd = "LIST"
            self._last_id = None
    
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
        try:
            # Modo LIST: retorna lista pequena de conversas (metadados ou poucas conversas)
            if self._last_cmd == "LIST":
                conversations_data = []
                if callable(self.get_conversations_cb):
                    conversations_data = self.get_conversations_cb() or []
                conv_json = json.dumps(conversations_data)
                return bytes(conv_json, 'utf-8')
            # Modo GET: retorna conversa completa por id
            elif self._last_cmd == "GET" and self._last_id:
                full_conv = None
                if callable(self.get_conversation_by_id_cb):
                    full_conv = self.get_conversation_by_id_cb(self._last_id)
                if full_conv is None:
                    full_conv = {}
                conv_json = json.dumps(full_conv)
                # após servir GET, volta para LIST por segurança
                self._last_cmd = "LIST"
                self._last_id = None
                return bytes(conv_json, 'utf-8')
            else:
                # fallback
                return bytes("[]", 'utf-8')
        except Exception as e:
            print(f"[BLE] Erro ao enviar conversas: {e}")
            return bytes("[]", 'utf-8')
    
    @characteristic(TRANSCRIPTION_STREAM_UUID, CharFlags.READ | CharFlags.NOTIFY)
    def transcription_stream(self, options):
        """Characteristic para stream de transcrições em tempo real."""
        result = self._transcription_buffer
        self._transcription_buffer = b""  # Limpa o buffer após leitura
        return result
    
    def send_transcription_data(self, json_data: str):
        """Envia dados de transcrição via notify. Chamado externamente."""
        try:
            print(f"[BLE] 📤 Enviando transcrição: {json_data[:100]}...")
            self._transcription_buffer = bytes(json_data, 'utf-8')
            # Trigger notify (precisa ser implementado quando integrado)
            # Por enquanto, o buffer será lido quando o app fizer read
        except Exception as e:
            print(f"[BLE] ❌ Erro ao preparar transcrição para envio: {e}")

async def _ble_main(
    on_start_cb,
    on_stop_cb,
    device_info_cb=None,
    set_device_name_cb=None,
    get_conversations_cb=None,
    get_conversation_by_id_cb=None,
    delete_conversation_cb=None,
    set_settings_cb=None,
    stop_event: threading.Event=None,
    service_ref: dict=None,
):
    bus = await get_message_bus()
    service = ConnectService(
        on_start_cb=on_start_cb, 
        on_stop_cb=on_stop_cb,
        device_info_cb=device_info_cb,
        set_device_name_cb=set_device_name_cb,
        get_conversations_cb=get_conversations_cb,
        get_conversation_by_id_cb=get_conversation_by_id_cb,
        delete_conversation_cb=delete_conversation_cb,
        set_settings_cb=set_settings_cb,
    )
    
    # Armazena referência do service para acesso externo
    if service_ref is not None:
        service_ref['instance'] = service
    
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

def start_ble_server_in_thread(
    on_start_cb,
    on_stop_cb,
    device_info_cb=None,
    set_device_name_cb=None,
    get_conversations_cb=None,
    get_conversation_by_id_cb=None,
    delete_conversation_cb=None,
    set_settings_cb=None,
):
    stop_event = threading.Event()
    service_ref = {'instance': None}  # Para armazenar referência do service

    def target():
        try:
            asyncio.run(_ble_main(
                on_start_cb, 
                on_stop_cb, 
                device_info_cb, 
                set_device_name_cb, 
                get_conversations_cb,
                get_conversation_by_id_cb,
                delete_conversation_cb,
                set_settings_cb,
                stop_event,
                service_ref
            ))
        except Exception as e:
            print("[BLE] exceção no loop async:", e)

    th = threading.Thread(target=target, daemon=True)
    th.start()
    return stop_event, th, service_ref
