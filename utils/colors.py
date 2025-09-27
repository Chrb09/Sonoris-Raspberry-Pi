# colors.py
# funções para manipulação de cores
import re

from utils.helpers import _clamp

# converte várias representações de cor para RGBA (0-1 floats)
def parse_color(raw, default=(0,0,0,1)):
    if raw is None:
        return default
    # hex string
    if isinstance(raw, str):
        s = raw.strip().lstrip('#')
        if len(s) == 6:
            try:
                r = int(s[0:2], 16)/255.0
                g = int(s[2:4], 16)/255.0
                b = int(s[4:6], 16)/255.0
                return (r, g, b, 1.0)
            except Exception:
                return default
        if len(s) == 8:
            try:
                r = int(s[0:2], 16)/255.0
                g = int(s[2:4], 16)/255.0
                b = int(s[4:6], 16)/255.0
                a = int(s[6:8], 16)/255.0
                return (r, g, b, a)
            except Exception:
                return default
        return default

    # list/tuple
    if isinstance(raw, (list, tuple)):
        vals = list(raw)
        if len(vals) == 3:
            vals.append(1)
        out = []
        for v in vals[:4]:
            try:
                fv = float(v)
            except Exception:
                fv = 0.0
            if fv > 1.0:
                fv = fv / 255.0
            out.append(_clamp(fv))
        while len(out) < 4:
            out.append(1.0)
        return tuple(out)

    return default
