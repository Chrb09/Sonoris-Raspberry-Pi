# colors.py
# funções para manipulação de cores

# converte várias representações de cor para RGBA (0-1 floats)
import re

def parse_color(value, default=(0,0,0,1)):
    """Retorna (r,g,b,a) com valores float entre 0 e 1.
       Aceita:
       - None -> retorna default
       - lista/tupla de 3/4 ints(0-255) ou floats(0-1)
       - hex '#RRGGBB' ou '#RRGGBBAA'
       - 'rgb(r,g,b)' ou 'rgba(r,g,b,a)'
    """
    if value is None:
        return default

    # já é lista/tupla
    if isinstance(value, (list, tuple)):
        vals = list(value)
        if len(vals) == 3:
            vals.append(1)
        # se valores inteiros maiores que 1 -> normaliza
        if any(isinstance(v, (int,)) and v > 1 for v in vals) or any((isinstance(v, float) and v > 1.0) for v in vals):
            try:
                vals = [float(v) / 255.0 for v in vals]
            except Exception:
                return default
        vals = [float(v) for v in vals]
        return tuple(vals[:4])

    # string hex
    if isinstance(value, str):
        value = value.strip()
        # hex
        if value.startswith('#'):
            hexv = value[1:]
            if len(hexv) == 6:
                r = int(hexv[0:2], 16)
                g = int(hexv[2:4], 16)
                b = int(hexv[4:6], 16)
                a = 255
            elif len(hexv) == 8:
                r = int(hexv[0:2], 16)
                g = int(hexv[2:4], 16)
                b = int(hexv[4:6], 16)
                a = int(hexv[6:8], 16)
            else:
                return default
            return (r/255.0, g/255.0, b/255.0, a/255.0)

        # rgba() or rgb()
        m = re.match(r'rgba?\s*\(\s*([^\)]+)\)', value, re.I)
        if m:
            parts = [p.strip() for p in m.group(1).split(',')]
            try:
                nums = []
                for p in parts:
                    if '%' in p:
                        nums.append(float(p.strip('%')) * 2.55)  # percent -> 0-255
                    else:
                        nums.append(float(p))
                if len(nums) == 3:
                    nums.append(1.0)
                # se alpha está em 0..1, ok; se alfa >1 assumimos 0-255
                if nums and nums[0] > 1:
                    nums = [n / 255.0 for n in nums]
                return tuple(nums[:4])
            except Exception:
                return default

    # fallback
    return default