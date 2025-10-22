"""
Configurações da interface do usuário.
Este módulo contém constantes e configurações usadas pela UI.
"""

import os
# Importamos Window apenas quando necessário, dentro da função init_window_settings
from env import FONT_NAME, TEXT_COLOR, WHITE_COLOR, BLUE_COLOR, icons_dir

# Configurações de janela
DEFAULT_WINDOW_SIZE = (720, 480)  # tamanho inicial da janela
WINDOW_FULLSCREEN = False  # se True, será 'auto'

def init_window_settings():
    """
    Inicializa as configurações da janela.
    Esta função deve ser chamada após a inicialização do Kivy.
    """
    # Importamos Window apenas quando esta função é chamada
    from kivy.core.window import Window
    
    Window.size = DEFAULT_WINDOW_SIZE
    if WINDOW_FULLSCREEN:
        Window.fullscreen = 'auto'
    Window.clearcolor = WHITE_COLOR

# Configurações de transcrição
FONT_SIZE_PARTIAL = 35
MAX_PARTIAL_CHARS = 120  # máximo de caracteres do texto parcial
PARTIAL_RESET_MS = 3000  # tempo para resetar o texto parcial (ms)

# Configuração de texto parcial
def truncate_partial(text, max_chars=MAX_PARTIAL_CHARS, partial_threshold=0.6):
    """
    Função para truncar texto parcial com reticências
    
    Args:
        text: O texto a ser truncado
        max_chars: Número máximo de caracteres permitidos
        partial_threshold: Limiar para corte em espaço (0.0-1.0)
    
    Returns:
        Texto truncado e capitalizado
    """
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t.capitalize()
    cut = t[:max_chars]
    last_space = cut.rfind(' ')
    if last_space > int(max_chars * partial_threshold):
        cut = cut[:last_space]
    return (cut + '…').capitalize()

# Caminhos para recursos de interface
ICON_PATHS = {
    'pause': os.path.join(icons_dir, "pause.png"),
    'resume': os.path.join(icons_dir, "resume.png"),
    'response': os.path.join(icons_dir, "response.png"),
    'private01': os.path.join(icons_dir, "private01.png"),  # modo privado inativo
    'private02': os.path.join(icons_dir, "private02.png"),  # modo privado ativo
    'back': os.path.join(icons_dir, "back.png"),
    'lock': os.path.join(icons_dir, "lock.png"),
    'plus': os.path.join(icons_dir, "plus.png"),
    'app_icon': os.path.join(icons_dir, "app_icon.png")
}

# Textos de interface comuns
UI_TEXTS = {
    'app_title': "Transcrição de Voz Sonoris",
    'waiting_text': "Aguardando...",
    'pause_btn': "[b]Pausar[/b]",
    'resume_btn': "[b]Retomar[/b]",
    'responses_btn': "[b]Respostas[/b]",
    'private_inactive_btn': "[b]Privado?[/b]",
    'private_active_btn': "[b]Privado[/b]",
    'new_conversation_btn': "[b]Nova conversa[/b]",
    'back_btn': "[b]Voltar[/b]",
    'private_popup_title': "[b]Deseja ativar o modo privado?[/b]",
    'private_popup_subtitle': "As transcrições não serão salvas até você iniciar \n uma nova conversa.",
    'yes_btn': "Sim",
    'no_btn': "Não"
}