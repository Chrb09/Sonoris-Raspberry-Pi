# helpers.py
# funções auxiliares diversas

# limita valor entre 0.0 e 1.0
def _clamp(v, lo=0.0, hi=1.0):
    try:
        fv = float(v)
    except Exception:
        return lo
    return max(lo, min(hi, fv))