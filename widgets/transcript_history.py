# widgets/transcript_history.py
# widgets/transcript_history.py
import os
import json
import time
import datetime
import uuid

from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

from utils.colors import parse_color

# ------------------------------
# TranscriptHistory
# ------------------------------

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# configurações
FONT_SIZE_PARTIAL = 35
TEXT_COLOR_GRAY = parse_color(cfg.get("color_gray", None), default=((0.30, 0.31, 0.31, 1))) # cor cinza para o texto TODO
FONT_SIZE_HISTORY = cfg.get("tamanho_historico", 28) # tamanho da fonte do histórico
MAX_PARTIAL_CHARS = int(cfg.get("max_partial_chars", 120)) # máximo de caracteres do texto parcial
PARTIAL_UPDATE_MIN_MS = int(cfg.get("partial_update_min_ms", 80)) # intervalo mínimo entre atualizações do texto parcial
HISTORY_MAX_LINES = int(cfg.get("history_max_lines", 200)) # máximo de linhas no histórico
PARTIAL_RESET_MS = int(cfg.get("partial_reset_ms", 3000)) # tempo para resetar o texto parcial (ms)
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "..", "transcripts")  # diretório para salvar transcrições

# Certifica que o diretório de transcrições existe
if not os.path.exists(TRANSCRIPTS_DIR):
    try:
        os.makedirs(TRANSCRIPTS_DIR)
    except Exception as e:
        print(f"Erro ao criar diretório de transcrições: {e}")

# widget de histórico (scrollable)
class TranscriptHistory(GridLayout):
    def __init__(self, **kwargs):
        kwargs.setdefault('padding', 10) 
        super().__init__(**kwargs)
        self.cols = 1
        self.size_hint_y = None
        self.spacing = 10
        self.bind(minimum_height=self.setter('height')) # auto ajusta height ao conteúdo
        self.lines = []
        
        # Propriedades para salvar transcrições
        self.is_private_mode = False
        self.saved_lines = []
        self.conversation_id = self._generate_conversation_id()
    
    def _generate_conversation_id(self):
        """Gera um ID único para uma nova conversa"""
        # Cria um ID no formato Conversa_DATA_HORA para facilitar identificação
        data_hora = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"Conversa_{data_hora}"
    
    def start_new_conversation(self):
        """Inicia uma nova conversa"""
        # Salva a conversa atual se tiver linhas
        self._save_current_conversation()
        # Gera um novo ID para a nova conversa
        self.conversation_id = self._generate_conversation_id()
        # Limpa as linhas salvas para a nova conversa
        self.saved_lines = []
    
    def set_private_mode(self, is_private):
        """Define se está em modo privado (não salva transcrições)"""
        self.is_private_mode = is_private

    # adiciona linha ao histórico, removendo a mais antiga se necessário
    def add_line(self, text):
        # cria label com altura variável (size_hint_y=None) e permite quebra de linha via text_size
        lbl = Label(
            text=text,
            size_hint_y=None,
            halign='left',
            valign='middle',
            text_size=(self.width, None),
            font_size=FONT_SIZE_HISTORY,
            color=TEXT_COLOR_GRAY,
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
            timestamp = datetime.datetime.now().isoformat()
            self.saved_lines.append({
                "text": text,
                "timestamp": timestamp
            })
            # Tenta salvar a linha no arquivo JSON
            self._save_line_to_file(text, timestamp)

    # limpa todo o histórico
    def clear_all(self):
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
        if self.is_private_mode:
            return
            
        try:
            conversation_file = os.path.join(TRANSCRIPTS_DIR, f"{self.conversation_id}.json")
            
            # Verifica se o arquivo já existe
            if os.path.exists(conversation_file):
                with open(conversation_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Cria novo arquivo com estrutura inicial
                data = {
                    "conversation_id": self.conversation_id,
                    "created_at": datetime.datetime.now().isoformat(),
                    "lines": []
                }
            
            # Adiciona nova linha
            data["lines"].append({
                "text": text,
                "timestamp": timestamp
            })
            
            # Salva o arquivo atualizado
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Erro ao salvar transcrição: {e}")
    
    def _save_current_conversation(self):
        """Salva todas as linhas da conversa atual em um arquivo"""
        if self.is_private_mode or not self.saved_lines:
            return
            
        try:
            conversation_file = os.path.join(TRANSCRIPTS_DIR, f"{self.conversation_id}.json")
            
            data = {
                "conversation_id": self.conversation_id,
                "created_at": datetime.datetime.now().isoformat(),
                "lines": self.saved_lines
            }
            
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
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
