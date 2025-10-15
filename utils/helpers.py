# helpers.py
# funções auxiliares diversas

# limita valor entre 0.0 e 1.0
def _clamp(v, lo=0.0, hi=1.0):
    try:
        fv = float(v)
    except Exception:
        return lo
    return max(lo, min(hi, fv))

# ativa modo privado e fecha popup
def enable_private_and_close(context_self):
    print ("Ativando modo privado e fechando popup")
    # ativa modo privado
    try:
        context_self.private_mode = True
    except Exception as e:
        print("Erro ao ativar private_mode:", e)
    
    # fecha popup
    try:
        context_self.popup.dismiss()
    except Exception as e:
        print("Erro ao fechar popup:", e)