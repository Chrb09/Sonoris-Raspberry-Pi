# config.py 
import os
import json
from utils.colors import parse_color
from kivy.core.text import LabelBase

# configurações do aplicativo
BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# configurações de UI (config.json)
FONT_NAME = cfg.get("fonte", None)

FONT_SIZE_HISTORY = cfg.get("tamanho_historico", 20)
BACKGROUND_COLOR = parse_color(cfg.get("color_background500", None), default=(0,0,0,1))
TEXT_COLOR = parse_color(cfg.get("color_white100", None), default=(1,1,1,1))
MAX_PARTIAL_CHARS = int(cfg.get("max_partial_chars", 240))
PARTIAL_UPDATE_MIN_MS = int(cfg.get("partial_update_min_ms", 80))
HISTORY_MAX_LINES = int(cfg.get("history_max_lines", 200))
PARTIAL_RESET_MS = int(cfg.get("partial_reset_ms", 3000))

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))
