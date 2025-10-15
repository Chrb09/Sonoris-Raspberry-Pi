import os
import json
from utils.colors import parse_color
from kivy.core.text import LabelBase

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# ==============================
# VARIÁVEIS DE CONFIGURAÇÃO
# ==============================

FONT_NAME = cfg.get("fonte", None) 
TEXT_COLOR = parse_color(cfg.get("color_black", None), default=(1,1,1,1))
WHITE_COLOR = parse_color(cfg.get("color_background", None), default=(1,1,1,1))
BLUE_COLOR = parse_color(cfg.get("color_blue", None), default=(0.168, 0.168, 0.168, 1))
icons_dir = os.path.join(BASE_DIR, "assets", "icons")

# registra fonte customizada se possível
if FONT_NAME and os.path.exists(os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf")):
    LabelBase.register(name=FONT_NAME, fn_regular=os.path.join(BASE_DIR, "fonts", f"{FONT_NAME}.ttf"))