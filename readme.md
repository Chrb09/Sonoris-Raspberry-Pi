<div align=center>
  
![Logo](assets/banner_logo_git.png)

</div>

# Sumário

- [Sumário](#sumário)
  - [🌟 Sobre a Sonoris](#sobre-a-sonoris)
  - [💻 Tecnologias Utilizada](#tecnologias-utilizadas)
  - [🚀 Como rodar o projeto](#como-rodar-o-projeto)
  - [❓ FAQ](#FAQ)
  - [Contribuidores](#contribuidores)

## 🌟 Sobre a Sonoris

<b>Sonoris</b> é um aplicativo e dispositivo inovador, desenvolvido ao longo de 2025 em parceria com uma empresa, como parte do Trabalho de Conclusão de Curso (TCC) do curso de **Desenvolvimento de Sistemas AMS da Etec da Zona Leste**.

O projeto tem como propósito **facilitar a comunicação e promover a inclusão de pessoas surdas**, principalmente em contextos profissionais e acadêmicos.


### Principais funcionalidades
O projeto conta com um dispositivo IoT que capta a fala humana por meio de um microfone omnidirecional e realiza a transcrição em um microcomputador Raspberry Pi. As legendas geradas são exibidas em um display LCD e também enviadas ao aplicativo mobile via Bluetooth.

Caso o usuário prefira, é possível ativar o modo privado, garantindo que as conversas captadas não sejam armazenadas no aplicativo.

O aplicativo permite a criação e configuração de contas de usuário, além da personalização de categorias e respostas rápidas — que podem ser reproduzidas em áudio ao serem acionadas.

Também é possível customizar as legendas do dispositivo, ajustando fonte, tamanho, espaçamento horizontal e outras preferências. Quando o modo privado está desativado, as conversas captadas são sincronizadas e armazenadas no aplicativo.

### Todos os repositórios
- <b> [Aplicativo](https://github.com/Beatriz02020/Sonoris-iot-app-transcricao) </b><br>
- <b> [Dispositivo](https://github.com/Chrb09/Sonoris-RaspberryPi) </b><br>
- <b> [Documentação](https://github.com/Beatriz02020/Sonoris-iot-app-transcricao/tree/documentation?tab=readme-ov-file) </b>

## 💻 Tecnologias utilizadas
### Aplicativo

![dart](https://img.shields.io/badge/dart-0175C2?style=for-the-badge&logo=dart&logoColor=white)
![flutter](https://img.shields.io/badge/flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)

### Dispositivo
![python](https://img.shields.io/badge/python-0175C2?style=for-the-badge&logo=python&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=for-the-badge&logo=raspberrypi&logoColor=white)
![Bluetooth](https://img.shields.io/badge/Bluetooth-0082FC?style=for-the-badge&logo=bluetooth&logoColor=white)


## 🚀 Como rodar o projeto
### Aplicativo
```sh
# clone o repositório
git clone https://github.com/Beatriz02020/Sonoris-app.git

# acesse o diretório
cd sonoris-app

# instale as dependências
flutter pub get

# rode o aplicativo
flutter run
```

### Dispositivo
```sh
# clone o repositório
git clone https://github.com/Beatriz02020/Sonoris-device.git

# acesse o diretório
cd sonoris-device

# instale as dependências
pip install -r requirements.txt

# execute o script principal
python main.py
```

## ❓ FAQ
### **O design do projeto foi criado com qual ferramenta?**
O design da Sonoris foi elaborado utilizando a ferramenta de design [ **Figma**](www.figma.com/design/gNida4bnTd89phUpLydH89/Figma-Oficial-Sonoris?node-id=0-1&p=f&t=ruMUI67KIcO3A3is-0).


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

> Feito com ❤️ usando Flutter e Python.