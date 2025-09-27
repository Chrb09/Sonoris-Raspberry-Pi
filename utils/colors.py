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
        # normaliza cada componente separadamente
        norm = []
        for v in vals[:4]:
            if isinstance(v, int) or (isinstance(v, float) and v > 1.0):
                norm.append(float(v) / 255.0)
            else:
                norm.append(float(v))
        return tuple(norm)

    # string hex
    if isinstance(value, str):
        value = value.strip()
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

        # rgba() ou rgb()
        m = re.match(r'rgba?\s*\(\s*([^\)]+)\)', value, re.I)
        if m:
            parts = [p.strip() for p in m.group(1).split(',')]
            try:
                nums = []
                for i, p in enumerate(parts):
                    if '%' in p:
                        nums.append(float(p.strip('%')) * 2.55)  # percent -> 0-255
                    else:
                        nums.append(float(p))
                if len(nums) == 3:
                    nums.append(1.0)
                # normaliza cada canal se >1
                norm = []
                for n in nums[:4]:
                    if n > 1:
                        norm.append(n/255.0)
                    else:
                        norm.append(n)
                return tuple(norm)
            except Exception:
                return default

    return default
