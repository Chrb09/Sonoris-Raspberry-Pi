import asyncio
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor
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
        get_conversation_chunk_cb=None,
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
        self.get_conversation_chunk_cb = get_conversation_chunk_cb
        self.delete_conversation_cb = delete_conversation_cb
        self.set_settings_cb = set_settings_cb
        self._device_info = {"device_name": "Sonoris Device", "total_active_time": 0, "total_conversations": 0}

        # Estado simples para comandos
        self._last_cmd = "LIST"  # LIST | GET | DEL | CHUNK
        self._last_id = None
        self._last_chunk_index = 0
        
        # Buffer para stream de transcrições
        self._transcription_buffer = b""
        self._response_lock = threading.Lock()
        self._pending_response = b"[]"
        self._active_mode = "LIST"
        self._next_mode_after_consume = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        try:
            self._pending_response = self._build_response_sync("LIST")
        except Exception:
            pass
        self._queue_response("LIST")

    @characteristic(CHAR_UUID, CharFlags.WRITE | CharFlags.WRITE_WITHOUT_RESPONSE)
    def connect(self, options):
        pass

    @connect.setter
    def connect(self, value, options):
        try:
            txt = bytes(value).decode('utf-8').strip()
        except Exception:
            txt = ""
        
        print(f"[BLE] Comando recebido: '{txt}'")

        # Usa upper() apenas para comparação, não para processar o payload
        txt_upper = txt.upper()
        
        if txt_upper == "START":
            if callable(self.on_start_cb):
                self.on_start_cb()
        elif txt_upper == "STOP":
            if callable(self.on_stop_cb):
                self.on_stop_cb()
        elif txt_upper.startswith("SETTINGS:"):
            # Processa configurações de legendas enviadas pelo app
            # IMPORTANTE: usa txt original (não upper) para preservar case do JSON
            try:
                payload = txt.split(":", 1)[1]
                settings = json.loads(payload)
                if callable(self.set_settings_cb):
                    self.set_settings_cb(settings)
                else:
                    print(f"[BLE] Aviso: set_settings_cb não definido")
            except Exception as e:
                print(f"[BLE] Erro ao processar SETTINGS: {e}")
        elif txt_upper.startswith("LIST"):
            self._last_cmd = "LIST"
            self._last_id = None
            self._queue_response("LIST")
        elif txt_upper.startswith("GET:"):
            self._last_cmd = "GET"
            self._last_id = txt.split(":", 1)[1].strip()
            if self._last_id:
                self._queue_response("GET", conversation_id=self._last_id)
        elif txt_upper.startswith("CHUNK:"):
            # Formato: CHUNK:conversation_id:chunk_index
            parts = txt.split(":", 2)
            if len(parts) == 3:
                self._last_cmd = "CHUNK"
                self._last_id = parts[1].strip()
                try:
                    self._last_chunk_index = int(parts[2].strip())
                except ValueError:
                    self._last_chunk_index = 0
                    print(f"[BLE] Índice de chunk inválido, usando 0")
                if self._last_id:
                    self._queue_response("CHUNK", conversation_id=self._last_id, chunk_index=self._last_chunk_index)
            else:
                print(f"[BLE] Comando CHUNK mal formatado: {txt}")
        elif txt_upper.startswith("DEL:"):
            self._last_cmd = "DEL"
            self._last_id = txt.split(":", 1)[1].strip()
            # executa delete imediatamente
            if self._last_id and callable(self.delete_conversation_cb):
                try:
                    ok = self.delete_conversation_cb(self._last_id)
                except Exception as e:
                    print(f"[BLE] Erro ao deletar conversa '{self._last_id}': {e}")
            # após deletar, volta para LIST
            self._last_cmd = "LIST"
            self._last_id = None
            self._queue_response("LIST")
    
    @characteristic(DEVICE_INFO_UUID, CharFlags.READ | CharFlags.NOTIFY)
    def device_info(self, options):
        # Obtém informações atualizadas do dispositivo se disponível
        if callable(self.device_info_cb):
            info = self.device_info_cb()
            if info:
                self._device_info = info
            else:
                print(f"[BLE] Callback retornou None, usando dados em cache")
        else:
            print(f"[BLE] device_info_cb não é callable")
        
        # Converte para JSON e depois para bytes
        try:
            info_json = json.dumps(self._device_info)
            return bytes(info_json, 'utf-8')
        except Exception as e:
            print(f"[BLE] Erro ao enviar info do dispositivo: {e}")
            import traceback
            traceback.print_exc()
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
            with self._response_lock:
                payload = self._pending_response or b"[]"
                followup = self._next_mode_after_consume
                self._next_mode_after_consume = None
            if followup:
                self._queue_response(followup)
            return payload
        except Exception as e:
            print(f"[BLE] Erro ao enviar conversas: {e}")
            import traceback
            traceback.print_exc()
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
            self._transcription_buffer = bytes(json_data, 'utf-8')
            # NOTA: O notify será disparado automaticamente quando o app fizer read
            # ou quando o characteristic state mudar (depende da implementação do bluez_peripheral)
        except Exception as e:
            print(f"[BLE] Erro ao preparar transcrição para envio: {e}")

    def _queue_response(self, mode, conversation_id=None, chunk_index=0):
        if not self._executor:
            return
        self._executor.submit(
            self._build_response,
            mode,
            conversation_id,
            chunk_index,
        )

    def _build_response(self, mode, conversation_id=None, chunk_index=0):
        payload = self._build_response_sync(mode, conversation_id, chunk_index)
        if payload is None:
            payload = b"[]"
        with self._response_lock:
            self._pending_response = payload
            self._active_mode = mode
            self._next_mode_after_consume = "LIST" if mode in {"GET", "CHUNK"} else None

    def _build_response_sync(self, mode, conversation_id=None, chunk_index=0):
        try:
            if mode == "LIST":
                data = []
                if callable(self.get_conversations_cb):
                    data = self.get_conversations_cb() or []
                return json.dumps(data).encode('utf-8')
            if mode == "GET" and conversation_id:
                metadata = {}
                if callable(self.get_conversation_by_id_cb):
                    metadata = self.get_conversation_by_id_cb(conversation_id) or {}
                return json.dumps(metadata).encode('utf-8')
            if mode == "CHUNK" and conversation_id is not None:
                chunk_data = {}
                if callable(self.get_conversation_chunk_cb):
                    chunk_data = self.get_conversation_chunk_cb(conversation_id, chunk_index) or {}
                return json.dumps(chunk_data).encode('utf-8')
        except Exception as exc:
            print(f"[BLE] Erro ao preparar resposta {mode}: {exc}")
        return b"[]"

    def shutdown_executor(self):
        if self._executor:
            try:
                self._executor.shutdown(wait=False)
            except Exception:
                pass
            self._executor = None

async def _ble_main(
    on_start_cb,
    on_stop_cb,
    device_info_cb=None,
    set_device_name_cb=None,
    get_conversations_cb=None,
    get_conversation_by_id_cb=None,
    get_conversation_chunk_cb=None,
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
        get_conversation_chunk_cb=get_conversation_chunk_cb,
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
        try:
            service.shutdown_executor()
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
    get_conversation_chunk_cb=None,
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
                get_conversation_chunk_cb,
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
