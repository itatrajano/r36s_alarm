#!/bin/bash
# ==============================================================================
# Script de Instalação e Teste do Relógio Despertador R36S
# Executável a partir do menu "Ports" do EmulationStation ou Terminal
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

if [ -f "$controlfolder/control.txt" ]; then
  source "$controlfolder/control.txt"
  [ -f "${controlfolder}/mod_${CFW_NAME}.txt" ] && source "${controlfolder}/mod_${CFW_NAME}.txt"
  get_controls
fi

# 2. Localizar o terminal do display físico do R36S
CUR_TTY="${CUR_TTY:-/dev/tty1}"
[ ! -c "$CUR_TTY" ] && CUR_TTY="/dev/tty0"
[ ! -c "$CUR_TTY" ] && CUR_TTY="/dev/tty"

# 3. Determinar os diretórios
if [ -n "$directory" ] && [ -d "/$directory/ports/relogio" ]; then
  SCRIPT_DIR="/$directory/ports"
  GAMEDIR="/$directory/ports/relogio"
else
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  GAMEDIR="$SCRIPT_DIR/relogio"
fi

# 4. Redirecionar saída para o display físico do console
if [ -c "$CUR_TTY" ]; then
  printf "\033c" > "$CUR_TTY"
  exec > "$CUR_TTY" 2>&1
fi

echo "================================================="
echo "   INSTALADOR DO RELÓGIO DESPERTADOR R36S       "
echo "================================================="
echo ""
echo "[1/4] Atribuindo permissões de execução..."
chmod +x "$SCRIPT_DIR/Relogio.sh" 2>/dev/null
chmod +x "$SCRIPT_DIR/Instalar_Relogio.sh" 2>/dev/null
chmod +x "$SCRIPT_DIR/Desinstalar_Relogio.sh" 2>/dev/null
chmod +x "$GAMEDIR/main.py" 2>/dev/null
echo "      Permissões configuradas com sucesso."
echo ""

echo "[2/4] Verificando arquivos e assets..."
[ -f "$GAMEDIR/fonts/ShareTechMono.ttf" ] && echo "      [OK] Fonte ShareTechMono.ttf encontrada."
[ -f "$GAMEDIR/sounds/alarm.wav" ] && echo "      [OK] Som alarm.wav encontrado."
[ -d "$GAMEDIR/sdl2" ] && echo "      [OK] Biblioteca PySDL2 embutida encontrada."
echo ""

echo "[3/4] Verificando Python 3..."
if command -v python3 >/dev/null 2>&1; then
    PY_VER=$(python3 --version 2>&1)
    echo "      [OK] $PY_VER detectado."
else
    echo "      [ERRO] python3 não encontrado!"
fi
echo ""

echo "[4/4] Verificando motor gráfico..."
export PYSDL2_DLL_PATH="/usr/lib"
if python3 -c "import sys; sys.path.insert(0, '$GAMEDIR'); import sdl2; print('[OK] PySDL2 carregado com sucesso!')" 2>/dev/null; then
    echo "      [OK] Suporte nativo PySDL2 verificado!"
elif python3 -c "import pygame; print('[OK] Pygame carregado!')" 2>/dev/null; then
    echo "      [OK] Suporte Pygame verificado!"
else
    echo "      [AVISO] Verificando ambiente de execução..."
fi
echo ""

echo "================================================="
echo "   INSTALAÇÃO CONCLUÍDA COM SUCESSO!            "
echo "================================================="
echo ""
echo "O atalho 'Relogio' agora pode ser aberto pelo     "
echo "menu PORTS do seu R36S.                          "
echo ""
echo "Retornando ao menu em 5 segundos..."
sleep 5

if [ -c "$CUR_TTY" ]; then
  printf "\033c" > "$CUR_TTY"
fi
exit 0
