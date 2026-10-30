#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R36S Digital Clock & Alarm
Design atualizado conforme novo modelo do Google Stitch (640x480).
Suporta Pygame e PySDL2 nativo (PortMaster) sem dependências externas no ArkOS.
"""

import os
import sys
import json
import time
import datetime
import ctypes

# Inserir diretório base no path do Python para encontrar a pasta sdl2/ embutida
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Configurar caminhos para bibliotecas dinâmicas do Linux no ArkOS
if "PYSDL2_DLL_PATH" not in os.environ:
    os.environ["PYSDL2_DLL_PATH"] = "/usr/lib"

FONTS_DIR = os.path.join(APP_DIR, "fonts")
SOUNDS_DIR = os.path.join(APP_DIR, "sounds")
CONFIG_FILE = os.path.join(APP_DIR, "config.json")
FONT_FILE = os.path.join(FONTS_DIR, "ShareTechMono.ttf")
ALARM_SOUND_FILE = os.path.join(SOUNDS_DIR, "alarm.wav")

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

THEMES = [
    {"name": "CYAN", "color": (0, 243, 255), "hex": "#00f3ff"},
    {"name": "GREEN MATRIX", "color": (57, 255, 20), "hex": "#39ff14"},
    {"name": "AMBER RETRO", "color": (255, 183, 3), "hex": "#ffb703"},
    {"name": "RED FLAME", "color": (255, 51, 102), "hex": "#ff3366"},
    {"name": "CLEAN WHITE", "color": (248, 250, 252), "hex": "#f8fafc"},
    {"name": "PURPLE NEON", "color": (217, 70, 239), "hex": "#d946ef"},
]

DIAS_SEMANA = [
    "SEGUNDA-FEIRA",
    "TERÇA-FEIRA",
    "QUARTA-FEIRA",
    "QUINTA-FEIRA",
    "SEXTA-FEIRA",
    "SÁBADO",
    "DOMINGO",
]
MESES = [
    "JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
    "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"
]


class Config:
    def __init__(self):
        self.alarm_hour = 7
        self.alarm_minute = 0
        self.alarm_active = True
        self.theme_index = 0
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.alarm_hour = int(data.get("alarm_hour", 7)) % 24
                    self.alarm_minute = int(data.get("alarm_minute", 0)) % 60
                    self.alarm_active = bool(data.get("alarm_active", True))
                    self.theme_index = int(data.get("theme_index", 0)) % len(THEMES)
            except Exception as e:
                print(f"[CONFIG] Erro ao carregar config.json: {e}")

    def save(self):
        try:
            data = {
                "alarm_hour": self.alarm_hour,
                "alarm_minute": self.alarm_minute,
                "alarm_active": self.alarm_active,
                "theme_index": self.theme_index,
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[CONFIG] Erro ao salvar config.json: {e}")


def get_battery_percentage():
    paths = [
        "/sys/class/power_supply/battery/capacity",
        "/sys/class/power_supply/axp20x-battery/capacity",
        "/sys/class/power_supply/rk817-battery/capacity",
        "/sys/class/power_supply/BAT0/capacity",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    val = int(f.read().strip())
                    return max(0, min(100, val))
            except Exception:
                pass
    return 100


# ==============================================================================
# MOTOR 1: PySDL2 NATIVO (Padrão do PortMaster e ArkOS no R36S)
# ==============================================================================
def run_pysdl2():
    import sdl2
    import sdl2.sdlttf as sdlttf
    import sdl2.sdlmixer as sdlmixer

    print("[MOTOR] Inicializando motor PySDL2 nativo...")
    gptokeyb_active = os.environ.get("GPTOKEYB_ACTIVE") == "1"
    init_flags = sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO
    if not gptokeyb_active:
        init_flags |= sdl2.SDL_INIT_JOYSTICK

    if sdl2.SDL_Init(init_flags) != 0:
        print(f"[ERRO] Falha ao inicializar SDL2: {sdl2.SDL_GetError()}")
        return False

    sdlttf.TTF_Init()

    has_audio = False
    alarm_chunk = None
    try:
        if sdlmixer.Mix_OpenAudio(44100, sdlmixer.MIX_DEFAULT_FORMAT, 2, 2048) == 0:
            has_audio = True
            if os.path.exists(ALARM_SOUND_FILE):
                alarm_chunk = sdlmixer.Mix_LoadWAV(ALARM_SOUND_FILE.encode("utf-8"))
    except Exception as e:
        print(f"[AUDIO] Aviso: Áudio não disponível: {e}")

    is_arkos = "ARKOS" in os.environ or os.path.exists("/dev/fb0")
    flags = sdl2.SDL_WINDOW_SHOWN
    if is_arkos:
        flags |= sdl2.SDL_WINDOW_FULLSCREEN

    window = sdl2.SDL_CreateWindow(
        b"R36S Digital Clock",
        sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
        SCREEN_WIDTH, SCREEN_HEIGHT, flags
    )
    if not window and is_arkos:
        window = sdl2.SDL_CreateWindow(
            b"R36S Digital Clock",
            sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED,
            SCREEN_WIDTH, SCREEN_HEIGHT, sdl2.SDL_WINDOW_SHOWN
        )

    if not window:
        print(f"[ERRO] Falha ao criar janela SDL: {sdl2.SDL_GetError()}")
        return False

    sdl2.SDL_ShowCursor(sdl2.SDL_DISABLE)

    renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC)
    if not renderer:
        print("[AVISO] Renderer acelerado falhou, tentando software renderer...")
        renderer = sdl2.SDL_CreateRenderer(window, -1, sdl2.SDL_RENDERER_SOFTWARE)

    if not renderer:
        print(f"[ERRO] Falha ao criar renderer SDL: {sdl2.SDL_GetError()}")
        return False

    # Fontes com tamanhos atualizados conforme novo modelo Stitch
    font_time = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 106)
    font_colon = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 92)
    font_date = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 18)
    font_header = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 13)
    font_badge = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 11)
    font_toast = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 12)
    font_modal_title = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 14)
    font_modal_val = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 94)
    font_modal_colon = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 64)
    font_modal_arrow = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 14)
    font_modal_badge = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 10)
    font_bottom = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 13)

    joysticks = []
    if not gptokeyb_active:
        for i in range(sdl2.SDL_NumJoysticks()):
            joy = sdl2.SDL_JoystickOpen(i)
            if joy:
                joysticks.append(joy)
                print(f"[JOYSTICK] Gamepad nativo aberto: {sdl2.SDL_JoystickName(joy).decode('utf-8', 'ignore')}")
    else:
        print("[INPUT] Modo gptokeyb ativo (eventos via teclado UINPUT, sem duplicação de joystick).")

    config = Config()
    running = True
    is_editing = False
    edit_field = 0  # 0: Hora, 1: Minuto
    temp_hour = config.alarm_hour
    temp_minute = config.alarm_minute
    temp_active = config.alarm_active
    is_alarm_ringing = False
    last_alarm_minute_triggered = -1

    toast_msg = "MODO NORMAL • SELECIONE OS BOTÕES DE AÇÃO"
    toast_timer = 0.0

    battery_pct = get_battery_percentage()
    last_battery_check = time.time()

    axis_prev_x = 0
    axis_prev_y = 0

    def show_toast(msg, duration=3.0):
        nonlocal toast_msg, toast_timer
        toast_msg = msg
        toast_timer = time.time() + duration

    def cycle_theme(direction=1):
        config.theme_index = (config.theme_index + direction) % len(THEMES)
        theme = THEMES[config.theme_index]
        show_toast(f"COR ALTERADA: {theme['name']}")
        config.save()

    def enter_edit_mode():
        nonlocal is_editing, temp_hour, temp_minute, temp_active, edit_field
        is_editing = True
        temp_hour = config.alarm_hour
        temp_minute = config.alarm_minute
        temp_active = config.alarm_active
        edit_field = 0
        show_toast("MODO DE EDIÇÃO DO ALARME ATIVADO")

    def cancel_edit_mode():
        nonlocal is_editing
        is_editing = False
        show_toast("EDIÇÃO CANCELADA")

    def save_alarm():
        nonlocal is_editing
        config.alarm_hour = temp_hour
        config.alarm_minute = temp_minute
        config.alarm_active = temp_active
        config.save()
        is_editing = False
        time_str = f"{config.alarm_hour:02d}:{config.alarm_minute:02d}"
        status_str = "ATIVO" if config.alarm_active else "SILENCIADO"
        show_toast(f"ALARME DEFINIDO PARA {time_str} ({status_str})")

    def toggle_temp_active():
        nonlocal temp_active
        temp_active = not temp_active

    def stop_alarm():
        nonlocal is_alarm_ringing
        is_alarm_ringing = False
        if has_audio:
            try:
                sdlmixer.Mix_HaltChannel(-1)
            except Exception:
                pass
        show_toast("ALARME SILENCIADO")

    def toggle_alarm_active():
        if is_alarm_ringing:
            stop_alarm()
            return
        config.alarm_active = not config.alarm_active
        config.save()
        if config.alarm_active:
            show_toast("ALARME ATIVADO")
        else:
            show_toast("ALARME SILENCIADO / DESATIVADO")

    def trigger_alarm():
        nonlocal is_alarm_ringing
        is_alarm_ringing = True
        show_toast("ALARME DISPARADO! [B] SILENCIAR", duration=60.0)
        if has_audio and alarm_chunk:
            try:
                sdlmixer.Mix_PlayChannel(-1, alarm_chunk, -1)
            except Exception:
                pass

    def adjust_edit_value(delta):
        nonlocal temp_hour, temp_minute
        if edit_field == 0:
            temp_hour = (temp_hour + delta) % 24
        else:
            temp_minute = (temp_minute + delta) % 60

    # Primitivas gráficas
    def draw_fill_rect(x, y, w, h, col):
        sdl2.SDL_SetRenderDrawColor(renderer, col[0], col[1], col[2], col[3] if len(col) > 3 else 255)
        r = sdl2.SDL_Rect(int(x), int(y), int(w), int(h))
        sdl2.SDL_RenderFillRect(renderer, ctypes.byref(r))

    def draw_outline_rect(x, y, w, h, col):
        sdl2.SDL_SetRenderDrawColor(renderer, col[0], col[1], col[2], col[3] if len(col) > 3 else 255)
        r = sdl2.SDL_Rect(int(x), int(y), int(w), int(h))
        sdl2.SDL_RenderDrawRect(renderer, ctypes.byref(r))

    def draw_rounded_box(x, y, w, h, bg_col, border_col=None, border_w=1):
        draw_fill_rect(x, y, w, h, bg_col)
        if border_col:
            for b in range(border_w):
                draw_outline_rect(x + b, y + b, w - b * 2, h - b * 2, border_col)

    def render_text(font, text, color, x, y, align="left"):
        if not font or not text:
            return 0, 0
        sdl_col = sdl2.SDL_Color(color[0], color[1], color[2], 255)
        surf = sdlttf.TTF_RenderUTF8_Blended(font, text.encode("utf-8"), sdl_col)
        if not surf:
            return 0, 0
        w = surf.contents.w
        h = surf.contents.h
        tex = sdl2.SDL_CreateTextureFromSurface(renderer, surf)
        sdl2.SDL_FreeSurface(surf)
        if not tex:
            return 0, 0
        draw_x = x
        if align == "center":
            draw_x = x - w // 2
        elif align == "right":
            draw_x = x - w
        dst = sdl2.SDL_Rect(int(draw_x), int(y), int(w), int(h))
        sdl2.SDL_RenderCopy(renderer, tex, None, ctypes.byref(dst))
        sdl2.SDL_DestroyTexture(tex)
        return w, h

    def get_text_width(font, text):
        if not font or not text:
            return 0
        w, h = ctypes.c_int(), ctypes.c_int()
        sdlttf.TTF_SizeUTF8(font, text.encode("utf-8"), ctypes.byref(w), ctypes.byref(h))
        return w.value

    # Loop Principal
    event = sdl2.SDL_Event()
    while running:
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:
            if event.type == sdl2.SDL_QUIT:
                running = False
            elif event.type == sdl2.SDL_KEYDOWN:
                sym = event.key.keysym.sym
                is_repeat = event.key.repeat != 0

                if sym in (sdl2.SDLK_ESCAPE, sdl2.SDLK_F1):
                    running = False
                elif sym == sdl2.SDLK_a and not is_repeat:
                    if is_editing:
                        save_alarm()
                    else:
                        enter_edit_mode()
                elif sym == sdl2.SDLK_b and not is_repeat:
                    if is_editing:
                        cancel_edit_mode()
                    else:
                        toggle_alarm_active()
                elif sym in (sdl2.SDLK_x, sdl2.SDLK_y) and not is_repeat:
                    if is_editing:
                        toggle_temp_active()
                elif sym in (sdl2.SDLK_q, sdl2.SDLK_PAGEUP) and not is_repeat:
                    cycle_theme(-1)
                elif sym in (sdl2.SDLK_e, sdl2.SDLK_PAGEDOWN) and not is_repeat:
                    cycle_theme(1)
                elif sym == sdl2.SDLK_UP:
                    if is_editing:
                        adjust_edit_value(1)
                elif sym == sdl2.SDLK_DOWN:
                    if is_editing:
                        adjust_edit_value(-1)
                elif sym in (sdl2.SDLK_LEFT, sdl2.SDLK_RIGHT, sdl2.SDLK_TAB) and not is_repeat:
                    if is_editing:
                        edit_field = 1 - edit_field

            elif not gptokeyb_active and event.type == sdl2.SDL_JOYBUTTONDOWN:
                btn = event.jbutton.button
                # Mapeamento GO-Super Gamepad (R36S):
                # b1 = A, b0 = B, b2 = X, b3 = Y, b4 = L1, b5 = R1
                # b8 = Up, b9 = Down, b10 = Left, b11 = Right, b12 = Select, b13 = Start
                if btn == 1:  # Botão físico A
                    if is_editing:
                        save_alarm()
                    else:
                        enter_edit_mode()
                elif btn == 0:  # Botão físico B
                    if is_editing:
                        cancel_edit_mode()
                    else:
                        toggle_alarm_active()
                elif btn in (2, 3):  # Botões X e Y
                    if is_editing:
                        toggle_temp_active()
                elif btn == 4:  # L1
                    cycle_theme(-1)
                elif btn == 5:  # R1
                    cycle_theme(1)
                elif btn == 8:  # D-Pad Up
                    if is_editing:
                        adjust_edit_value(1)
                elif btn == 9:  # D-Pad Down
                    if is_editing:
                        adjust_edit_value(-1)
                elif btn in (10, 11):  # D-Pad Left / Right
                    if is_editing:
                        edit_field = 1 - edit_field
                elif btn in (12, 16):  # Select / FN
                    running = False

            elif not gptokeyb_active and event.type == sdl2.SDL_JOYHATMOTION:
                val = event.jhat.value
                if val == sdl2.SDL_HAT_UP:
                    if is_editing:
                        adjust_edit_value(1)
                elif val == sdl2.SDL_HAT_DOWN:
                    if is_editing:
                        adjust_edit_value(-1)
                elif val in (sdl2.SDL_HAT_LEFT, sdl2.SDL_HAT_RIGHT):
                    if is_editing:
                        edit_field = 1 - edit_field

            elif not gptokeyb_active and event.type == sdl2.SDL_JOYAXISMOTION:
                axis = event.jaxis.axis
                val = event.jaxis.value
                threshold = 16000
                if axis == 1:
                    if val < -threshold and axis_prev_y >= -threshold:
                        if is_editing:
                            adjust_edit_value(1)
                    elif val > threshold and axis_prev_y <= threshold:
                        if is_editing:
                            adjust_edit_value(-1)
                    axis_prev_y = val
                elif axis == 0:
                    if val < -threshold and axis_prev_x >= -threshold:
                        if is_editing:
                            edit_field = 1 - edit_field
                    elif val > threshold and axis_prev_x <= threshold:
                        if is_editing:
                            edit_field = 1 - edit_field
                    axis_prev_x = val

        now = datetime.datetime.now()
        theme = THEMES[config.theme_index]
        theme_col = theme["color"]

        # Checar disparo do alarme
        if config.alarm_active and not is_alarm_ringing:
            if (now.hour == config.alarm_hour and
                now.minute == config.alarm_minute and
                now.second == 0 and
                last_alarm_minute_triggered != now.minute):
                last_alarm_minute_triggered = now.minute
                trigger_alarm()
        if now.minute != config.alarm_minute:
            last_alarm_minute_triggered = -1

        # Checagem de bateria
        if time.time() - last_battery_check > 30:
            battery_pct = get_battery_percentage()
            last_battery_check = time.time()

        # Fundo Preto Puro e Nítido
        sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderClear(renderer)

        if not is_editing:
            # ==================================================================
            # TELA 1: RELÓGIO PRINCIPAL (Design Atualizado Stitch)
            # ==================================================================

            # 1. HEADER (Lado esquerdo limpo, Centro: Alarme, Direita: Bateria)
            draw_rounded_box(12, 10, 616, 36, (13, 15, 18), (30, 36, 44), 1)

            # Card Alarme Centralizado
            alarm_card_w = 230
            alarm_card_x = (SCREEN_WIDTH - alarm_card_w) // 2
            if is_alarm_ringing and (int(time.time() * 4) % 2 == 0):
                draw_rounded_box(alarm_card_x, 15, alarm_card_w, 26, (153, 27, 27), (239, 68, 68), 1)
            else:
                draw_rounded_box(alarm_card_x, 15, alarm_card_w, 26, (23, 23, 23), (38, 38, 38), 1)

            # Ícone do despertador
            draw_outline_rect(alarm_card_x + 10, 21, 12, 12, (251, 191, 36))
            draw_fill_rect(alarm_card_x + 15, 23, 2, 4, (251, 191, 36))
            draw_fill_rect(alarm_card_x + 15, 27, 4, 2, (251, 191, 36))

            render_text(font_header, "ALARME:", (209, 213, 219), alarm_card_x + 28, 21)
            time_str = f"{config.alarm_hour:02d}:{config.alarm_minute:02d}"
            render_text(font_header, time_str, (251, 191, 36), alarm_card_x + 84, 21)

            badge_txt = "ATIVO" if config.alarm_active else "SILENCIADO"
            badge_bg = (6, 78, 59) if config.alarm_active else (38, 38, 38)
            badge_border = (6, 95, 70) if config.alarm_active else (64, 64, 64)
            badge_fg = (52, 211, 153) if config.alarm_active else (156, 163, 175)
            bw = get_text_width(font_badge, badge_txt) + 12
            draw_rounded_box(alarm_card_x + 138, 18, bw, 20, badge_bg, badge_border, 1)
            render_text(font_badge, badge_txt, badge_fg, alarm_card_x + 144, 22)

            # Bateria à Direita
            render_text(font_header, f"{battery_pct}%", (156, 163, 175), 570, 21)
            draw_outline_rect(606, 23, 18, 10, (100, 116, 139))
            draw_fill_rect(624, 26, 2, 4, (100, 116, 139))
            charge_w = max(1, int(16 * (battery_pct / 100.0)))
            charge_col = (16, 185, 129) if battery_pct > 20 else (239, 68, 68)
            draw_fill_rect(607, 24, charge_w, 8, charge_col)

            # 2. DATA E DIA DA SEMANA
            dia_semana = DIAS_SEMANA[now.weekday()]
            date_str = f"{dia_semana}, {now.day:02d} {MESES[now.month - 1]} {now.year}"
            render_text(font_date, date_str, (156, 163, 175), SCREEN_WIDTH // 2, 110, align="center")

            # 3. DÍGITOS DO RELÓGIO (Fonte Aumentada 106px / 92px, sem 24H)
            h_str = f"{now.hour:02d}"
            m_str = f"{now.minute:02d}"
            s_str = f"{now.second:02d}"
            colon_char = ":" if (int(time.time() * 2) % 2 == 0) else " "

            hw = get_text_width(font_time, h_str)
            cw = get_text_width(font_colon, ":")
            mw = get_text_width(font_time, m_str)
            sw = get_text_width(font_time, s_str)
            total_w = hw + cw + mw + cw + sw + 20
            start_x = (SCREEN_WIDTH - total_w) // 2
            base_y = 158

            render_text(font_time, h_str, theme_col, start_x, base_y)
            cur_x = start_x + hw + 4
            render_text(font_colon, colon_char, theme_col, cur_x, base_y + 4)
            cur_x += cw + 4
            render_text(font_time, m_str, theme_col, cur_x, base_y)
            cur_x += mw + 4
            render_text(font_colon, colon_char, theme_col, cur_x, base_y + 4)
            cur_x += cw + 4
            render_text(font_time, s_str, theme_col, cur_x, base_y)

            # 4. TOAST / STATUS
            t_msg = toast_msg if time.time() <= toast_timer else "MODO NORMAL • SELECIONE OS BOTÕES DE AÇÃO"
            tw = get_text_width(font_toast, t_msg) + 30
            tx = (SCREEN_WIDTH - tw) // 2
            draw_rounded_box(tx, 305, tw, 24, (20, 22, 25), (38, 45, 56), 1)
            draw_fill_rect(tx + 10, 314, 6, 6, theme_col)
            render_text(font_toast, t_msg, (209, 213, 219), tx + 22, 310)

            # 5. RODAPÉ LIMPO E CENTRALIZADO (Cards removidos)
            draw_rounded_box(12, 412, 616, 56, (10, 12, 15), (30, 36, 44), 1)
            tip_txt = "TECLAS: [A] Editar • [B] Silenciar • [L1/R1] Trocar Cor • [SELECT+START] Sair"
            render_text(font_bottom, tip_txt, (203, 213, 225), SCREEN_WIDTH // 2, 431, align="center")

        else:
            # ==================================================================
            # TELA 2: AJUSTE DE ALARME (Nova Tela Dedicada do Stitch)
            # ==================================================================

            # 1. HEADER
            draw_rounded_box(12, 10, 616, 36, (13, 15, 18), (30, 36, 44), 1)
            render_text(font_header, f"{battery_pct}%", (156, 163, 175), 570, 21)
            draw_outline_rect(606, 23, 18, 10, (100, 116, 139))
            draw_fill_rect(624, 26, 2, 4, (100, 116, 139))
            charge_w = max(1, int(16 * (battery_pct / 100.0)))
            charge_col = (16, 185, 129) if battery_pct > 20 else (239, 68, 68)
            draw_fill_rect(607, 24, charge_w, 8, charge_col)

            # 2. TÍTULO
            render_text(font_modal_title, "DEFINIR HORÁRIO DE ALARME", (156, 163, 175), SCREEN_WIDTH // 2, 70, align="center")

            # 3. CAMPOS DE HORA E MINUTO (Dígitos 94px)
            box_w, box_h = 150, 138

            # --- CAMPO HORA ---
            h_is_sel = (edit_field == 0)
            h_arr_col = (251, 191, 36) if h_is_sel else (82, 82, 82)
            render_text(font_modal_arrow, "▲ +1H", h_arr_col, SCREEN_WIDTH // 2 - 110, 104, align="center")

            hx = SCREEN_WIDTH // 2 - 185
            hy = 126
            h_bg = (10, 10, 10) if h_is_sel else (13, 15, 18)
            h_border = (251, 191, 36) if h_is_sel else (38, 38, 38)
            draw_rounded_box(hx, hy, box_w, box_h, h_bg, h_border, 2 if h_is_sel else 1)

            h_val_col = (251, 191, 36) if h_is_sel else (163, 163, 163)
            render_text(font_modal_val, f"{temp_hour:02d}", h_val_col, SCREEN_WIDTH // 2 - 110, 134, align="center")

            if h_is_sel:
                draw_rounded_box(SCREEN_WIDTH // 2 - 170, 238, 120, 18, (69, 26, 3), (120, 53, 15), 1)
                render_text(font_modal_badge, "HORA [SELECIONADO]", (253, 230, 138), SCREEN_WIDTH // 2 - 110, 241, align="center")
            else:
                render_text(font_modal_badge, "HORA", (115, 115, 115), SCREEN_WIDTH // 2 - 110, 241, align="center")

            render_text(font_modal_arrow, "▼ -1H", h_arr_col, SCREEN_WIDTH // 2 - 110, 272, align="center")

            # --- DOIS PONTOS ---
            render_text(font_modal_colon, ":", (115, 115, 115), SCREEN_WIDTH // 2, 162, align="center")

            # --- CAMPO MINUTO ---
            m_is_sel = (edit_field == 1)
            m_arr_col = (251, 191, 36) if m_is_sel else (82, 82, 82)
            render_text(font_modal_arrow, "▲ +1M", m_arr_col, SCREEN_WIDTH // 2 + 110, 104, align="center")

            mx = SCREEN_WIDTH // 2 + 35
            my = 126
            m_bg = (10, 10, 10) if m_is_sel else (13, 15, 18)
            m_border = (251, 191, 36) if m_is_sel else (38, 38, 38)
            draw_rounded_box(mx, my, box_w, box_h, m_bg, m_border, 2 if m_is_sel else 1)

            m_val_col = (251, 191, 36) if m_is_sel else (163, 163, 163)
            render_text(font_modal_val, f"{temp_minute:02d}", m_val_col, SCREEN_WIDTH // 2 + 110, 134, align="center")

            if m_is_sel:
                draw_rounded_box(SCREEN_WIDTH // 2 + 45, 238, 130, 18, (69, 26, 3), (120, 53, 15), 1)
                render_text(font_modal_badge, "MINUTO [SELECIONADO]", (253, 230, 138), SCREEN_WIDTH // 2 + 110, 241, align="center")
            else:
                render_text(font_modal_badge, "MINUTO", (115, 115, 115), SCREEN_WIDTH // 2 + 110, 241, align="center")

            render_text(font_modal_arrow, "▼ -1M", m_arr_col, SCREEN_WIDTH // 2 + 110, 272, align="center")

            # 4. CARD STATUS DO ALARME
            status_box_w = 430
            status_box_x = (SCREEN_WIDTH - status_box_w) // 2
            draw_rounded_box(status_box_x, 316, status_box_w, 42, (20, 23, 28), (38, 45, 56), 1)
            render_text(font_badge, "STATUS DO ALARME:", (212, 212, 212), status_box_x + 16, 330)

            # Badge ATIVO
            act_bg = (6, 78, 59) if temp_active else (23, 23, 23)
            act_border = (16, 185, 129) if temp_active else (38, 38, 38)
            act_fg = (52, 211, 153) if temp_active else (82, 82, 82)
            draw_rounded_box(status_box_x + 165, 324, 70, 26, act_bg, act_border, 1)
            if temp_active:
                draw_fill_rect(status_box_x + 173, 334, 6, 6, (52, 211, 153))
                render_text(font_badge, "ATIVO", act_fg, status_box_x + 185, 330)
            else:
                render_text(font_badge, "ATIVO", act_fg, status_box_x + 180, 330)

            # Badge INATIVO
            inact_bg = (38, 38, 38) if not temp_active else (23, 23, 23)
            inact_border = (82, 82, 82) if not temp_active else (38, 38, 38)
            inact_fg = (212, 212, 212) if not temp_active else (82, 82, 82)
            draw_rounded_box(status_box_x + 242, 324, 75, 26, inact_bg, inact_border, 1)
            render_text(font_badge, "INATIVO", inact_fg, status_box_x + 256, 330)

            render_text(font_badge, "[X / Y: Alternar]", (115, 115, 115), status_box_x + 325, 330)

            # 5. RODAPÉ DO MODO DE AJUSTE
            draw_rounded_box(12, 412, 616, 56, (10, 12, 15), (30, 36, 44), 1)
            render_text(font_bottom, "TECLAS: [D-PAD] Ajustar / Navegar • [A] Confirmar • [B] Cancelar", (203, 213, 225), SCREEN_WIDTH // 2, 431, align="center")

        sdl2.SDL_RenderPresent(renderer)
        sdl2.SDL_Delay(33)

    # Cleanup
    if has_audio:
        try:
            sdlmixer.Mix_CloseAudio()
        except Exception:
            pass
    sdlttf.TTF_Quit()
    sdl2.SDL_DestroyRenderer(renderer)
    sdl2.SDL_DestroyWindow(window)
    sdl2.SDL_Quit()
    return True


# ==============================================================================
# MOTOR 2: Pygame Fallback (se disponível no ambiente)
# ==============================================================================
def run_pygame():
    try:
        import pygame
    except ImportError:
        return False

    print("[MOTOR] Executando com Pygame...")
    pygame.init()
    pygame.mixer.init()

    flags = pygame.FULLSCREEN if "ARKOS" in os.environ or os.path.exists("/dev/fb0") else 0
    try:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    except Exception:
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()
    config = Config()

    if os.path.exists(FONT_FILE):
        f_time = pygame.font.Font(FONT_FILE, 106)
        f_colon = pygame.font.Font(FONT_FILE, 92)
        f_date = pygame.font.Font(FONT_FILE, 18)
        f_header = pygame.font.Font(FONT_FILE, 13)
        f_badge = pygame.font.Font(FONT_FILE, 11)
        f_toast = pygame.font.Font(FONT_FILE, 12)
        f_modal_title = pygame.font.Font(FONT_FILE, 14)
        f_modal_val = pygame.font.Font(FONT_FILE, 94)
        f_modal_colon = pygame.font.Font(FONT_FILE, 64)
        f_modal_arrow = pygame.font.Font(FONT_FILE, 14)
        f_modal_badge = pygame.font.Font(FONT_FILE, 10)
        f_bottom = pygame.font.Font(FONT_FILE, 13)
    else:
        f_time = pygame.font.SysFont("monospace", 100, bold=True)
        f_colon = pygame.font.SysFont("monospace", 88, bold=True)
        f_date = pygame.font.SysFont("monospace", 18, bold=True)
        f_header = pygame.font.SysFont("sans-serif", 13, bold=True)
        f_badge = pygame.font.SysFont("sans-serif", 11, bold=True)
        f_toast = pygame.font.SysFont("monospace", 12)
        f_modal_title = pygame.font.SysFont("sans-serif", 14, bold=True)
        f_modal_val = pygame.font.SysFont("monospace", 90, bold=True)
        f_modal_colon = pygame.font.SysFont("monospace", 60, bold=True)
        f_modal_arrow = pygame.font.Font(None, 14)
        f_modal_badge = pygame.font.SysFont("sans-serif", 10, bold=True)
        f_bottom = pygame.font.SysFont("sans-serif", 13)

    alarm_sound = None
    if os.path.exists(ALARM_SOUND_FILE):
        try:
            alarm_sound = pygame.mixer.Sound(ALARM_SOUND_FILE)
        except Exception:
            pass

    gptokeyb_active = os.environ.get("GPTOKEYB_ACTIVE") == "1"
    if not gptokeyb_active:
        pygame.joystick.init()
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            j.init()

    running = True
    is_editing = False
    edit_field = 0
    temp_hour = config.alarm_hour
    temp_minute = config.alarm_minute
    temp_active = config.alarm_active
    is_alarm_ringing = False
    last_alarm_minute_triggered = -1

    toast_msg = "MODO NORMAL • SELECIONE OS BOTÕES DE AÇÃO"
    toast_timer = 0.0

    battery_pct = get_battery_percentage()
    last_battery_check = time.time()

    hat_prev_x, hat_prev_y = 0, 0
    axis_prev_x, axis_prev_y = 0, 0

    def show_toast(msg, duration=3.0):
        nonlocal toast_msg, toast_timer
        toast_msg = msg
        toast_timer = time.time() + duration

    def cycle_theme(direction=1):
        config.theme_index = (config.theme_index + direction) % len(THEMES)
        theme = THEMES[config.theme_index]
        show_toast(f"COR ALTERADA: {theme['name']}")
        config.save()

    def enter_edit_mode():
        nonlocal is_editing, temp_hour, temp_minute, temp_active, edit_field
        is_editing = True
        temp_hour = config.alarm_hour
        temp_minute = config.alarm_minute
        temp_active = config.alarm_active
        edit_field = 0
        show_toast("MODO DE EDIÇÃO DO ALARME ATIVADO")

    def cancel_edit_mode():
        nonlocal is_editing
        is_editing = False
        show_toast("EDIÇÃO CANCELADA")

    def save_alarm():
        nonlocal is_editing
        config.alarm_hour = temp_hour
        config.alarm_minute = temp_minute
        config.alarm_active = temp_active
        config.save()
        is_editing = False
        time_str = f"{config.alarm_hour:02d}:{config.alarm_minute:02d}"
        status_str = "ATIVO" if config.alarm_active else "SILENCIADO"
        show_toast(f"ALARME DEFINIDO PARA {time_str} ({status_str})")

    def toggle_temp_active():
        nonlocal temp_active
        temp_active = not temp_active

    def stop_alarm():
        nonlocal is_alarm_ringing
        is_alarm_ringing = False
        if alarm_sound:
            try:
                alarm_sound.stop()
            except Exception:
                pass
        show_toast("ALARME SILENCIADO")

    def toggle_alarm_active():
        if is_alarm_ringing:
            stop_alarm()
            return
        config.alarm_active = not config.alarm_active
        config.save()
        if config.alarm_active:
            show_toast("ALARME ATIVADO")
        else:
            show_toast("ALARME SILENCIADO / DESATIVADO")

    def trigger_alarm():
        nonlocal is_alarm_ringing
        is_alarm_ringing = True
        show_toast("ALARME DISPARADO! [B] SILENCIAR", duration=60.0)
        if alarm_sound:
            try:
                alarm_sound.play(loops=-1)
            except Exception:
                pass

    def adjust_edit_value(delta):
        nonlocal temp_hour, temp_minute
        if edit_field == 0:
            temp_hour = (temp_hour + delta) % 24
        else:
            temp_minute = (temp_minute + delta) % 60

    def draw_rounded_rect(surf, col, rect, radius=6, border_col=None, border_w=1):
        pygame.draw.rect(surf, col, rect, border_radius=radius)
        if border_col and border_w > 0:
            pygame.draw.rect(surf, border_col, rect, width=border_w, border_radius=radius)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_F1):
                    running = False
                elif event.key == pygame.K_a:
                    if is_editing:
                        save_alarm()
                    else:
                        enter_edit_mode()
                elif event.key == pygame.K_b:
                    if is_editing:
                        cancel_edit_mode()
                    else:
                        toggle_alarm_active()
                elif event.key in (pygame.K_x, pygame.K_y):
                    if is_editing:
                        toggle_temp_active()
                elif event.key in (pygame.K_q, pygame.K_PAGEUP):
                    cycle_theme(-1)
                elif event.key in (pygame.K_e, pygame.K_PAGEDOWN):
                    cycle_theme(1)
                elif event.key == pygame.K_UP:
                    if is_editing:
                        adjust_edit_value(1)
                elif event.key == pygame.K_DOWN:
                    if is_editing:
                        adjust_edit_value(-1)
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    if is_editing:
                        edit_field = 1 - edit_field

            elif not gptokeyb_active and event.type == pygame.JOYBUTTONDOWN:
                btn = event.button
                if btn == 1:
                    if is_editing:
                        save_alarm()
                    else:
                        enter_edit_mode()
                elif btn == 0:
                    if is_editing:
                        cancel_edit_mode()
                    else:
                        toggle_alarm_active()
                elif btn in (2, 3):
                    if is_editing:
                        toggle_temp_active()
                elif btn == 4:
                    cycle_theme(-1)
                elif btn == 5:
                    cycle_theme(1)
                elif btn == 8:
                    if is_editing:
                        adjust_edit_value(1)
                elif btn == 9:
                    if is_editing:
                        adjust_edit_value(-1)
                elif btn in (10, 11):
                    if is_editing:
                        edit_field = 1 - edit_field
                elif btn in (12, 16):
                    running = False

            elif not gptokeyb_active and event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = event.value
                if hat_y == 1 and hat_prev_y != 1:
                    if is_editing:
                        adjust_edit_value(1)
                elif hat_y == -1 and hat_prev_y != -1:
                    if is_editing:
                        adjust_edit_value(-1)
                if hat_x != 0 and hat_prev_x == 0:
                    if is_editing:
                        edit_field = 1 - edit_field
                hat_prev_x, hat_prev_y = hat_x, hat_y

            elif not gptokeyb_active and event.type == pygame.JOYAXISMOTION:
                axis = event.axis
                val = event.value
                th = 0.5
                if axis == 1:
                    if val < -th and axis_prev_y >= -th:
                        if is_editing:
                            adjust_edit_value(1)
                    elif val > th and axis_prev_y <= th:
                        if is_editing:
                            adjust_edit_value(-1)
                    axis_prev_y = val
                elif axis == 0:
                    if val < -th and axis_prev_x >= -th:
                        if is_editing:
                            edit_field = 1 - edit_field
                    elif val > th and axis_prev_x <= th:
                        if is_editing:
                            edit_field = 1 - edit_field
                    axis_prev_x = val

        now = datetime.datetime.now()
        theme = THEMES[config.theme_index]
        theme_col = theme["color"]

        if config.alarm_active and not is_alarm_ringing:
            if (now.hour == config.alarm_hour and
                now.minute == config.alarm_minute and
                now.second == 0 and
                last_alarm_minute_triggered != now.minute):
                last_alarm_minute_triggered = now.minute
                trigger_alarm()
        if now.minute != config.alarm_minute:
            last_alarm_minute_triggered = -1

        if time.time() - last_battery_check > 30:
            battery_pct = get_battery_percentage()
            last_battery_check = time.time()

        screen.fill((0, 0, 0))

        if not is_editing:
            # 1. HEADER
            draw_rounded_rect(screen, (13, 15, 18), pygame.Rect(12, 10, 616, 36), radius=6, border_col=(30, 36, 44), border_w=1)

            # Card Alarme
            alarm_card_w = 230
            alarm_card_x = (SCREEN_WIDTH - alarm_card_w) // 2
            a_rect = pygame.Rect(alarm_card_x, 15, alarm_card_w, 26)
            if is_alarm_ringing and (int(time.time() * 4) % 2 == 0):
                draw_rounded_rect(screen, (153, 27, 27), a_rect, radius=4, border_col=(239, 68, 68), border_w=1)
            else:
                draw_rounded_rect(screen, (23, 23, 23), a_rect, radius=4, border_col=(38, 38, 38), border_w=1)

            pygame.draw.circle(screen, (251, 191, 36), (alarm_card_x + 18, 28), 5, width=1)
            screen.blit(f_header.render("ALARME:", True, (209, 213, 219)), (alarm_card_x + 28, 21))
            screen.blit(f_header.render(f"{config.alarm_hour:02d}:{config.alarm_minute:02d}", True, (251, 191, 36)), (alarm_card_x + 84, 21))

            b_txt = "ATIVO" if config.alarm_active else "SILENCIADO"
            b_bg = (6, 78, 59) if config.alarm_active else (38, 38, 38)
            b_border = (6, 95, 70) if config.alarm_active else (64, 64, 64)
            b_fg = (52, 211, 153) if config.alarm_active else (156, 163, 175)
            b_surf = f_badge.render(b_txt, True, b_fg)
            bw = b_surf.get_width() + 10
            draw_rounded_rect(screen, b_bg, pygame.Rect(alarm_card_x + 138, 18, bw, 20), radius=3, border_col=b_border, border_w=1)
            screen.blit(b_surf, (alarm_card_x + 143, 22))

            # Bateria
            screen.blit(f_header.render(f"{battery_pct}%", True, (156, 163, 175)), (570, 21))
            pygame.draw.rect(screen, (100, 116, 139), pygame.Rect(606, 23, 18, 10), width=1)
            pygame.draw.line(screen, (100, 116, 139), (624, 26), (624, 30), 2)
            charge_w = max(1, int(16 * (battery_pct / 100.0)))
            charge_col = (16, 185, 129) if battery_pct > 20 else (239, 68, 68)
            pygame.draw.rect(screen, charge_col, (607, 24, charge_w, 8))

            # 2. DATA
            dia_semana = DIAS_SEMANA[now.weekday()]
            date_str = f"{dia_semana}, {now.day:02d} {MESES[now.month - 1]} {now.year}"
            d_surf = f_date.render(date_str, True, (156, 163, 175))
            screen.blit(d_surf, d_surf.get_rect(center=(SCREEN_WIDTH // 2, 118)))

            # 3. RELÓGIO PRINCIPAL
            h_str = f"{now.hour:02d}"
            m_str = f"{now.minute:02d}"
            s_str = f"{now.second:02d}"
            colon_char = ":" if (int(time.time() * 2) % 2 == 0) else " "

            h_surf = f_time.render(h_str, True, theme_col)
            c1_surf = f_colon.render(colon_char, True, theme_col)
            m_surf = f_time.render(m_str, True, theme_col)
            c2_surf = f_colon.render(colon_char, True, theme_col)
            s_surf = f_time.render(s_str, True, theme_col)

            total_w = (h_surf.get_width() + c1_surf.get_width() +
                       m_surf.get_width() + c2_surf.get_width() +
                       s_surf.get_width() + 16)
            start_x = (SCREEN_WIDTH - total_w) // 2
            base_y = 158

            screen.blit(h_surf, (start_x, base_y))
            cur_x = start_x + h_surf.get_width() + 4
            screen.blit(c1_surf, (cur_x, base_y + 4))
            cur_x += c1_surf.get_width() + 4
            screen.blit(m_surf, (cur_x, base_y))
            cur_x += m_surf.get_width() + 4
            screen.blit(c2_surf, (cur_x, base_y + 4))
            cur_x += c2_surf.get_width() + 4
            screen.blit(s_surf, (cur_x, base_y))

            # 4. TOAST
            t_msg = toast_msg if time.time() <= toast_timer else "MODO NORMAL • SELECIONE OS BOTÕES DE AÇÃO"
            t_surf = f_toast.render(t_msg, True, (209, 213, 219))
            tw = t_surf.get_width() + 28
            tx = (SCREEN_WIDTH - tw) // 2
            draw_rounded_rect(screen, (20, 22, 25), pygame.Rect(tx, 305, tw, 24), radius=12, border_col=(38, 45, 56), border_w=1)
            pygame.draw.circle(screen, theme_col, (tx + 12, 317), 3)
            screen.blit(t_surf, (tx + 22, 310))

            # 5. RODAPÉ
            draw_rounded_rect(screen, (10, 12, 15), pygame.Rect(12, 412, 616, 56), radius=8, border_col=(30, 36, 44), border_w=1)
            lbl = f_bottom.render("TECLAS: [A] Editar • [B] Silenciar • [L1/R1] Trocar Cor • [SELECT+START] Sair", True, (203, 213, 225))
            screen.blit(lbl, lbl.get_rect(center=(SCREEN_WIDTH // 2, 440)))

        else:
            # TELA DE AJUSTE DE ALARME
            draw_rounded_rect(screen, (13, 15, 18), pygame.Rect(12, 10, 616, 36), radius=6, border_col=(30, 36, 44), border_w=1)
            screen.blit(f_header.render(f"{battery_pct}%", True, (156, 163, 175)), (570, 21))
            pygame.draw.rect(screen, (100, 116, 139), pygame.Rect(606, 23, 18, 10), width=1)
            pygame.draw.line(screen, (100, 116, 139), (624, 26), (624, 30), 2)
            charge_w = max(1, int(16 * (battery_pct / 100.0)))
            charge_col = (16, 185, 129) if battery_pct > 20 else (239, 68, 68)
            pygame.draw.rect(screen, charge_col, (607, 24, charge_w, 8))

            t_title = f_modal_title.render("DEFINIR HORÁRIO DE ALARME", True, (156, 163, 175))
            screen.blit(t_title, t_title.get_rect(center=(SCREEN_WIDTH // 2, 75)))

            box_w, box_h = 150, 138

            # Hora
            h_is_sel = (edit_field == 0)
            arr1_col = (251, 191, 36) if h_is_sel else (82, 82, 82)
            arr1 = f_modal_arrow.render("▲ +1H", True, arr1_col)
            screen.blit(arr1, arr1.get_rect(center=(SCREEN_WIDTH // 2 - 110, 112)))

            h_r = pygame.Rect(SCREEN_WIDTH // 2 - 185, 126, box_w, box_h)
            h_bg = (10, 10, 10) if h_is_sel else (13, 15, 18)
            h_border = (251, 191, 36) if h_is_sel else (38, 38, 38)
            draw_rounded_rect(screen, h_bg, h_r, radius=8, border_col=h_border, border_w=2 if h_is_sel else 1)

            h_val = f_modal_val.render(f"{temp_hour:02d}", True, (251, 191, 36) if h_is_sel else (163, 163, 163))
            screen.blit(h_val, h_val.get_rect(center=(h_r.centerx, h_r.centery - 10)))

            if h_is_sel:
                draw_rounded_rect(screen, (69, 26, 3), pygame.Rect(h_r.centerx - 60, h_r.bottom - 26, 120, 18), radius=4, border_col=(120, 53, 15), border_w=1)
                b_lbl = f_modal_badge.render("HORA [SELECIONADO]", True, (253, 230, 138))
            else:
                b_lbl = f_modal_badge.render("HORA", True, (115, 115, 115))
            screen.blit(b_lbl, b_lbl.get_rect(center=(h_r.centerx, h_r.bottom - 17)))

            arr2 = f_modal_arrow.render("▼ -1H", True, arr1_col)
            screen.blit(arr2, arr2.get_rect(center=(SCREEN_WIDTH // 2 - 110, 280)))

            # Dois pontos
            sep = f_modal_colon.render(":", True, (115, 115, 115))
            screen.blit(sep, sep.get_rect(center=(SCREEN_WIDTH // 2, 195)))

            # Minuto
            m_is_sel = (edit_field == 1)
            arr3_col = (251, 191, 36) if m_is_sel else (82, 82, 82)
            arr3 = f_modal_arrow.render("▲ +1M", True, arr3_col)
            screen.blit(arr3, arr3.get_rect(center=(SCREEN_WIDTH // 2 + 110, 112)))

            m_r = pygame.Rect(SCREEN_WIDTH // 2 + 35, 126, box_w, box_h)
            m_bg = (10, 10, 10) if m_is_sel else (13, 15, 18)
            m_border = (251, 191, 36) if m_is_sel else (38, 38, 38)
            draw_rounded_rect(screen, m_bg, m_r, radius=8, border_col=m_border, border_w=2 if m_is_sel else 1)

            m_val = f_modal_val.render(f"{temp_minute:02d}", True, (251, 191, 36) if m_is_sel else (163, 163, 163))
            screen.blit(m_val, m_val.get_rect(center=(m_r.centerx, m_r.centery - 10)))

            if m_is_sel:
                draw_rounded_rect(screen, (69, 26, 3), pygame.Rect(m_r.centerx - 65, m_r.bottom - 26, 130, 18), radius=4, border_col=(120, 53, 15), border_w=1)
                b_lbl2 = f_modal_badge.render("MINUTO [SELECIONADO]", True, (253, 230, 138))
            else:
                b_lbl2 = f_modal_badge.render("MINUTO", True, (115, 115, 115))
            screen.blit(b_lbl2, b_lbl2.get_rect(center=(m_r.centerx, m_r.bottom - 17)))

            arr4 = f_modal_arrow.render("▼ -1M", True, arr3_col)
            screen.blit(arr4, arr4.get_rect(center=(SCREEN_WIDTH // 2 + 110, 280)))

            # Card Status do Alarme
            status_box_w = 430
            status_box_x = (SCREEN_WIDTH - status_box_w) // 2
            st_rect = pygame.Rect(status_box_x, 316, status_box_w, 42)
            draw_rounded_rect(screen, (20, 23, 28), st_rect, radius=6, border_col=(38, 45, 56), border_w=1)
            screen.blit(f_badge.render("STATUS DO ALARME:", True, (212, 212, 212)), (status_box_x + 16, 330))

            # Badge ATIVO
            act_bg = (6, 78, 59) if temp_active else (23, 23, 23)
            act_border = (16, 185, 129) if temp_active else (38, 38, 38)
            act_fg = (52, 211, 153) if temp_active else (82, 82, 82)
            draw_rounded_rect(screen, act_bg, pygame.Rect(status_box_x + 165, 324, 70, 26), radius=4, border_col=act_border, border_w=1)
            if temp_active:
                pygame.draw.circle(screen, (52, 211, 153), (status_box_x + 176, 337), 3)
                screen.blit(f_badge.render("ATIVO", True, act_fg), (status_box_x + 185, 330))
            else:
                screen.blit(f_badge.render("ATIVO", True, act_fg), (status_box_x + 180, 330))

            # Badge INATIVO
            inact_bg = (38, 38, 38) if not temp_active else (23, 23, 23)
            inact_border = (82, 82, 82) if not temp_active else (38, 38, 38)
            inact_fg = (212, 212, 212) if not temp_active else (82, 82, 82)
            draw_rounded_rect(screen, inact_bg, pygame.Rect(status_box_x + 242, 324, 75, 26), radius=4, border_col=inact_border, border_w=1)
            screen.blit(f_badge.render("INATIVO", True, inact_fg), (status_box_x + 256, 330))

            screen.blit(f_badge.render("[X / Y: Alternar]", True, (115, 115, 115)), (status_box_x + 325, 330))

            # Rodapé Modo Ajuste
            draw_rounded_rect(screen, (10, 12, 15), pygame.Rect(12, 412, 616, 56), radius=8, border_col=(30, 36, 44), border_w=1)
            lbl = f_bottom.render("TECLAS: [D-PAD] Ajustar / Navegar • [A] Confirmar • [B] Cancelar", True, (203, 213, 225))
            screen.blit(lbl, lbl.get_rect(center=(SCREEN_WIDTH // 2, 440)))

        pygame.display.flip()
        clock.tick(30)

    if alarm_sound:
        try:
            alarm_sound.stop()
        except Exception:
            pass
    pygame.quit()
    return True


if __name__ == "__main__":
    print("[MAIN] Iniciando aplicação do Relógio...")
    success = False
    try:
        success = run_pysdl2()
    except Exception as e:
        print(f"[MAIN] Falha no motor PySDL2: {e}")
        import traceback
        traceback.print_exc()

    if not success:
        print("[MAIN] Tentando motor secundário Pygame...")
        try:
            success = run_pygame()
        except Exception as e:
            print(f"[MAIN] Falha no motor Pygame: {e}")
            import traceback
            traceback.print_exc()

    if not success:
        print("[ERRO FATAL] Nenhum motor gráfico (PySDL2 ou Pygame) pôde ser executado.")
        sys.exit(1)
    sys.exit(0)
