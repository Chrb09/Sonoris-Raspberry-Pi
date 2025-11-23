# widgets/transcript_history.py
import os
import json
import time
import datetime
import uuid

from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from utils.device_info import DeviceInfo
from env import TEXT_COLOR, FONT_SIZE_HISTORY, LINE_HEIGHT, FONT_NAME

# ------------------------------
# TranscriptHistory
# ------------------------------

BASE_DIR = os.path.dirname(__file__)

# configurações
MAX_PARTIAL_CHARS = 120  # máximo de caracteres do texto parcial
PARTIAL_UPDATE_MIN_MS = 80  # intervalo mínimo entre atualizações do texto parcial (ms)
HISTORY_MAX_LINES = 200  # máximo de linhas no histórico
PARTIAL_RESET_MS = 3000  # tempo para resetar o texto parcial (ms)
MAX_LINE_CHARS = 40  # máximo de caracteres por linha (4 linhas x 40 chars = 492 bytes, MTU-safe)
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "..", "transcripts")  # diretório para salvar transcrições

# Certifica que o diretório de transcrições existe
if not os.path.exists(TRANSCRIPTS_DIR):
    try:
        os.makedirs(TRANSCRIPTS_DIR)
    except Exception as e:
        print(f"Erro ao criar diretório de transcrições: {e}")

