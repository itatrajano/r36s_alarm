#!/bin/bash
# ==============================================================================
# Script de Desinstalação do Relógio Despertador para o R36S
# Executável a partir do menu "Ports" do EmulationStation ou Terminal
# ==============================================================================

XDG_DATA_HOME=${XDG_DATA_HOME:-$HOME/.local/share}

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
else
  controlfolder="/roms/ports/PortMaster"
fi

if [ -f "$controlfolder/control.txt" ]; then
  source "$controlfolder/control.txt"
  [ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"
fi

CUR_TTY="${CUR_TTY:-/dev/tty1}"
[ ! -c "$CUR_TTY" ] && CUR_TTY="/dev/tty0"
[ ! -c "$CUR_TTY" ] && CUR_TTY="/dev/tty"

if [ -n "$directory" ] && [ -d "/$directory/ports/relogio" ]; then
  SCRIPT_DIR="/$directory/ports"
  GAMEDIR="/$directory/ports/relogio"
else
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  GAMEDIR="$SCRIPT_DIR/relogio"
fi

if [ -c "$CUR_TTY" ]; then
  printf "\033c" > "$CUR_TTY"
  exec > "$CUR_TTY" 2>&1
fi

echo "================================================="
echo "  DESINSTALANDO RELÓGIO DESPERTADOR R36S         "
echo "================================================="
echo ""

if [ -f "$SCRIPT_DIR/Relogio.sh" ]; then
    echo "[1/3] Removendo lançador Relogio.sh..."
    rm -f "$SCRIPT_DIR/Relogio.sh"
fi

if [ -d "$GAMEDIR" ]; then
    echo "[2/3] Removendo pasta relogio/ e arquivos..."
    rm -rf "$GAMEDIR"
fi

if [ -f "$SCRIPT_DIR/Instalar_Relogio.sh" ]; then
    echo "[3/3] Removendo script de instalação..."
    rm -f "$SCRIPT_DIR/Instalar_Relogio.sh"
fi

echo ""
echo "================================================="
echo "   DESINSTALAÇÃO CONCLUÍDA COM SUCESSO!          "
echo "================================================="
echo "Os arquivos foram completamente removidos da     "
echo "pasta /ports.                                    "
echo "Retornando ao menu em 3 segundos..."
sleep 3

rm -f "$SCRIPT_DIR/Desinstalar_Relogio.sh" 2>/dev/null

if [ -c "$CUR_TTY" ]; then
  printf "\033c" > "$CUR_TTY"
fi
exit 0
