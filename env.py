import os
from kivy.core.text import LabelBase

BASE_DIR = os.path.dirname(__file__)

# ==============================
# VARIÁVEIS DE CONFIGURAÇÃO
# ==============================

# Cores principais (valores já normalizados para Kivy: 0-1)
TEXT_COLOR = (0.168, 0.168, 0.168, 1)  # Cor de texto do partial e history (cinza escuro)
BACKGROUND_COLOR = (1, 1, 1, 1)  # Cor de fundo do layout principal (branco)

# Tamanhos de fonte
FONT_SIZE = 36  # Tamanho base da fonte (36 é tamanho inicial)
FONT_SIZE_PARTIAL = FONT_SIZE  # Tamanho da fonte do texto parcial
FONT_SIZE_HISTORY = int(FONT_SIZE * 0.65)  # 35% menor que o partial (65% do tamanho base)

# Font Weight (peso da fonte)
# Valores suportados: 100 (Thin), 200 (ExtraLight), 300 (Light), 400 (Regular), 500 (Medium), 600 (SemiBold), 700 (Bold), 800 (ExtraBold), 900 (Black)
FONT_WEIGHT = 400  # Peso da fonte (400 = Regular)

# Família da fonte
FONT_FAMILY = "Inter" # Opções disponíveis: "Inter", "Roboto", "Poppins"

# Line Height (altura da linha)
LINE_HEIGHT = 1.2  # Multiplicador da altura da linha (0.8 = mais compacta, 1.2 = sem espaçamento extra, 1.6 = 60% mais espaço)

icons_dir = os.path.join(BASE_DIR, "assets", "icons")

# Mapeamento de font weights para nomes de arquivo
FONT_WEIGHT_MAP = {
    100: "Thin",
    200: "ExtraLight",
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "SemiBold",
    700: "Bold",
    800: "ExtraBold",
    900: "Black"
}

# Determina o nome do arquivo de fonte baseado no peso e família
def get_font_file(family="Inter", weight=400):
    """
    Retorna o caminho do arquivo de fonte baseado na família e peso especificados.
    
    Args:
        family: Família da fonte ("Inter", "Roboto", "Poppins")
        weight: Peso da fonte (100-900)
    
    Returns:
        Caminho do arquivo de fonte ou None se não encontrado
    """
    weight_name = FONT_WEIGHT_MAP.get(weight, "Regular")
    
    # Tenta encontrar o arquivo específico da família e peso
    font_path = os.path.join(BASE_DIR, "fonts", f"{family}-{weight_name}.ttf")
    
    # Se não encontrar o peso específico, tenta o Regular da mesma família
    if not os.path.exists(font_path):
        font_path = os.path.join(BASE_DIR, "fonts", f"{family}-Regular.ttf")
        if not os.path.exists(font_path):
            # Fallback: tenta apenas o nome da família
            font_path = os.path.join(BASE_DIR, "fonts", f"{family}.ttf")
            if not os.path.exists(font_path):
                return None
    
    return font_path

# Nome da fonte registrada (usa a família escolhida)
FONT_NAME = FONT_FAMILY

# Registra fonte customizada com a família e peso especificados
font_file = get_font_file(FONT_FAMILY, FONT_WEIGHT)
if font_file:
    LabelBase.register(name=FONT_NAME, fn_regular=font_file)
else:
    print(f"[ENV] Aviso: Arquivo de fonte não encontrado para '{FONT_FAMILY}' com peso {FONT_WEIGHT}")

# Registra pesos adicionais para uso específico em componentes
# Isso permite que botões usem Bold enquanto texto normal usa Regular, etc.
_registered_weights = {FONT_WEIGHT}  # Já registramos o peso principal

def register_font_weight(weight):
    """
    Registra um peso específico da fonte configurada se ainda não foi registrado.
    
    Args:
        weight: Peso da fonte (100-900)
    
    Returns:
        Nome da fonte registrada para esse peso
    """
    # Se for o mesmo peso já registrado como padrão, retorna o nome padrão
    if weight == FONT_WEIGHT:
        _registered_weights.add(weight)
        return FONT_NAME
    
    weight_name_suffix = FONT_WEIGHT_MAP.get(weight, 'Regular')
    font_name = f"{FONT_FAMILY}-{weight_name_suffix}"
    
    # Se já foi registrado, apenas retorna o nome
    if weight in _registered_weights:
        return font_name
    
    font_file = get_font_file(FONT_FAMILY, weight)
    if font_file:
        LabelBase.register(name=font_name, fn_regular=font_file)
        _registered_weights.add(weight)
        return font_name
    else:
        # Se não encontrar, usa o peso padrão já registrado
        print(f"[ENV] Aviso: Peso {weight} ({weight_name_suffix}) não encontrado, usando peso padrão {FONT_WEIGHT}")
        return FONT_NAME

# Registra pesos comumente usados na UI
FONT_NAME_BOLD = register_font_weight(700)      # Para botões e títulos
FONT_NAME_SEMIBOLD = register_font_weight(600)  # Para subtítulos
FONT_NAME_MEDIUM = register_font_weight(500)    # Para texto de ênfase
FONT_NAME_REGULAR = register_font_weight(400)   # Para texto normal (fallback)