# widget de histórico (scrollable)
class TranscriptHistory(GridLayout):
    def __init__(self, ble_service_ref=None, **kwargs):
        kwargs.setdefault('padding', 10) 
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.spacing = 10
        self.bind(minimum_height=self.setter('height')) # auto ajusta height ao conteúdo
        self.lines = []
        
        # Referência ao BLE service para envio de transcrições
        self.ble_service_ref = ble_service_ref
        
        # Inicializa o gerenciador de informações do dispositivo
        self.device_info = DeviceInfo()
        
        # Propriedades para salvar transcrições
        self.is_private_mode = False
        self.saved_lines = []
        self.conversation_id = self._generate_conversation_id()
        self.conversation_finalized = False  # Flag para indicar se conversa foi finalizada
        
        # Marca conversas antigas (de sessões anteriores) como finalizadas
        self._finalize_old_conversations()
        
        # Incrementa o contador de conversas ao iniciar
        self.device_info.increment_conversation_counter()
    
    def _generate_conversation_id(self):
        """Gera um ID único para uma nova conversa"""
        # Cria um ID no formato Conversa_DATA_HORA para facilitar identificação
        data_hora = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"Conversa_{data_hora}"
    
    def _finalize_old_conversations(self):
        """
        Marca todas as conversas existentes como finalizadas ao iniciar o programa.
        Isso garante que conversas interrompidas (quando programa foi fechado) sejam enviadas.
        """
        try:
            if not os.path.exists(TRANSCRIPTS_DIR):
                return
            
            print(f"[FINALIZE_OLD] Verificando conversas antigas...")
            finalized_count = 0
            
            for file in os.listdir(TRANSCRIPTS_DIR):
                if file.endswith(".json"):
                    file_path = os.path.join(TRANSCRIPTS_DIR, file)
                    try:
                        # Lê o arquivo
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        # Verifica se tem linhas (conversa não vazia)
                        if data.get('lines'):
                            # Adiciona flag de finalizada se não existir
                            if 'finalized' not in data or not data['finalized']:
                                data['finalized'] = True
                                
                                # Salva o arquivo atualizado
                                with open(file_path, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, ensure_ascii=False, indent=2)
                                
                                finalized_count += 1
                                print(f"[FINALIZE_OLD] ✓ Marcada como finalizada: {data.get('conversation_id', file)}")
                        else:
                            # Remove conversas vazias
                            os.remove(file_path)
                            print(f"[FINALIZE_OLD] 🗑️ Removida conversa vazia: {file}")
                    
                    except Exception as e:
                        print(f"[FINALIZE_OLD] ⚠️ Erro ao processar {file}: {e}")
            
            if finalized_count > 0:
                print(f"[FINALIZE_OLD] ✅ {finalized_count} conversa(s) antiga(s) marcada(s) como finalizada(s)")
            else:
                print(f"[FINALIZE_OLD] ℹ️ Nenhuma conversa antiga para finalizar")
        
        except Exception as e:
            print(f"[FINALIZE_OLD] ❌ Erro ao finalizar conversas antigas: {e}")
    
    def start_new_conversation(self):
        """Inicia uma nova conversa"""
        # Marca conversa atual como finalizada (pronta para envio quando app requisitar)
        self.conversation_finalized = True
        print(f"[START_NEW_CONV] Conversa '{self.conversation_id}' marcada como finalizada")
        
        # Salva a conversa atual se tiver linhas
        self._save_current_conversation()
        
        # Gera um novo ID para a nova conversa
        self.conversation_id = self._generate_conversation_id()
        # Limpa as linhas salvas para a nova conversa
        self.saved_lines = []
        # Reseta flag de finalização para nova conversa
        self.conversation_finalized = False
        # Incrementa o contador de conversas
        self.device_info.increment_conversation_counter()
    
    def set_private_mode(self, is_private):
        """Define se está em modo privado (não salva transcrições)"""
        self.is_private_mode = is_private

    # adiciona linha ao histórico, removendo a mais antiga se necessário
    def add_line(self, text):
        print(f"\n[ADD_LINE] Recebido: '{text[:50]}...' | Modo Privado: {self.is_private_mode}")
        
        # Limita o tamanho do texto para evitar overflow no envio BLE
        if len(text) > MAX_LINE_CHARS:
            text = text[:MAX_LINE_CHARS] + "..."
            print(f"[ADD_LINE] ⚠️ Texto truncado para {MAX_LINE_CHARS} caracteres")
        
        # Importa valores atuais do módulo env (podem ter sido atualizados via BLE)
        import env as env_module
        
        # cria label com altura variável (size_hint_y=None) e permite quebra de linha via text_size
        lbl = Label(
            text=text,
            size_hint_y=None,
            halign='left',
            valign='middle',
            text_size=(self.width, None),
            font_size=env_module.FONT_SIZE_HISTORY,
            color=env_module.TEXT_COLOR,
            font_name=env_module.FONT_NAME,
            line_height=env_module.LINE_HEIGHT
        )

        # quando a largura mudar, atualiza text_size para forçar rewrap do texto
        def _on_width(inst, w):
            inst.text_size = (w, None)
        lbl.bind(width=_on_width)

        # quando texture_size for calculado, ajusta a altura do label para o height do texto renderizado
        def _on_texture_size(inst, ts):
            try:
                inst.height = ts[1]
            except Exception:
                pass
        lbl.bind(texture_size=_on_texture_size)

        self.add_widget(lbl)
        # força uma atualização do texture_size no próximo frame para definir a altura inicial corretamente
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: _on_texture_size(lbl, lbl.texture_size), 0)
        self.lines.append(lbl)
        
        # Salva a linha se não estiver em modo privado
        if not self.is_private_mode:
            print(f"[ADD_LINE] Salvando linha (modo privado OFF)")
            timestamp = datetime.datetime.now().isoformat()
            self.saved_lines.append({
                "text": text,
                "timestamp": timestamp
            })
            # Tenta salvar a linha no arquivo JSON
            self._save_line_to_file(text, timestamp)
        else:
            print(f"[ADD_LINE] ⚠️ MODO PRIVADO ATIVO - não salvando")

    # limpa todo o histórico
    def clear_all(self):
        # Marca conversa atual como finalizada (pronta para envio quando app requisitar)
        self.conversation_finalized = True
        print(f"[CLEAR_ALL] Conversa '{self.conversation_id}' marcada como finalizada")
        
        # Salva a conversa atual antes de limpar
        self._save_current_conversation()
        
        # Inicia uma nova conversa
        self.start_new_conversation()
        
        # Limpa os widgets da UI
        for w in list(self.lines):
            try:
                self.remove_widget(w)
            except Exception:
                pass
        self.lines = []
    
    def _save_line_to_file(self, text, timestamp):
        """Salva uma linha em um arquivo de transcrição"""
        print(f"\n[SAVE_LINE] Iniciando salvamento...")
        
        if self.is_private_mode:
            print(f"[SAVE_LINE] ⚠️ MODO PRIVADO - abortando")
            return
            
        try:
            conversation_file = os.path.join(TRANSCRIPTS_DIR, f"{self.conversation_id}.json")
            print(f"[SAVE_LINE] Arquivo: {conversation_file}")
            print(f"[SAVE_LINE] Diretório existe: {os.path.exists(TRANSCRIPTS_DIR)}")
            
            # Verifica se o arquivo já existe
            if os.path.exists(conversation_file):
                print(f"[SAVE_LINE] Arquivo existe - carregando...")
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"[SAVE_LINE] Linhas existentes: {len(data.get('lines', []))}")
            else:
                # Cria novo arquivo com estrutura inicial
                print(f"[SAVE_LINE] Criando novo arquivo...")
                data = {
                    "conversation_id": self.conversation_id,
                    "created_at": datetime.datetime.now().isoformat(),
                    "finalized": False,  # Conversa em andamento
                    "lines": []
                }
            
            # Adiciona nova linha
            data["lines"].append({
                "text": text,
                "timestamp": timestamp
            })
            print(f"[SAVE_LINE] Total de linhas após adicionar: {len(data['lines'])}")
            
            # Salva o arquivo atualizado
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"[SAVE_LINE] ✓ SUCESSO - Arquivo salvo!")
            print(f"[SAVE_LINE] Tamanho do arquivo: {os.path.getsize(conversation_file)} bytes\n")
            
            # NÃO envia via BLE aqui - apenas salva localmente
            # O envio será feito apenas quando a conversa for finalizada
                
        except Exception as e:
            print(f"[SAVE_LINE] ✗ ERRO ao salvar transcrição: {e}")
            import traceback
            print(f"[SAVE_LINE] Traceback completo:")
            traceback.print_exc()
    
    # REMOVIDO: _send_conversation_via_ble
    # Conversas agora são enviadas apenas quando o app requisita via get_conversations_cb
    
    def _save_current_conversation(self):
        """Salva todas as linhas da conversa atual em um arquivo"""
        if self.is_private_mode or not self.saved_lines:
            return
            
        try:
            conversation_file = os.path.join(TRANSCRIPTS_DIR, f"{self.conversation_id}.json")
            
            data = {
                "conversation_id": self.conversation_id,
                "created_at": datetime.datetime.now().isoformat(),
                "finalized": self.conversation_finalized,  # Usa a flag da instância
                "lines": self.saved_lines
            }
            
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            if self.conversation_finalized:
                print(f"[SAVE_CONV] ✅ Conversa '{self.conversation_id}' salva como FINALIZADA")
            else:
                print(f"[SAVE_CONV] 💾 Conversa '{self.conversation_id}' salva (ainda em andamento)")
                
        except Exception as e:
            print(f"Erro ao salvar conversa: {e}")
    
    def get_saved_conversations(self):
        """Retorna uma lista de todas as conversas salvas"""
        conversations = []
        try:
            for file in os.listdir(TRANSCRIPTS_DIR):
                if file.startswith("Conversa_") and file.endswith(".json"):
                    file_path = os.path.join(TRANSCRIPTS_DIR, file)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        conversations.append(json.load(f))
        except Exception as e:
            print(f"Erro ao listar conversas salvas: {e}")
        return conversations
    
    def get_device_info_for_bluetooth(self):
        """Retorna informações do dispositivo para envio via Bluetooth"""
        # Atualiza o tempo ativo antes de retornar
        self.device_info.update_active_time()
        return self.device_info.get_device_data_for_bluetooth()
    
    def update_device_name(self, name):
        """Atualiza o nome do dispositivo"""
        try:
            return self.device_info.update_device_name(name)
        except Exception as e:
            print(f"[DEVICE_INFO] Erro ao atualizar nome: {e}")
            return False
