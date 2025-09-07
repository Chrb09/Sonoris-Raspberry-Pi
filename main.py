# main.py
import json
import os
from transcriber import Transcriber
from ui import TranscriberApp

BASE_DIR = os.path.dirname(__file__)
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
else:
    cfg = {}

# create transcriber
transcriber = Transcriber(cfg)

# create and run app, passing transcriber
app = TranscriberApp(transcriber=transcriber)
app.run()
