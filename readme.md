<div align=center>
  
![Logo](assets/banner_logo_git.png)

</div>

<b>Sonoris</b> é um projeto, constituido por um aplicativo e um dispositivo, desenvolvido ao longo de 2025 em parceria com uma empresa, como parte do Trabalho de Conclusão de Curso (TCC) do curso de **Desenvolvimento de Sistemas AMS da Etec da Zona Leste**. **[Landing Page da Sonoris](https://sonoris.vercel.app/)**

# Sumário

- [🌟 Sobre a Sonoris](#-sobre-a-sonoris)
- [📖 Funcionalidades do dispositivo](#-funcionalidades-do-dispositivo)
- [💻 Tecnologias Utilizadas](#-tecnologias-utilizadas)
  - [Telas](#telas)
  - [Transcrição](#transcrição)
  - [Servidor BLE](#servidor-ble)
- [🚀 Como rodar o projeto](#-como-rodar-o-projeto)
- [📁 Outros repositórios](#-outros-repositórios)
- [😀 Contribuidores](#-contribuidores)

## 🌟 Sobre a Sonoris

O projeto tem como propósito facilitar a comunicação e promover a inclusão de **pessoas com deficiência auditiva**, principalmente em contextos profissionais e acadêmicos, utilizando transcrição de voz e opções de customização.

<div align=center>
  
![Logo](assets/dispositivo.png)

</div>

## 📖 Funcionalidades do dispositivo

O dispositivo IoT que capta a fala humana por meio de um microfone omnidirecional e realiza a transcrição em um microcomputador Raspberry Pi. As legendas geradas são exibidas em um display LCD e também enviadas ao aplicativo mobile via Bluetooth.

Caso o usuário prefira, é possível ativar o modo privado, garantindo que as conversas captadas não sejam armazenadas no aplicativo.

Também é possível customizar as legendas do dispositivo, ajustando fonte, tamanho, espaçamento horizontal e outras preferências pelo aplicativo.

## 💻 Tecnologias utilizadas

### Telas:

![python](https://img.shields.io/badge/python-0175C2?style=for-the-badge&logo=python&logoColor=white)
![kivy](https://img.shields.io/badge/kivy-0175C2?style=for-the-badge&logo=python&logoColor=white)

### Transcrição:

![python](https://img.shields.io/badge/python-0175C2?style=for-the-badge&logo=python&logoColor=white)
![vosk](https://img.shields.io/badge/vosk-0175C2?style=for-the-badge&logo=python&logoColor=white)
![webrtcvad](https://img.shields.io/badge/webrtcvad-0175C2?style=for-the-badge&logo=python&logoColor=white)

### Servidor BLE:

![Bluetooth](https://img.shields.io/badge/Bluetooth_Low_Energy-0175C2?style=for-the-badge&logo=bluetooth&logoColor=white)
![Bluetooth](https://img.shields.io/badge/bluez_peripheral-0175C2?style=for-the-badge&logo=bluetooth&logoColor=white)

## 🚀 Como rodar o projeto

```sh
# clone o repositório
git clone https://github.com/Chrb09/Sonoris-Raspberry-Pi.git

# acesse o diretório
cd Sonoris-RaspberryPi
```

Baixe o [vosk-model-pt-fb-v0.1.1-20220516_2113](https://alphacephei.com/vosk/models/vosk-model-pt-fb-v0.1.1-20220516_2113.zip), extraia os conteúdos em uma pasta chamada 'modelLarge' na root do projeto.

![Estrutura da pasta](assets/modelLarge.png)

```python
# crie o ambiente virtual
python -m venv meu_ambiente_virtual

# ative o ambiente virtual
source meu_ambiente_virtual/bin/activate

# instale as dependências
pip install -r requirements.txt

# execute o script principal
python main.py
```

## 📁 Outros repositórios

- <b> [Aplicativo](https://github.com/Beatriz02020/Sonoris-iot-app-transcricao) </b><br>
- <b> [Landing Page](https://github.com/Amanda093/Sonoris) </b><br>
- <b> [Documentação](https://github.com/Beatriz02020/Sonoris-iot-app-transcricao/tree/documentation) </b>

## 😀 Contribuidores

<div align=center>
<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Amanda093">
        <img src="https://avatars.githubusercontent.com/u/138123400?v=4" width="100px;" alt="Amanda - Github"/><br>
        <sub>
          <b>Amanda</b>
        </sub> <br>
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/Beatriz02020">
        <img src="https://avatars.githubusercontent.com/u/133404301?v=4" width="100px;" alt="Beatriz - Github"/><br>
        <sub>
          <b>Beatriz</b>
        </sub> <br>
      </a>
    </td>
    </td>
    <td align="center">
      <a href="https://github.com/Chrb09">
        <img src="https://avatars.githubusercontent.com/u/132484542?v=4" width="100px;" alt="Carlos - Github"/><br>
        <sub>
            <b>Carlos</b>
          </sub> <br>
      </a>
    </td>
  </tr>
</table>
</div>
<br>
