"""
Gerenciador de informações do dispositivo.
Este módulo contém classes para gerenciar informações do dispositivo,
como nome, tempo ativo e contador de conversas.
"""

import os
import json
import time

class DeviceInfo:
    """
    Classe para gerenciar informações do dispositivo.
    Armazena e gerencia o nome do dispositivo, tempo ativo e contador de conversas.
    """
    
    def __init__(self, base_dir=None):
        """Inicializa o gerenciador de informações do dispositivo."""
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "device_data")
        self.info_file = os.path.join(self.data_dir, "device_info.json")
        
        # Valores padrão
        self._device_name = "Sonoris Device"
        self._total_active_time = 0  # Em segundos
        self._total_conversations = 0
        self._start_time = time.time()
        
        # Certifica que o diretório de dados existe
        if not os.path.exists(self.data_dir):
            try:
                os.makedirs(self.data_dir)
            except Exception as e:
                print(f"Erro ao criar diretório de dados: {e}")
        
        # Carrega os dados salvos, se existirem
        self._load_data()
    
    def _load_data(self):
        """Carrega os dados do arquivo JSON."""
        if os.path.exists(self.info_file):
            try:
                with open(self.info_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._device_name = data.get('device_name', self._device_name)
                    self._total_active_time = data.get('total_active_time', 0)
                    self._total_conversations = data.get('total_conversations', 0)
            except Exception as e:
                print(f"Erro ao carregar dados do dispositivo: {e}")
    
    def _save_data(self):
        """Salva os dados no arquivo JSON."""
        try:
            data = {
                'device_name': self._device_name,
                'total_active_time': self._total_active_time,
                'total_conversations': self._total_conversations
            }
            
            with open(self.info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar dados do dispositivo: {e}")
    
    @property
    def device_name(self):
        """Nome do dispositivo."""
        return self._device_name
    
    @device_name.setter
    def device_name(self, value):
        """Define o nome do dispositivo (apenas pelo Bluetooth)."""
        if value and isinstance(value, str):
            self._device_name = value
            self._save_data()
    
    @property
    def total_active_time(self):
        """Tempo total ativo em segundos."""
        # Atualiza o tempo com a sessão atual
        current_session_time = (time.time() - self._start_time)  # Em segundos
        return self._total_active_time + int(current_session_time)
    
    def update_active_time(self):
        """Atualiza o tempo ativo total."""
        current_session_time = (time.time() - self._start_time)  # Em segundos
        self._total_active_time += int(current_session_time)
        self._start_time = time.time()  # Reinicia o contador
        self._save_data()
    
    @property
    def total_conversations(self):
        """Total de conversas."""
        return self._total_conversations
    
    def increment_conversation_counter(self):
        """Incrementa o contador de conversas."""
        self._total_conversations += 1
        self._save_data()
        return self._total_conversations
    
    def get_device_data_for_bluetooth(self):
        """Retorna um dicionário com os dados para envio via Bluetooth."""
        return {
            'device_name': self.device_name,
            'total_active_time': self.total_active_time,
            'total_conversations': self.total_conversations
        }