# helpers.py
# funções auxiliares diversas
import os

# limita valor entre 0.0 e 1.0
def _clamp(v, lo=0.0, hi=1.0):
    try:
        fv = float(v)
    except Exception:
        return lo
    return max(lo, min(hi, fv))

# ativa modo privado e fecha popup
# TODO ajustar para apresentar o novo icone
def enable_private_and_close(context_self):
    print ("Ativando modo privado e fechando popup")
    # ativa modo privado
    try:
        context_self.private_mode = True
    except Exception as e:
        print("Erro ao ativar private_mode:", e)
    
    # atualiza ícone do botão private_btn para private02.png
    try:
        btn = getattr(context_self, 'private_btn', None)
        if btn:
            try:
                btn.icon_src = os.path.join(icons_dir, "private02.png")

            except Exception:
                pass
    except Exception as e:
        print("Erro ao atualizar ícone do private_btn:", e)

    # fecha popup
    try:
        context_self.popup.dismiss()
    except Exception as e:
        print("Erro ao fechar popup:", e)