# Relógio Despertador Digital para R36S (Ports)

Um relógio despertador digital com visual retrô, desenvolvido sob medida para o console portátil **R36S** (ArkOS / AmberELEC / TheRA), na resolução nativa de **640x480** pixels.

---

## 🎮 Controles no R36S

| Botão | Função no Modo Normal | Função no Modo de Edição |
| :--- | :--- | :--- |
| **A** | Abre o painel de **Edição do Alarme** | **Salvar e Confirmar** alterações |
| **B** | **Silencia/Ativa** o alarme (ou para o bipe) | **Cancelar** e fechar sem salvar |
| **X ou Y** | - | Alterna status do alarme (**ATIVO** / **INATIVO**) |
| **D-Pad Cima / Baixo** | - | Ajusta a **Hora** (+1H/-1H) ou **Minuto** (+1M/-1M) |
| **D-Pad Esquerda / Direita** | - | Alterna seleção entre **Hora** e **Minuto** |
| **L1 / R1** | Alterna a **Cor da Fonte** (6 paletas) | Alterna a **Cor da Fonte** |
| **SELECT + START** | **Sair** do aplicativo e retornar ao menu | Fecha o aplicativo |

### 🎨 Paletas de Cores Disponíveis (L1 / R1):
1. **CYAN GLOW** (`#00f3ff`)
2. **GREEN MATRIX** (`#39ff14`)
3. **AMBER RETRO** (`#ffb703`)
4. **RED FLAME** (`#ff3366`)
5. **CLEAN WHITE** (`#f8fafc`)
6. **PURPLE NEON** (`#d946ef`)

---

## 📦 Como Instalar no R36S

1. Conecte o cartão MicroSD do seu R36S (partição `EASYROMS` ou `ROMS`) ao computador.
2. Navegue até a pasta **`ports/`** (geralmente `EASYROMS/ports/` ou `roms/ports/`).
3. Copie o conteúdo da pasta `ports/` deste projeto para dentro da pasta `ports/` do cartão:
   ```
   ports/
   ├── Instalar_Relogio.sh
   ├── Relogio.sh
   ├── Desinstalar_Relogio.sh
   └── relogio/
       ├── main.py
       ├── config.json
       ├── relogio.gptk
       ├── fonts/
       │   └── ShareTechMono.ttf
       └── sounds/
           └── alarm.wav
   ```
4. Insira o cartão de volta no R36S e ligue o console.
5. Acesse o menu **PORTS** no EmulationStation:
   - Execute **`Instalar Relogio`** uma única vez para configurar permissões.
   - A partir de então, basta abrir **`Relogio`** para usar o despertador!

---

## ⏰ Comportamento do Alarme

- Quando o horário atual atinge a hora e minuto configurados e o alarme estiver **ATIVO**:
  - O indicador de alarme piscará em alerta vermelho/âmbar.
  - O som característico retrô de despertador digital tocará em repetição.
  - Para silenciar/desligar o toque, basta pressionar o botão **B**.
- O horário do alarme e o tema escolhido são salvos automaticamente no arquivo `config.json`, sendo mantidos mesmo após desligar o console.

---

## 🗑️ Como Desinstalar

Caso deseje remover o relógio:
1. No menu **PORTS** do R36S, selecione e execute o script **`Desinstalar Relogio`**.
2. O script removerá automaticamente o executável `Relogio.sh`, os arquivos da pasta `relogio/` e a si próprio, deixando seu console limpo.


---
>**AI sloped with subsidized tokens and love. 🤖💛**
