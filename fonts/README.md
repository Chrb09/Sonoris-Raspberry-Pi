# Estrutura de Fontes

Este diretório deve conter os arquivos de fonte utilizados pela aplicação Sonoris.

## Famílias de Fontes Suportadas

A aplicação suporta três famílias de fontes:

- **Inter**
- **Roboto**
- **Poppins**

## Estrutura de Arquivos Esperada

Para cada família de fonte, os arquivos devem seguir o padrão: `{Família}-{Peso}.ttf`

### Pesos Suportados

| Peso | Nome do Arquivo            | Descrição           |
| ---- | -------------------------- | ------------------- |
| 100  | `{Família}-Thin.ttf`       | Extra fino          |
| 200  | `{Família}-ExtraLight.ttf` | Extra leve          |
| 300  | `{Família}-Light.ttf`      | Leve                |
| 400  | `{Família}-Regular.ttf`    | Regular (padrão)    |
| 500  | `{Família}-Medium.ttf`     | Médio               |
| 600  | `{Família}-SemiBold.ttf`   | Semi-negrito        |
| 700  | `{Família}-Bold.ttf`       | Negrito             |
| 800  | `{Família}-ExtraBold.ttf`  | Extra negrito       |
| 900  | `{Família}-Black.ttf`      | Black (mais pesado) |

## Exemplo de Estrutura Completa

```
fonts/
├── Inter-Thin.ttf           (peso 100)
├── Inter-ExtraLight.ttf     (peso 200)
├── Inter-Light.ttf          (peso 300)
├── Inter-Regular.ttf        (peso 400)
├── Inter.ttf                (fallback para peso 400)
├── Inter-Medium.ttf         (peso 500)
├── Inter-SemiBold.ttf       (peso 600)
├── Inter-Bold.ttf           (peso 700)
├── Inter-ExtraBold.ttf      (peso 800)
├── Inter-Black.ttf          (peso 900)
│
├── Roboto-Thin.ttf          (peso 100)
├── Roboto-Light.ttf         (peso 300)
├── Roboto-Regular.ttf       (peso 400)
├── Roboto.ttf               (fallback)
├── Roboto-Medium.ttf        (peso 500)
├── Roboto-Bold.ttf          (peso 700)
├── Roboto-Black.ttf         (peso 900)
│
├── Poppins-Thin.ttf         (peso 100)
├── Poppins-ExtraLight.ttf   (peso 200)
├── Poppins-Light.ttf        (peso 300)
├── Poppins-Regular.ttf      (peso 400)
├── Poppins.ttf              (fallback)
├── Poppins-Medium.ttf       (peso 500)
├── Poppins-SemiBold.ttf     (peso 600)
├── Poppins-Bold.ttf         (peso 700)
├── Poppins-ExtraBold.ttf    (peso 800)
└── Poppins-Black.ttf        (peso 900)
```

## Configuração em `env.py`

Para alterar a fonte e o peso, edite as seguintes variáveis em `env.py`:

```python
FONT_FAMILY = "Inter"  # Opções: "Inter", "Roboto", "Poppins"
FONT_WEIGHT = 400      # Valores: 100-900
```

## Fallback

Se o peso específico não for encontrado, o sistema tentará:

1. `{Família}-Regular.ttf`
2. `{Família}.ttf`

Se nenhum arquivo for encontrado, uma mensagem de aviso será exibida no console.

## Download de Fontes

- **Inter**: https://fonts.google.com/specimen/Inter
- **Roboto**: https://fonts.google.com/specimen/Roboto
- **Poppins**: https://fonts.google.com/specimen/Poppins

Certifique-se de baixar todos os pesos disponíveis para cada família.
