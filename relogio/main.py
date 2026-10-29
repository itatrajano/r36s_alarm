#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
R36S Digital Clock & Alarm
Baseado no design do Google Stitch (640x480)
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
# MOTOR 1: PySDL2 NATIVO (O padrão do PortMaster e ArkOS no R36S)
# ==============================================================================
def run_pysdl2():
    import sdl2
    import sdl2.sdlttf as sdlttf
    import sdl2.sdlmixer as sdlmixer

    print("[MOTOR] Inicializando motor PySDL2 nativo...")
    # Se gptokeyb estiver ativo, não abrimos o Joystick nativo para evitar eventos duplicados
    gptokeyb_active = os.environ.get("GPTOKEYB_ACTIVE") == "1"
    init_flags = sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_AUDIO
    if not gptokeyb_active:
        init_flags |= sdl2.SDL_INIT_JOYSTICK

    if sdl2.SDL_Init(init_flags) != 0:
        print(f"[ERRO] Falha ao inicializar SDL2: {sdl2.SDL_GetError()}")
        return False

    sdlttf.TTF_Init()

    # Inicializar áudio
    has_audio = False
    alarm_chunk = None
    try:
        if sdlmixer.Mix_OpenAudio(44100, sdlmixer.MIX_DEFAULT_FORMAT, 2, 2048) == 0:
            has_audio = True
            if os.path.exists(ALARM_SOUND_FILE):
                alarm_chunk = sdlmixer.Mix_LoadWAV(ALARM_SOUND_FILE.encode("utf-8"))
    except Exception as e:
        print(f"[AUDIO] Aviso: Áudio não disponível: {e}")

    # Criar Janela (Fullscreen se em console ArkOS/KMS/DRM)
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

    # Carregar fontes TrueType
    font_time = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 94)
    font_colon = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 84)
    font_date = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 17)
    font_header = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 13)
    font_badge = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 12)
    font_modal_val = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 52)
    font_toast = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 12)
    font_card_title = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 12)
    font_card_sub = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 10)
    font_bottom = sdlttf.TTF_OpenFont(FONT_FILE.encode("utf-8"), 10)

    # Joysticks / Gamepad (somente se gptokeyb não estiver rodando)
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
    edit_field = 0
    temp_hour = config.alarm_hour
    temp_minute = config.alarm_minute
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

    def toggle_edit_mode():
        nonlocal is_editing, temp_hour, temp_minute, edit_field
        is_editing = not is_editing
        if is_editing:
            temp_hour = config.alarm_hour
            temp_minute = config.alarm_minute
            edit_field = 0
            show_toast("MODO DE EDIÇÃO DO ALARME ATIVADO")
        else:
            show_toast("EDIÇÃO CANCELADA")

    def save_alarm():
        nonlocal is_editing
        config.alarm_hour = temp_hour
        config.alarm_minute = temp_minute
        config.alarm_active = True
        config.save()
        is_editing = False
        time_str = f"{config.alarm_hour:02d}:{config.alarm_minute:02d}"
        show_toast(f"ALARME DEFINIDO PARA {time_str}")

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
        nonlocal is_editing
        if is_alarm_ringing:
            stop_alarm()
            return
        if is_editing:
            is_editing = False
            show_toast("EDIÇÃO CANCELADA")
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
            temp_minute = (temp_minute + delta * 5) % 60

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

    def draw_badge_btn(txt, center_x, center_y, bg_col, border_col, txt_col=(255, 255, 255)):
        w, h = 26, 20
        x, y = center_x - w // 2, center_y - h // 2
        draw_rounded_box(x, y, w, h, bg_col, border_col, 1)
        render_text(font_badge, txt, txt_col, center_x, center_y - 7, align="center")

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
                        toggle_edit_mode()
                elif sym == sdl2.SDLK_b and not is_repeat:
                    toggle_alarm_active()
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
                    # Esquerda/Direita apenas alternam entre Hora e Minuto no modo de edição
                    if is_editing:
                        edit_field = 1 - edit_field

            elif not gptokeyb_active and event.type == sdl2.SDL_JOYBUTTONDOWN:
                btn = event.jbutton.button
                # Mapeamento GO-Super Gamepad (R36S):
                # b1 = A (Leste), b0 = B (Sul), b4 = L1, b5 = R1
                # b8 = Up, b9 = Down, b10 = Left, b11 = Right, b12 = Select, b13 = Start
                if btn == 1:  # Botão físico A
                    if is_editing:
                        save_alarm()
                    else:
                        toggle_edit_mode()
                elif btn == 0:  # Botão físico B
                    toggle_alarm_active()
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

        # Fundo Preto Puro e Limpo
        sdl2.SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderClear(renderer)

        # 1. HEADER
        draw_rounded_box(12, 10, 616, 36, (13, 15, 18), (30, 36, 44), 1)
        dot_pulse = (int(time.time() * 2) % 2 == 0)
        dot_col = (16, 185, 129) if dot_pulse else (5, 120, 85)
        draw_fill_rect(26, 26, 8, 8, dot_col)
        render_text(font_header, "R36S OS • CLOCK", (156, 163, 175), 40, 21)

        # Card Alarme
        if is_alarm_ringing and (int(time.time() * 4) % 2 == 0):
            draw_rounded_box(210, 15, 220, 26, (153, 27, 27), (239, 68, 68), 1)
        else:
            draw_rounded_box(210, 15, 220, 26, (23, 23, 23), (38, 38, 38), 1)

        draw_fill_rect(220, 25, 6, 6, (251, 191, 36))
        render_text(font_header, "ALARME:", (209, 213, 219), 232, 21)
        time_str = f"{config.alarm_hour:02d}:{config.alarm_minute:02d}"
        render_text(font_header, time_str, (251, 191, 36), 288, 21)

        badge_txt = "ATIVO" if config.alarm_active else "SILENCIADO"
        badge_bg = (6, 78, 59) if config.alarm_active else (38, 38, 38)
        badge_border = (6, 95, 70) if config.alarm_active else (64, 64, 64)
        badge_fg = (52, 211, 153) if config.alarm_active else (156, 163, 175)
        bw = get_text_width(font_badge, badge_txt) + 12
        draw_rounded_box(336, 18, bw, 20, badge_bg, badge_border, 1)
        render_text(font_badge, badge_txt, badge_fg, 342, 21)

        render_text(font_header, theme["name"], theme_col, 490, 21)
        render_text(font_header, f"{battery_pct}%", (156, 163, 175), 570, 21)
        draw_outline_rect(606, 23, 18, 10, (100, 116, 139))
        draw_fill_rect(624, 26, 2, 4, (100, 116, 139))
        charge_w = max(1, int(16 * (battery_pct / 100.0)))
        charge_col = (16, 185, 129) if battery_pct > 20 else (239, 68, 68)
        draw_fill_rect(607, 24, charge_w, 8, charge_col)

        # 2. DATA E RELÓGIO DIGITAL
        dia_semana = DIAS_SEMANA[now.weekday()]
        date_str = f"{dia_semana}, {now.day:02d} {MESES[now.month - 1]} {now.year}"
        render_text(font_date, date_str, (156, 163, 175), SCREEN_WIDTH // 2, 105, align="center")

        h_str = f"{now.hour:02d}"
        m_str = f"{now.minute:02d}"
        s_str = f"{now.second:02d}"
        colon_char = ":" if (int(time.time() * 2) % 2 == 0) else " "

        hw = get_text_width(font_time, h_str)
        cw = get_text_width(font_colon, ":")
        mw = get_text_width(font_time, m_str)
        sw = get_text_width(font_time, s_str)
        aw = get_text_width(font_date, "24H")
        total_w = hw + cw + mw + cw + sw + aw + 24
        start_x = (SCREEN_WIDTH - total_w) // 2
        base_y = 145

        render_text(font_time, h_str, theme_col, start_x, base_y)
        cur_x = start_x + hw + 4
        render_text(font_colon, colon_char, theme_col, cur_x, base_y + 4)
        cur_x += cw + 4
        render_text(font_time, m_str, theme_col, cur_x, base_y)
        cur_x += mw + 4
        render_text(font_colon, colon_char, theme_col, cur_x, base_y + 4)
        cur_x += cw + 4
        render_text(font_time, s_str, theme_col, cur_x, base_y)
        cur_x += sw + 10
        render_text(font_date, "24H", (156, 163, 175), cur_x, base_y + 60)

        # Toast
        t_msg = toast_msg if time.time() <= toast_timer else "MODO NORMAL • SELECIONE OS BOTÕES DE AÇÃO"
        tw = get_text_width(font_toast, t_msg) + 30
        tx = (SCREEN_WIDTH - tw) // 2
        draw_rounded_box(tx, 275, tw, 24, (20, 22, 25), (38, 45, 56), 1)
        draw_fill_rect(tx + 10, 284, 6, 6, theme_col)
        render_text(font_toast, t_msg, (209, 213, 219), tx + 22, 280)

        # 3. MODAL DE EDIÇÃO
        if is_editing:
            draw_fill_rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (0, 0, 0, 210))
            modal_w, modal_h = 470, 260
            mx = (SCREEN_WIDTH - modal_w) // 2
            my = (SCREEN_HEIGHT - modal_h) // 2 - 10
            draw_rounded_box(mx, my, modal_w, modal_h, (10, 12, 16), (45, 55, 72), 2)

            render_text(font_card_title, "EDITAR HORA DO ALARME", (251, 191, 36), SCREEN_WIDTH // 2, my + 14, align="center")
            render_text(font_bottom, "Use DPAD Cima/Baixo para ajustar, Esquerda/Direita para alternar, A para salvar", (156, 163, 175), SCREEN_WIDTH // 2, my + 34, align="center")
            draw_fill_rect(mx + 15, my + 48, modal_w - 30, 1, (38, 45, 56))

            cy = my + 115
            bw, bh = 84, 60
            # Hora
            hx = SCREEN_WIDTH // 2 - 95
            h_border = (251, 191, 36) if edit_field == 0 else (55, 65, 81)
            h_bg = (23, 23, 23) if edit_field == 0 else (15, 17, 21)
            draw_rounded_box(hx, cy - bh // 2, bw, bh, h_bg, h_border, 2 if edit_field == 0 else 1)
            render_text(font_card_title, "▲", h_border, hx + bw // 2, cy - bh // 2 - 16, align="center")
            render_text(font_modal_val, f"{temp_hour:02d}", (251, 191, 36), hx + bw // 2, cy - 26, align="center")
            render_text(font_card_title, "▼", h_border, hx + bw // 2, cy + bh // 2 + 4, align="center")

            render_text(font_modal_val, ":", (251, 191, 36), SCREEN_WIDTH // 2, cy - 26, align="center")

            # Minuto
            mx_box = SCREEN_WIDTH // 2 + 11
            m_border = (251, 191, 36) if edit_field == 1 else (55, 65, 81)
            m_bg = (23, 23, 23) if edit_field == 1 else (15, 17, 21)
            draw_rounded_box(mx_box, cy - bh // 2, bw, bh, m_bg, m_border, 2 if edit_field == 1 else 1)
            render_text(font_card_title, "▲", m_border, mx_box + bw // 2, cy - bh // 2 - 16, align="center")
            render_text(font_modal_val, f"{temp_minute:02d}", (251, 191, 36), mx_box + bw // 2, cy - 26, align="center")
            render_text(font_card_title, "▼", m_border, mx_box + bw // 2, cy + bh // 2 + 4, align="center")

            # Botões do Modal
            b1_x = SCREEN_WIDTH // 2 - 165
            draw_rounded_box(b1_x, my + modal_h - 45, 155, 30, (35, 25, 10), (245, 158, 11), 1)
            draw_badge_btn("A", b1_x + 18, my + modal_h - 30, (185, 28, 28), (248, 113, 113))
            render_text(font_card_title, "SALVAR & FECHAR", (253, 230, 138), b1_x + 36, my + modal_h - 37)

            b2_x = SCREEN_WIDTH // 2 + 10
            draw_rounded_box(b2_x, my + modal_h - 45, 155, 30, (23, 23, 23), (75, 85, 99), 1)
            draw_badge_btn("B", b2_x + 18, my + modal_h - 30, (161, 98, 7), (253, 224, 71), (0, 0, 0))
            render_text(font_card_title, "CANCELAR", (156, 163, 175), b2_x + 38, my + modal_h - 37)

        # 4. RODAPÉ
        draw_rounded_box(12, 385, 616, 85, (10, 12, 15), (30, 36, 44), 1)
        col_w = 196
        # Card A
        draw_rounded_box(20, 393, col_w, 46, (20, 22, 26), (38, 45, 56), 1)
        draw_badge_btn("A", 42, 416, (185, 28, 28), (248, 113, 113))
        render_text(font_card_title, "EDITAR ALARME", (229, 231, 235), 62, 401)
        render_text(font_card_sub, "Configurar horário", (156, 163, 175), 62, 417)

        # Card B
        draw_rounded_box(224, 393, col_w, 46, (20, 22, 26), (38, 45, 56), 1)
        draw_badge_btn("B", 246, 416, (161, 98, 7), (253, 224, 71), (0, 0, 0))
        render_text(font_card_title, "SILENCIAR / MUDAR", (229, 231, 235), 266, 401)
        render_text(font_card_sub, "Desliga ou silencia", (156, 163, 175), 266, 417)

        # Card L1/R1
        draw_rounded_box(428, 393, col_w, 46, (20, 22, 26), (38, 45, 56), 1)
        draw_badge_btn("L1", 446, 416, (51, 65, 85), (100, 116, 139))
        draw_badge_btn("R1", 474, 416, (51, 65, 85), (100, 116, 139))
        render_text(font_card_title, "COR DA FONTE", (229, 231, 235), 496, 401)
        render_text(font_card_sub, "Alternar paleta", (156, 163, 175), 496, 417)

        draw_fill_rect(22, 445, 596, 1, (28, 32, 40))
        render_text(font_bottom, "LAYOUT R36S • 640 × 480 IPS", (100, 116, 139), 24, 452)
        tip_txt = "[A] Editar • [B] Silenciar • [L1/R1] Trocar Cor • [SELECT+START] Sair"
        render_text(font_bottom, tip_txt, (148, 163, 184), 616, 452, align="right")

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
        f_time = pygame.font.Font(FONT_FILE, 94)
        f_colon = pygame.font.Font(FONT_FILE, 84)
        f_date = pygame.font.Font(FONT_FILE, 17)
        f_header = pygame.font.Font(FONT_FILE, 13)
        f_badge = pygame.font.Font(FONT_FILE, 12)
        f_modal_val = pygame.font.Font(FONT_FILE, 52)
        f_toast = pygame.font.Font(FONT_FILE, 12)
        f_card_t = pygame.font.Font(FONT_FILE, 12)
        f_card_s = pygame.font.Font(FONT_FILE, 10)
        f_bottom = pygame.font.Font(FONT_FILE, 10)
    else:
        f_time = pygame.font.SysFont("monospace", 88, bold=True)
        f_colon = pygame.font.SysFont("monospace", 80, bold=True)
        f_date = pygame.font.SysFont("monospace", 16, bold=True)
        f_header = pygame.font.SysFont("sans-serif", 13, bold=True)
        f_badge = pygame.font.SysFont("sans-serif", 12, bold=True)
        f_modal_val = pygame.font.SysFont("monospace", 50, bold=True)
        f_toast = pygame.font.SysFont("monospace", 12)
        f_card_t = pygame.font.SysFont("sans-serif", 12, bold=True)
        f_card_s = pygame.font.SysFont("sans-serif", 10)
        f_bottom = pygame.font.SysFont("sans-serif", 10)

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

    def toggle_edit_mode():
        nonlocal is_editing, temp_hour, temp_minute, edit_field
        is_editing = not is_editing
        if is_editing:
            temp_hour = config.alarm_hour
            temp_minute = config.alarm_minute
            edit_field = 0
            show_toast("MODO DE EDIÇÃO DO ALARME ATIVADO")
        else:
            show_toast("EDIÇÃO CANCELADA")

    def save_alarm():
        nonlocal is_editing
        config.alarm_hour = temp_hour
        config.alarm_minute = temp_minute
        config.alarm_active = True
        config.save()
        is_editing = False
        time_str = f"{config.alarm_hour:02d}:{config.alarm_minute:02d}"
        show_toast(f"ALARME DEFINIDO PARA {time_str}")

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
        nonlocal is_editing
        if is_alarm_ringing:
            stop_alarm()
            return
        if is_editing:
            is_editing = False
            show_toast("EDIÇÃO CANCELADA")
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
            temp_minute = (temp_minute + delta * 5) % 60

    def draw_rounded_rect(surf, col, rect, radius=6, border_col=None, border_w=1):
        pygame.draw.rect(surf, col, rect, border_radius=radius)
        if border_col and border_w > 0:
            pygame.draw.rect(surf, border_col, rect, width=border_w, border_radius=radius)

    def draw_badge_btn(surf, text, center_x, center_y, bg_col, border_col, txt_col=(255, 255, 255)):
        w, h = 26, 20
        rect = pygame.Rect(center_x - w // 2, center_y - h // 2, w, h)
        draw_rounded_rect(surf, bg_col, rect, radius=10, border_col=border_col, border_w=1)
        txt = f_badge.render(text, True, txt_col)
        surf.blit(txt, txt.get_rect(center=rect.center))

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
                        toggle_edit_mode()
                elif event.key == pygame.K_b:
                    toggle_alarm_active()
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
                        toggle_edit_mode()
                elif btn == 0:
                    toggle_alarm_active()
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

        # 1. HEADER
        header_rect = pygame.Rect(12, 10, 616, 36)
        draw_rounded_rect(screen, (13, 15, 18), header_rect, radius=6, border_col=(30, 36, 44), border_w=1)
        dot_pulse = (int(time.time() * 2) % 2 == 0)
        dot_col = (16, 185, 129) if dot_pulse else (5, 120, 85)
        pygame.draw.circle(screen, dot_col, (28, 28), 4)
        t_title = f_header.render("R36S OS • CLOCK", True, (156, 163, 175))
        screen.blit(t_title, (38, 20))

        alarm_card_rect = pygame.Rect(210, 15, 220, 26)
        if is_alarm_ringing and (int(time.time() * 4) % 2 == 0):
            draw_rounded_rect(screen, (153, 27, 27), alarm_card_rect, radius=4, border_col=(239, 68, 68), border_w=1)
        else:
            draw_rounded_rect(screen, (23, 23, 23), alarm_card_rect, radius=4, border_col=(38, 38, 38), border_w=1)

        pygame.draw.circle(screen, (251, 191, 36), (222, 28), 5, width=1)
        pygame.draw.line(screen, (251, 191, 36), (222, 28), (222, 25), 1)
        pygame.draw.line(screen, (251, 191, 36), (222, 28), (225, 28), 1)
        screen.blit(f_header.render("ALARME:", True, (209, 213, 219)), (234, 21))
        screen.blit(f_header.render(f"{config.alarm_hour:02d}:{config.alarm_minute:02d}", True, (251, 191, 36)), (290, 21))

        b_txt = "ATIVO" if config.alarm_active else "SILENCIADO"
        b_bg = (6, 78, 59) if config.alarm_active else (38, 38, 38)
        b_border = (6, 95, 70) if config.alarm_active else (64, 64, 64)
        b_fg = (52, 211, 153) if config.alarm_active else (156, 163, 175)
        b_surf = f_badge.render(b_txt, True, b_fg)
        bw = b_surf.get_width() + 10
        draw_rounded_rect(screen, b_bg, pygame.Rect(340, 18, bw, 20), radius=3, border_col=b_border, border_w=1)
        screen.blit(b_surf, (345, 21))

        screen.blit(f_header.render(theme["name"], True, theme_col), (490, 21))
        screen.blit(f_header.render(f"{battery_pct}%", True, (156, 163, 175)), (570, 21))
        pygame.draw.rect(screen, (100, 116, 139), pygame.Rect(606, 23, 18, 10), width=1)
        pygame.draw.line(screen, (100, 116, 139), (624, 26), (624, 30), 2)
        charge_w = max(1, int(16 * (battery_pct / 100.0)))
        charge_col = (16, 185, 129) if battery_pct > 20 else (239, 68, 68)
        pygame.draw.rect(screen, charge_col, (607, 24, charge_w, 8))

        # 2. DATA E RELÓGIO
        dia_semana = DIAS_SEMANA[now.weekday()]
        date_str = f"{dia_semana}, {now.day:02d} {MESES[now.month - 1]} {now.year}"
        d_surf = f_date.render(date_str, True, (156, 163, 175))
        screen.blit(d_surf, d_surf.get_rect(center=(SCREEN_WIDTH // 2, 115)))

        h_str = f"{now.hour:02d}"
        m_str = f"{now.minute:02d}"
        s_str = f"{now.second:02d}"
        colon_char = ":" if (int(time.time() * 2) % 2 == 0) else " "

        h_surf = f_time.render(h_str, True, theme_col)
        c1_surf = f_colon.render(colon_char, True, theme_col)
        m_surf = f_time.render(m_str, True, theme_col)
        c2_surf = f_colon.render(colon_char, True, theme_col)
        s_surf = f_time.render(s_str, True, theme_col)
        ampm_surf = f_date.render("24H", True, (156, 163, 175))

        total_w = (h_surf.get_width() + c1_surf.get_width() +
                   m_surf.get_width() + c2_surf.get_width() +
                   s_surf.get_width() + ampm_surf.get_width() + 18)
        start_x = (SCREEN_WIDTH - total_w) // 2
        base_y = 150

        screen.blit(h_surf, (start_x, base_y))
        cur_x = start_x + h_surf.get_width() + 4
        screen.blit(c1_surf, (cur_x, base_y + 4))
        cur_x += c1_surf.get_width() + 4
        screen.blit(m_surf, (cur_x, base_y))
        cur_x += m_surf.get_width() + 4
        screen.blit(c2_surf, (cur_x, base_y + 4))
        cur_x += c2_surf.get_width() + 4
        screen.blit(s_surf, (cur_x, base_y))
        cur_x += s_surf.get_width() + 10
        screen.blit(ampm_surf, (cur_x, base_y + 60))

        # Toast
        t_msg = toast_msg if time.time() <= toast_timer else "MODO NORMAL • SELECIONE OS BOTÕES DE AÇÃO"
        t_surf = f_toast.render(t_msg, True, (209, 213, 219))
        tw = t_surf.get_width() + 28
        tx = (SCREEN_WIDTH - tw) // 2
        draw_rounded_rect(screen, (20, 22, 25), pygame.Rect(tx, 280, tw, 24), radius=12, border_col=(38, 45, 56), border_w=1)
        pygame.draw.circle(screen, theme_col, (tx + 12, 292), 3)
        screen.blit(t_surf, (tx + 22, 285))

        # 3. MODAL DE EDIÇÃO
        if is_editing:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            screen.blit(overlay, (0, 0))

            modal_w, modal_h = 470, 270
            m_rect = pygame.Rect((SCREEN_WIDTH - modal_w) // 2, (SCREEN_HEIGHT - modal_h) // 2 - 10, modal_w, modal_h)
            draw_rounded_rect(screen, (10, 12, 16), m_rect, radius=10, border_col=(45, 55, 72), border_w=2)

            t_m = f_card_t.render("EDITAR HORA DO ALARME", True, (251, 191, 36))
            screen.blit(t_m, t_m.get_rect(center=(SCREEN_WIDTH // 2, m_rect.y + 24)))
            sub_m = f_bottom.render("Use DPAD Cima/Baixo para ajustar, Esquerda/Direita para alternar, A para salvar", True, (156, 163, 175))
            screen.blit(sub_m, sub_m.get_rect(center=(SCREEN_WIDTH // 2, m_rect.y + 44)))
            pygame.draw.line(screen, (38, 45, 56), (m_rect.x + 15, m_rect.y + 56), (m_rect.right - 15, m_rect.y + 56), 1)

            box_w, box_h = 84, 60
            center_y = m_rect.y + 120

            # Hora
            h_r = pygame.Rect(SCREEN_WIDTH // 2 - 95, center_y - box_h // 2, box_w, box_h)
            h_border = (251, 191, 36) if edit_field == 0 else (55, 65, 81)
            h_bg = (23, 23, 23) if edit_field == 0 else (15, 17, 21)
            draw_rounded_rect(screen, h_bg, h_r, radius=6, border_col=h_border, border_w=2 if edit_field == 0 else 1)
            arr1 = f_card_t.render("▲", True, h_border)
            screen.blit(arr1, arr1.get_rect(center=(h_r.centerx, h_r.top - 14)))
            arr2 = f_card_t.render("▼", True, h_border)
            screen.blit(arr2, arr2.get_rect(center=(h_r.centerx, h_r.bottom + 14)))
            h_val = f_modal_val.render(f"{temp_hour:02d}", True, (251, 191, 36))
            screen.blit(h_val, h_val.get_rect(center=h_r.center))

            sep = f_modal_val.render(":", True, (251, 191, 36))
            screen.blit(sep, sep.get_rect(center=(SCREEN_WIDTH // 2, center_y)))

            # Minuto
            m_r = pygame.Rect(SCREEN_WIDTH // 2 + 11, center_y - box_h // 2, box_w, box_h)
            m_border = (251, 191, 36) if edit_field == 1 else (55, 65, 81)
            m_bg = (23, 23, 23) if edit_field == 1 else (15, 17, 21)
            draw_rounded_rect(screen, m_bg, m_r, radius=6, border_col=m_border, border_w=2 if edit_field == 1 else 1)
            arr3 = f_card_t.render("▲", True, m_border)
            screen.blit(arr3, arr3.get_rect(center=(m_r.centerx, m_r.top - 14)))
            arr4 = f_card_t.render("▼", True, m_border)
            screen.blit(arr4, arr4.get_rect(center=(m_r.centerx, m_r.bottom + 14)))
            m_val = f_modal_val.render(f"{temp_minute:02d}", True, (251, 191, 36))
            screen.blit(m_val, m_val.get_rect(center=m_r.center))

            btn1 = pygame.Rect(m_rect.centerx - 170, m_rect.bottom - 45, 160, 30)
            draw_rounded_rect(screen, (35, 25, 10), btn1, radius=5, border_col=(245, 158, 11), border_w=1)
            draw_badge_btn(screen, "A", btn1.x + 20, btn1.centery, (185, 28, 28), (248, 113, 113))
            save_txt = f_card_t.render("SALVAR & FECHAR", True, (253, 230, 138))
            screen.blit(save_txt, (btn1.x + 36, btn1.centery - save_txt.get_height() // 2))

            btn2 = pygame.Rect(m_rect.centerx + 10, m_rect.bottom - 45, 160, 30)
            draw_rounded_rect(screen, (23, 23, 23), btn2, radius=5, border_col=(75, 85, 99), border_w=1)
            draw_badge_btn(screen, "B", btn2.x + 20, btn2.centery, (161, 98, 7), (253, 224, 71), (0, 0, 0))
            can_txt = f_card_t.render("CANCELAR", True, (156, 163, 175))
            screen.blit(can_txt, (btn2.x + 38, btn2.centery - can_txt.get_height() // 2))

        # 4. RODAPÉ
        footer_rect = pygame.Rect(12, 385, 616, 85)
        draw_rounded_rect(screen, (10, 12, 15), footer_rect, radius=8, border_col=(30, 36, 44), border_w=1)
        col_w = 196

        c1 = pygame.Rect(footer_rect.x + 8, footer_rect.y + 8, col_w, 46)
        draw_rounded_rect(screen, (20, 22, 26), c1, radius=6, border_col=(38, 45, 56), border_w=1)
        draw_badge_btn(screen, "A", c1.x + 22, c1.centery, (185, 28, 28), (248, 113, 113))
        screen.blit(f_card_t.render("EDITAR ALARME", True, (229, 231, 235)), (c1.x + 42, c1.y + 8))
        screen.blit(f_card_s.render("Configurar horário", True, (156, 163, 175)), (c1.x + 42, c1.y + 24))

        c2 = pygame.Rect(footer_rect.x + 8 + col_w + 8, footer_rect.y + 8, col_w, 46)
        draw_rounded_rect(screen, (20, 22, 26), c2, radius=6, border_col=(38, 45, 56), border_w=1)
        draw_badge_btn(screen, "B", c2.x + 22, c2.centery, (161, 98, 7), (253, 224, 71), (0, 0, 0))
        screen.blit(f_card_t.render("SILENCIAR / MUDAR", True, (229, 231, 235)), (c2.x + 42, c2.y + 8))
        screen.blit(f_card_s.render("Desliga ou silencia", True, (156, 163, 175)), (c2.x + 42, c2.y + 24))

        c3 = pygame.Rect(footer_rect.x + 8 + (col_w + 8) * 2, footer_rect.y + 8, col_w, 46)
        draw_rounded_rect(screen, (20, 22, 26), c3, radius=6, border_col=(38, 45, 56), border_w=1)
        draw_badge_btn(screen, "L1", c3.x + 18, c3.centery, (51, 65, 85), (100, 116, 139))
        draw_badge_btn(screen, "R1", c3.x + 46, c3.centery, (51, 65, 85), (100, 116, 139))
        screen.blit(f_card_t.render("COR DA FONTE", True, (229, 231, 235)), (c3.x + 68, c3.y + 8))
        screen.blit(f_card_s.render("Alternar paleta", True, (156, 163, 175)), (c3.x + 68, c3.y + 24))

        pygame.draw.line(screen, (28, 32, 40), (footer_rect.x + 10, footer_rect.y + 60), (footer_rect.right - 10, footer_rect.y + 60), 1)
        screen.blit(f_bottom.render("LAYOUT R36S • 640 × 480 IPS", True, (100, 116, 139)), (footer_rect.x + 12, footer_rect.y + 67))
        lbl_k = f_bottom.render("[A] Editar • [B] Silenciar • [L1/R1] Trocar Cor • [SELECT+START] Sair", True, (148, 163, 184))
        screen.blit(lbl_k, (footer_rect.right - lbl_k.get_width() - 12, footer_rect.y + 67))

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
