#!/bin/bash
# ==============================================================================
# PORTMASTER: relogio.zip, Relogio.sh
# R36S Digital Clock & Alarm Launcher
# ==============================================================================

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

# 1. Localizar pasta do PortMaster
if [ -d "/opt/system/Tools/PortMaster/" ]; then
  controlfolder="/opt/system/Tools/PortMaster"
elif [ -d "/opt/tools/PortMaster/" ]; then
  controlfolder="/opt/tools/PortMaster"
elif [ -d "$XDG_DATA_HOME/PortMaster/" ]; then
  controlfolder="$XDG_DATA_HOME/PortMaster"
elif [ -d "/roms2/tools/PortMaster/" ]; then
  controlfolder="/roms2/tools/PortMaster"
elif [ -d "/roms/tools/PortMaster/" ]; then
  controlfolder="/roms/tools/PortMaster"
elif [ -d "/roms2/ports/PortMaster/" ]; then
  controlfolder="/roms2/ports/PortMaster"
elif [ -d "/roms/ports/PortMaster/" ]; then
  controlfolder="/roms/ports/PortMaster"
else
  controlfolder="/roms/ports/PortMaster"
fi

# 2. Carregar configurações do ArkOS/PortMaster
if [ -f "$controlfolder/control.txt" ]; then
  source "$controlfolder/control.txt"
  [ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"
  get_controls
fi

# 3. Determinar o diretório do aplicativo no cartão primário ou secundário
if [ -n "$directory" ] && [ -d "/$directory/ports/relogio" ]; then
  GAMEDIR="/$directory/ports/relogio"
else
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  GAMEDIR="$SCRIPT_DIR/relogio"
fi

cd "$GAMEDIR" || exit 1

# 4. Gravar log completo de execução para diagnóstico
> "$GAMEDIR/log.txt" && exec > >(tee "$GAMEDIR/log.txt") 2>&1

echo "================================================="
echo "   Iniciando Relógio Despertador R36S           "
echo "   Data: $(date)                                "
echo "================================================="
echo "GAMEDIR: $GAMEDIR"
echo "controlfolder: $controlfolder"
echo "directory: $directory"
echo "CFW_NAME: $CFW_NAME"

# 5. Configurar variáveis de ambiente do sistema e SDL
export PYSDL2_DLL_PATH="/usr/lib"
export SDL_GAMECONTROLLERCONFIG="$sdl_controllerconfig"
export HOTKEY="select"
export ARKOS=1

# 6. Iniciar gptokeyb se disponível
GPTOKEYB_BIN=""
if [ -n "$GPTOKEYB" ] && [ -x "$GPTOKEYB" ]; then
  GPTOKEYB_BIN="$GPTOKEYB"
elif [ -x "/opt/system/gptokeyb" ]; then
  GPTOKEYB_BIN="/opt/system/gptokeyb"
elif [ -x "$controlfolder/gptokeyb" ]; then
  GPTOKEYB_BIN="$controlfolder/gptokeyb"
fi

if [ -n "$GPTOKEYB_BIN" ] && [ -f "$GAMEDIR/relogio.gptk" ]; then
  echo "Iniciando gptokeyb ($GPTOKEYB_BIN)..."
  export GPTOKEYB_ACTIVE=1
  $GPTOKEYB_BIN "python3" -c "$GAMEDIR/relogio.gptk" &
else
  export GPTOKEYB_ACTIVE=0
fi

# 7. Executar a aplicação com python3
echo "Executando python3 main.py..."
python3 main.py
EXIT_CODE=$?
echo "Aplicação encerrada com código: $EXIT_CODE"

# 8. Limpeza de processos ao sair
if [ -n "$GPTOKEYB_BIN" ]; then
  killall -9 gptokeyb 2>/dev/null
  if [ -n "$ESUDO" ]; then
    $ESUDO killall -9 gptokeyb 2>/dev/null
  fi
fi

CUR_TTY="${CUR_TTY:-/dev/tty1}"
[ ! -c "$CUR_TTY" ] && CUR_TTY="/dev/tty0"
if [ -c "$CUR_TTY" ]; then
  printf "\033c" > "$CUR_TTY"
fi

exit 0
