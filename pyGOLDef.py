#Ver 0.4
import pygame
import sys
import json
import os
import re
import subprocess
import webbrowser

# Inizializza Pygame
pygame.init()
pygame.font.init()

# ----------------- TEMA E COLORI -----------------
BG_MAIN = (30, 30, 46)
BG_PANEL = (24, 24, 37)
BG_MENU = (17, 17, 27)
GRID_COLOR = (49, 50, 68)
BORDER_COLOR = (243, 139, 168)
TEXT_COLOR = (205, 214, 244)
TEXT_MUTED = (166, 173, 200)
CELL_ALIVE = (0, 230, 118)

# Colori Pulsanti
C_START = (166, 227, 161)
C_STOP = (243, 139, 168)
C_RESET = (249, 226, 175)
C_BTN_BG = (69, 71, 90)
C_BTN_HOV = (88, 91, 112)
C_SAVE = (203, 166, 247)
C_ACTION = (137, 180, 250)

FILE_MODELLI = "modelli_conway.json"
WIKI_URL = "https://conwaylife.com/wiki/Main_Page"

MODELLI_DEFAULT = {
    "Blinker (Oscillatore)": [[0, 0], [0, 1], [0, 2]],
    "Toad (Oscillatore)": [[0, 1], [0, 2], [0, 3], [1, 0], [1, 1], [1, 2]],
    "Beacon (Oscillatore)": [[0, 0], [0, 1], [1, 0], [1, 1], [2, 2], [2, 3], [3, 2], [3, 3]],
    "Pulsar (Oscillatore)": [
        [0, 2], [0, 3], [0, 4], [0, 8], [0, 9], [0, 10], [2, 0], [2, 5], [2, 7], [2, 12],
        [3, 0], [3, 5], [3, 7], [3, 12], [4, 0], [4, 5], [4, 7], [4, 12], [5, 2], [5, 3],
        [5, 4], [5, 8], [5, 9], [5, 10], [7, 2], [7, 3], [7, 4], [7, 8], [7, 9], [7, 10],
        [8, 0], [8, 5], [8, 7], [8, 12], [9, 0], [9, 5], [9, 7], [9, 12], [10, 0], [10, 5],
        [10, 7], [10, 12], [12, 2], [12, 3], [12, 4], [12, 8], [12, 9], [12, 10]
    ],
    "Penta-decathlon (Oscillatore)": [[0,1], [0,2], [0,3], [0,4], [0,5], [0,6], [0,7], [0,8], [0,9], [0,10]],
    "Glider (Astronave)": [[0, 1], [1, 2], [2, 0], [2, 1], [2, 2]],
    "LWSS (Astronave Leggera)": [[0, 1], [0, 4], [1, 0], [2, 0], [2, 4], [3, 0], [3, 1], [3, 2], [3, 3]],
    "MWSS (Astronave Media)": [[0, 3], [1, 1], [1, 5], [2, 0], [3, 0], [3, 5], [4, 0], [4, 1], [4, 2], [4, 3], [4, 4]],
    "R-pentomino (Matusalemme)": [[0, 1], [0, 2], [1, 0], [1, 1], [2, 1]],
    "Diehard (Matusalemme)": [[0, 6], [1, 0], [1, 1], [2, 1], [2, 5], [2, 6], [2, 7]],
    "Acorn (Matusalemme)": [[0, 1], [1, 3], [2, 0], [2, 1], [2, 4], [2, 5], [2, 6]],
    "Gosper Glider Gun": [
        [0, 24], [1, 22], [1, 24], [2, 12], [2, 13], [2, 20], [2, 21], [2, 34], [2, 35],
        [3, 11], [3, 15], [3, 20], [3, 21], [3, 34], [3, 35], [4, 0], [4, 1], [4, 10],
        [4, 16], [4, 20], [4, 21], [5, 0], [5, 1], [5, 10], [5, 14], [5, 16], [5, 17],
        [5, 22], [5, 24], [6, 10], [6, 16], [6, 24], [7, 11], [7, 15], [8, 12], [8, 13]
    ]
}

# ----------------- HELPER APPUNTI (CROSS-PLATFORM) -----------------
def get_clipboard_text():
    """Legge il testo dagli appunti di sistema senza usare Tkinter."""
    try:
        if sys.platform == "darwin":
            return subprocess.check_output(["pbpaste"], text=True)
        elif sys.platform == "win32":
            return subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                text=True
            )
        else:
            for cmd in (["xclip", "-o", "-selection", "clipboard"], ["xsel", "-ob"]):
                try:
                    return subprocess.check_output(cmd, text=True)
                except FileNotFoundError:
                    continue
    except Exception:
        pass
    return ""


# ----------------- FUNZIONI RLE (ENCODER & DECODER) -----------------
def parse_rle(rle_text):
    """Decodifica una stringa in formato RLE restituendo (nome, lista_coordinate [row, col])."""
    name = None
    data_lines = []
    header_found = False

    for line in rle_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            if line.startswith("#N") or line.startswith("#n"):
                name = line[2:].strip()
            continue
        if not header_found and line.lower().startswith("x"):
            header_found = True
            continue
        data_lines.append(line)

    data = "".join(data_lines)
    if "!" in data:
        data = data.split("!", 1)[0]

    coords = []
    r, c = 0, 0
    for count_str, tag in re.findall(r'(\d*)([bo$])', data):
        count = int(count_str) if count_str else 1
        if tag == 'b':
            c += count
        elif tag == 'o':
            for i in range(count):
                coords.append([r, c + i])
            c += count
        elif tag == '$':
            r += count
            c = 0

    return name, coords


def encode_rle(coords, name="Modello"):
    """Codifica una lista di coordinate [row, col] in formato RLE standard."""
    if not coords:
        return ""

    min_r = min(r for r, c in coords)
    min_c = min(c for r, c in coords)
    norm = {(r - min_r, c - min_c) for r, c in coords}

    max_r = max(r for r, c in norm)
    max_c = max(c for r, c in norm)
    width = max_c + 1
    height = max_r + 1

    tokens = []
    empty_rows = 0

    for r in range(height):
        row_cells = sorted(c for rr, c in norm if rr == r)
        if not row_cells:
            empty_rows += 1
            continue

        if empty_rows > 0:
            tokens.append(f"{empty_rows}$" if empty_rows > 1 else "$")
            empty_rows = 0

        row_str = ""
        last_c = row_cells[-1]
        c = 0
        while c <= last_c:
            is_alive = (r, c) in norm
            run = 1
            while c + run <= last_c and ((r, c + run) in norm) == is_alive:
                run += 1
            tag = 'o' if is_alive else 'b'
            row_str += f"{run}{tag}" if run > 1 else tag
            c += run

        tokens.append(row_str)
        if r < height - 1:
            empty_rows = 1

    body = "".join(tokens) + "!"
    wrapped_lines = [body[i:i + 70] for i in range(0, len(body), 70)]

    header = f"#N {name}\nx = {width}, y = {height}, rule = B3/S23\n"
    return header + "\n".join(wrapped_lines) + "\n"


class Button:
    def __init__(self, x, y, w, h, text, color, hover_color, font, text_color=(20, 20, 30)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font = font
        self.text_color = text_color
        self.is_hovered = False

    def draw(self, surface):
        current_color = self.hover_color if self.is_hovered else self.color
        pygame.draw.rect(surface, current_color, self.rect, border_radius=6)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def check_hover(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)


class GameOfLifePygame:
    def __init__(self):
        self.top_bar_h = 34
        self.w_left = 300
        self.w_right = 300
        self.w_center = 720
        self.width = self.w_left + self.w_center + self.w_right
        self.height = 760
        self.grid_view_h = self.height - self.top_bar_h

        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Il Gioco della Vita - RLE Edition")

        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_btn = pygame.font.SysFont("segoeui", 14, bold=True)
        self.font_list = pygame.font.SysFont("segoeui", 14)
        self.font_small = pygame.font.SysFont("segoeui", 12)
        self.font_mono = pygame.font.SysFont("menlo,consolas,monospace", 13)

        # LOGICA GRIGLIA
        self.alive_cells = set()
        self.initial_cells = set()

        self.is_infinite = True
        self.grid_w = 100
        self.grid_h = 100

        # Telecamera e Zoom
        self.cell_size = 14
        self.camera_x = self.w_center // 2
        self.camera_y = self.grid_view_h // 2

        self.is_panning = False
        self.last_mouse_pos = (0, 0)
        self.brush_mode = None

        self.running = False
        self.cicli = 0
        self.speed_ms = 80
        self.last_update_time = 0

        self.history = []
        self.end_message = ""
        self.last_dir = os.getcwd()

        # Barra Menù superiore (File RLE + Info)
        self.open_menu = None  # None, "rle", "info"
        self.menus = {
            "rle": {
                "label": "File RLE  v",
                "rect": pygame.Rect(10, 4, 110, 26),
                "drop_w": 260,
                "items": [
                    ("Importa file .rle...", self.import_rle_file),
                    ("Incolla codice RLE...", self.import_rle_paste),
                    ("Esporta Griglia (.rle)", self.export_grid_rle),
                    ("Esporta Modello Selezionato (.rle)", self.export_selected_rle),
                ],
            },
            "info": {
                "label": "Info  v",
                "rect": pygame.Rect(128, 4, 80, 26),
                "drop_w": 230,
                "items": [
                    ("ConwayLife Wiki", self.open_wiki),
                ],
            },
        }

        # Minimappa
        right_start = self.w_left + self.w_center
        self.minimap_rect = pygame.Rect(right_start + 20, self.height - 220, self.w_right - 40, 195)
        self.minimap_data = None

        self.patterns = self.carica_file_modelli()
        self.pattern_names = sorted(list(self.patterns.keys()))
        self.selected_pattern_idx = 0
        self.scroll_y = 0

        self.init_ui()

    def open_wiki(self):
        webbrowser.open(WIKI_URL)

    def carica_file_modelli(self):
        if not os.path.exists(FILE_MODELLI):
            with open(FILE_MODELLI, 'w') as f:
                json.dump(MODELLI_DEFAULT, f, indent=4)
            return MODELLI_DEFAULT.copy()
        try:
            with open(FILE_MODELLI, 'r') as f:
                return json.load(f)
        except Exception:
            return MODELLI_DEFAULT.copy()

    def salva_file_modelli(self):
        with open(FILE_MODELLI, 'w') as f:
            json.dump(self.patterns, f, indent=4)

    def init_ui(self):
        self.buttons = []

        # PANNELLO SINISTRO (Libreria)
        btn_w_l = self.w_left - 40
        self.btn_load = Button(20, self.height - 200, btn_w_l, 35, "CARICA", C_BTN_BG, C_BTN_HOV, self.font_btn, TEXT_COLOR)
        self.btn_save = Button(20, self.height - 155, btn_w_l, 35, "SALVA NUOVO", C_SAVE, (220, 180, 255), self.font_btn)
        self.btn_rename = Button(20, self.height - 105, (btn_w_l // 2) - 5, 30, "RINOMINA", C_ACTION, (160, 200, 255), self.font_small)
        self.btn_delete = Button(20 + (btn_w_l // 2) + 5, self.height - 105, (btn_w_l // 2) - 5, 30, "ELIMINA", C_STOP, (255, 160, 180), self.font_small)

        # PANNELLO DESTRO (Controlli)
        r_x = self.w_left + self.w_center + 20
        btn_w_r = self.w_right - 40
        y0 = self.top_bar_h

        self.btn_start = Button(r_x, y0 + 50, btn_w_r, 42, "AVVIA", C_START, (180, 240, 180), self.font_title)
        self.btn_stop = Button(r_x, y0 + 102, btn_w_r, 34, "PAUSA", C_STOP, (255, 160, 180), self.font_btn)
        self.btn_reset = Button(r_x, y0 + 146, btn_w_r, 34, "RESETTA", C_RESET, (255, 240, 190), self.font_btn)

        self.btn_mode = Button(r_x, y0 + 198, btn_w_r - 80, 30, "MODALITÀ: INFINITA", C_BTN_BG, C_BTN_HOV, self.font_small, TEXT_COLOR)
        self.btn_resize = Button(r_x + btn_w_r - 70, y0 + 198, 70, 30, "DIM", C_BTN_BG, C_BTN_HOV, self.font_small, TEXT_COLOR)

        self.btn_spd_down = Button(r_x, y0 + 258, 40, 30, "-", C_BTN_BG, C_BTN_HOV, self.font_title, TEXT_COLOR)
        self.btn_spd_up = Button(r_x + btn_w_r - 40, y0 + 258, 40, 30, "+", C_BTN_BG, C_BTN_HOV, self.font_title, TEXT_COLOR)

        self.btn_zoom_down = Button(r_x, y0 + 318, 40, 30, "-", C_BTN_BG, C_BTN_HOV, self.font_title, TEXT_COLOR)
        self.btn_zoom_up = Button(r_x + btn_w_r - 40, y0 + 318, 40, 30, "+", C_BTN_BG, C_BTN_HOV, self.font_title, TEXT_COLOR)

        self.buttons.extend([
            self.btn_load, self.btn_save, self.btn_rename, self.btn_delete,
            self.btn_start, self.btn_stop, self.btn_reset, self.btn_mode, self.btn_resize,
            self.btn_spd_down, self.btn_spd_up, self.btn_zoom_down, self.btn_zoom_up
        ])
        self.update_mode_button()

    def update_mode_button(self):
        if self.is_infinite:
            self.btn_mode.text = "MODALITÀ: INFINITA"
        else:
            self.btn_mode.text = f"LIMITATA: {self.grid_w}x{self.grid_h}"

    def _make_modal_background(self):
        background = self.screen.copy()
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        background.blit(overlay, (0, 0))
        return background

    def show_popup(self, title, msg, type="msg"):
        box_w, box_h = 460, 200
        box_x = (self.width - box_w) // 2
        box_y = (self.height - box_h) // 2
        rect = pygame.Rect(box_x, box_y, box_w, box_h)
        input_text = ""
        clock = pygame.time.Clock()
        background = self._make_modal_background()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if type == "input":
                        if event.key == pygame.K_RETURN:
                            return input_text
                        elif event.key == pygame.K_BACKSPACE:
                            input_text = input_text[:-1]
                        elif event.key == pygame.K_ESCAPE:
                            return None
                        elif event.unicode.isprintable() and len(input_text) < 45:
                            input_text += event.unicode
                    else:
                        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                            if type == "yesno" and event.key == pygame.K_ESCAPE:
                                return False
                            if type == "yesno" and event.key == pygame.K_RETURN:
                                return True
                            return None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx, my = event.pos
                    if type == "msg":
                        if box_y + 140 <= my <= box_y + 170 and box_x + 180 <= mx <= box_x + 280:
                            return None
                    elif type == "yesno":
                        if box_y + 140 <= my <= box_y + 170:
                            if box_x + 90 <= mx <= box_x + 190:
                                return True
                            if box_x + 270 <= mx <= box_x + 370:
                                return False

            self.screen.blit(background, (0, 0))
            pygame.draw.rect(self.screen, BG_PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, GRID_COLOR, rect, 2, border_radius=10)
            self.screen.blit(self.font_title.render(title, True, C_SAVE), (box_x + 20, box_y + 20))
            self.screen.blit(self.font_list.render(msg, True, TEXT_COLOR), (box_x + 20, box_y + 60))

            if type == "input":
                pygame.draw.rect(self.screen, BG_MAIN, (box_x + 20, box_y + 100, box_w - 40, 30), border_radius=5)
                cursor = "|" if pygame.time.get_ticks() % 1000 < 500 else ""
                self.screen.blit(self.font_list.render(input_text + cursor, True, CELL_ALIVE), (box_x + 25, box_y + 105))
                self.screen.blit(self.font_small.render("Invio per confermare, ESC per annullare", True, TEXT_MUTED), (box_x + 20, box_y + 145))
            elif type == "yesno":
                pygame.draw.rect(self.screen, C_START, (box_x + 90, box_y + 140, 100, 30), border_radius=5)
                self.screen.blit(self.font_btn.render("SÌ", True, (20, 20, 30)), (box_x + 132, box_y + 146))
                pygame.draw.rect(self.screen, C_STOP, (box_x + 270, box_y + 140, 100, 30), border_radius=5)
                self.screen.blit(self.font_btn.render("NO", True, (20, 20, 30)), (box_x + 308, box_y + 146))
            else:
                pygame.draw.rect(self.screen, C_SAVE, (box_x + 180, box_y + 140, 100, 30), border_radius=5)
                self.screen.blit(self.font_btn.render("OK", True, (20, 20, 30)), (box_x + 220, box_y + 146))

            pygame.display.flip()
            clock.tick(30)

    # --- FILE CHOOSER NATIVO PER FILE .RLE ---
    def show_file_chooser(self, ext=".rle"):
        box_w, box_h = 620, 480
        box_x = (self.width - box_w) // 2
        box_y = (self.height - box_h) // 2
        rect = pygame.Rect(box_x, box_y, box_w, box_h)
        list_rect = pygame.Rect(box_x + 20, box_y + 85, box_w - 40, box_h - 155)

        btn_open = Button(box_x + box_w - 230, box_y + box_h - 50, 100, 34, "APRI", C_START, (180, 240, 180), self.font_btn)
        btn_cancel = Button(box_x + box_w - 120, box_y + box_h - 50, 100, 34, "ANNULLA", C_STOP, (255, 160, 180), self.font_btn)

        current_dir = self.last_dir if os.path.isdir(self.last_dir) else os.getcwd()
        scroll = 0
        selected_idx = 0
        last_click_time = 0
        last_click_idx = -1

        def list_entries(directory):
            entries = [("..", True)]
            try:
                items = os.listdir(directory)
                dirs = sorted(d for d in items if not d.startswith(".") and os.path.isdir(os.path.join(directory, d)))
                files = sorted(f for f in items if f.lower().endswith(ext) and os.path.isfile(os.path.join(directory, f)))
                for d in dirs:
                    entries.append((d, True))
                for f in files:
                    entries.append((f, False))
            except PermissionError:
                pass
            return entries

        entries = list_entries(current_dir)
        background = self._make_modal_background()
        clock = pygame.time.Clock()
        row_h = 26

        while True:
            mouse_pos = pygame.mouse.get_pos()
            btn_open.check_hover(mouse_pos)
            btn_cancel.check_hover(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_RETURN and 0 <= selected_idx < len(entries):
                        name, is_dir = entries[selected_idx]
                        full_path = os.path.normpath(os.path.join(current_dir, name))
                        if is_dir:
                            current_dir = full_path
                            self.last_dir = current_dir
                            entries = list_entries(current_dir)
                            selected_idx = 0
                            scroll = 0
                        else:
                            self.last_dir = current_dir
                            return full_path
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if btn_cancel.rect.collidepoint(mouse_pos):
                            return None
                        elif btn_open.rect.collidepoint(mouse_pos) and 0 <= selected_idx < len(entries):
                            name, is_dir = entries[selected_idx]
                            full_path = os.path.normpath(os.path.join(current_dir, name))
                            if is_dir:
                                current_dir = full_path
                                self.last_dir = current_dir
                                entries = list_entries(current_dir)
                                selected_idx = 0
                                scroll = 0
                            else:
                                self.last_dir = current_dir
                                return full_path
                        elif list_rect.collidepoint(mouse_pos):
                            idx = (mouse_pos[1] - list_rect.y - 5 - scroll) // row_h
                            if 0 <= idx < len(entries):
                                now = pygame.time.get_ticks()
                                if idx == last_click_idx and now - last_click_time < 350:
                                    name, is_dir = entries[idx]
                                    full_path = os.path.normpath(os.path.join(current_dir, name))
                                    if is_dir:
                                        current_dir = full_path
                                        self.last_dir = current_dir
                                        entries = list_entries(current_dir)
                                        selected_idx = 0
                                        scroll = 0
                                    else:
                                        self.last_dir = current_dir
                                        return full_path
                                else:
                                    selected_idx = idx
                                last_click_idx = idx
                                last_click_time = now
                    elif event.button in (4, 5) and list_rect.collidepoint(mouse_pos):
                        if event.button == 4:
                            scroll = min(0, scroll + 26)
                        else:
                            max_scroll = -max(0, len(entries) * row_h - list_rect.height + 10)
                            scroll = max(max_scroll, scroll - 26)

            self.screen.blit(background, (0, 0))
            pygame.draw.rect(self.screen, BG_PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, GRID_COLOR, rect, 2, border_radius=10)

            self.screen.blit(self.font_title.render("Seleziona file .rle", True, C_SAVE), (box_x + 20, box_y + 18))

            disp_dir = current_dir if len(current_dir) <= 68 else "..." + current_dir[-65:]
            self.screen.blit(self.font_small.render(disp_dir, True, TEXT_MUTED), (box_x + 20, box_y + 54))

            pygame.draw.rect(self.screen, BG_MAIN, list_rect, border_radius=6)
            self.screen.set_clip(list_rect)
            for i, (name, is_dir) in enumerate(entries):
                y = list_rect.y + 5 + scroll + i * row_h
                if y + row_h < list_rect.y or y > list_rect.bottom:
                    continue
                if i == selected_idx:
                    pygame.draw.rect(self.screen, C_BTN_HOV, (list_rect.x + 4, y, list_rect.width - 8, row_h - 2), border_radius=4)
                prefix = "[DIR]  " if is_dir else "[RLE]  "
                color = C_ACTION if is_dir else CELL_ALIVE
                self.screen.blit(self.font_list.render(prefix + name, True, color), (list_rect.x + 12, y + 3))
            self.screen.set_clip(None)

            self.screen.blit(self.font_small.render("Doppio clic su una cartella per aprirla o su un file .rle", True, TEXT_MUTED), (box_x + 20, box_y + box_h - 42))
            btn_open.draw(self.screen)
            btn_cancel.draw(self.screen)

            pygame.display.flip()
            clock.tick(60)

    # --- CASELLA DI TESTO MULTIRIGA PER INCOLLARE RLE ---
    def show_rle_paste_popup(self):
        box_w, box_h = 640, 440
        box_x = (self.width - box_w) // 2
        box_y = (self.height - box_h) // 2
        rect = pygame.Rect(box_x, box_y, box_w, box_h)
        text_rect = pygame.Rect(box_x + 20, box_y + 80, box_w - 40, box_h - 150)

        btn_paste = Button(box_x + 20, box_y + box_h - 50, 110, 34, "INCOLLA", C_ACTION, (160, 200, 255), self.font_btn)
        btn_clear = Button(box_x + 140, box_y + box_h - 50, 95, 34, "PULISCI", C_RESET, (255, 240, 190), self.font_btn)
        btn_import = Button(box_x + box_w - 230, box_y + box_h - 50, 100, 34, "IMPORTA", C_START, (180, 240, 180), self.font_btn)
        btn_cancel = Button(box_x + box_w - 120, box_y + box_h - 50, 100, 34, "ANNULLA", C_STOP, (255, 160, 180), self.font_btn)

        text_content = ""
        background = self._make_modal_background()
        clock = pygame.time.Clock()
        line_h = 18

        while True:
            mouse_pos = pygame.mouse.get_pos()
            for b in (btn_paste, btn_clear, btn_import, btn_cancel):
                b.check_hover(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    is_cmd_or_ctrl = bool(mods & (pygame.KMOD_META | pygame.KMOD_CTRL))
                    if event.key == pygame.K_ESCAPE:
                        return None
                    elif event.key == pygame.K_v and is_cmd_or_ctrl:
                        pasted = get_clipboard_text()
                        if pasted:
                            text_content += pasted.replace("\r\n", "\n").replace("\r", "\n")
                    elif event.key == pygame.K_BACKSPACE:
                        text_content = text_content[:-1]
                    elif event.key == pygame.K_RETURN:
                        text_content += "\n"
                    elif event.unicode and event.unicode.isprintable():
                        text_content += event.unicode
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_cancel.rect.collidepoint(mouse_pos):
                        return None
                    elif btn_import.rect.collidepoint(mouse_pos):
                        return text_content
                    elif btn_clear.rect.collidepoint(mouse_pos):
                        text_content = ""
                    elif btn_paste.rect.collidepoint(mouse_pos):
                        pasted = get_clipboard_text()
                        if pasted:
                            text_content += pasted.replace("\r\n", "\n").replace("\r", "\n")

            self.screen.blit(background, (0, 0))
            pygame.draw.rect(self.screen, BG_PANEL, rect, border_radius=10)
            pygame.draw.rect(self.screen, GRID_COLOR, rect, 2, border_radius=10)

            self.screen.blit(self.font_title.render("Incolla codice RLE", True, C_SAVE), (box_x + 20, box_y + 18))
            self.screen.blit(self.font_small.render("Usa Cmd+V / Ctrl+V oppure il pulsante INCOLLA qui sotto:", True, TEXT_MUTED), (box_x + 20, box_y + 52))

            pygame.draw.rect(self.screen, BG_MAIN, text_rect, border_radius=6)
            pygame.draw.rect(self.screen, GRID_COLOR, text_rect, 1, border_radius=6)

            self.screen.set_clip(text_rect)
            cursor = "|" if pygame.time.get_ticks() % 1000 < 500 else ""
            raw_lines = (text_content + cursor).split("\n")
            max_visible = (text_rect.height - 12) // line_h
            visible_lines = raw_lines[-max_visible:] if len(raw_lines) > max_visible else raw_lines

            for i, ln in enumerate(visible_lines):
                surf = self.font_mono.render(ln[:74], True, CELL_ALIVE)
                self.screen.blit(surf, (text_rect.x + 8, text_rect.y + 8 + i * line_h))
            self.screen.set_clip(None)

            for b in (btn_paste, btn_clear, btn_import, btn_cancel):
                b.draw(self.screen)

            pygame.display.flip()
            clock.tick(60)

    # --- IMPORT / EXPORT RLE ---
    def _finalize_rle_import(self, rle_text, default_name="Incollato"):
        rle_name, coords = parse_rle(rle_text)
        if not coords:
            self.show_popup("Errore", "Nessuna cella valida trovata nel codice RLE.", "msg")
            return

        base_name = rle_name if rle_name else default_name
        pattern_key = f"[RLE] {base_name}"

        min_r = min(r for r, c in coords)
        min_c = min(c for r, c in coords)
        coords_norm = [[r - min_r, c - min_c] for r, c in coords]

        self.patterns[pattern_key] = coords_norm
        self.salva_file_modelli()
        self.pattern_names = sorted(list(self.patterns.keys()))
        self.selected_pattern_idx = self.pattern_names.index(pattern_key)

        self.load_selected_pattern()
        self.show_popup("Importazione Riuscita", f"Caricato '{pattern_key}' ({len(coords_norm)} celle).", "msg")

    def import_rle_file(self):
        self.running = False
        path = self.show_file_chooser(ext=".rle")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            default_name = os.path.splitext(os.path.basename(path))[0]
            self._finalize_rle_import(content, default_name=default_name)
        except Exception as e:
            self.show_popup("Errore", f"Errore lettura RLE: {str(e)[:40]}", "msg")

    def import_rle_paste(self):
        self.running = False
        rle_text = self.show_rle_paste_popup()
        if not rle_text or not rle_text.strip():
            return
        self._finalize_rle_import(rle_text, default_name="Modello Incollato")

    def export_grid_rle(self):
        cells = self.initial_cells if (self.cicli > 0 and self.initial_cells) else self.alive_cells
        if not cells:
            self.show_popup("Attenzione", "La griglia è vuota!", "msg")
            return

        filename = self.show_popup("Esporta Griglia RLE", "Nome file di destinazione (es. mio.rle):", "input")
        if not filename or not filename.strip():
            return

        path = filename.strip()
        if not path.lower().endswith(".rle"):
            path += ".rle"

        coords = [[y, x] for x, y in cells]
        model_name = os.path.splitext(os.path.basename(path))[0]
        rle_content = encode_rle(coords, name=model_name)

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rle_content)
            self.show_popup("Esportazione Riuscita", f"Salvato in '{path}'!", "msg")
        except Exception as e:
            self.show_popup("Errore", f"Impossibile salvare: {str(e)[:40]}", "msg")

    def export_selected_rle(self):
        if not self.pattern_names:
            return
        name = self.pattern_names[self.selected_pattern_idx]
        coords = self.patterns[name]
        if not coords:
            self.show_popup("Attenzione", "Il modello selezionato è vuoto.", "msg")
            return

        filename = self.show_popup("Esporta Modello RLE", f"Nome file per '{name[:20]}':", "input")
        if not filename or not filename.strip():
            return

        path = filename.strip()
        if not path.lower().endswith(".rle"):
            path += ".rle"

        rle_content = encode_rle(coords, name=name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(rle_content)
            self.show_popup("Esportazione Riuscita", f"Salvato in '{path}'!", "msg")
        except Exception as e:
            self.show_popup("Errore", f"Impossibile salvare: {str(e)[:40]}", "msg")

    # --- LOGICA GRIGLIA ---
    def update_generation(self):
        neighbor_counts = {}
        for x, y in self.alive_cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    coord = (x + dx, y + dy)
                    neighbor_counts[coord] = neighbor_counts.get(coord, 0) + 1

        new_alive = set()
        for (cx, cy), count in neighbor_counts.items():
            if count == 3 or (count == 2 and (cx, cy) in self.alive_cells):
                if not self.is_infinite:
                    if 0 <= cx < self.grid_w and 0 <= cy < self.grid_h:
                        new_alive.add((cx, cy))
                else:
                    new_alive.add((cx, cy))

        self.cicli += 1

        if not new_alive:
            self.running = False
            self.end_message = f"Morte al ciclo {self.cicli}!"
        elif not self.end_message:
            fs_new = frozenset(new_alive)
            if fs_new == frozenset(self.alive_cells):
                self.running = False
                self.end_message = f"Stabile dal ciclo {self.cicli}"
            elif fs_new in self.history:
                periodo = len(self.history) - self.history.index(fs_new)
                self.end_message = f"Oscillatore (p.{periodo}) dal {self.cicli}"
            else:
                self.history.append(fs_new)
                if len(self.history) > 30:
                    self.history.pop(0)

        self.alive_cells = new_alive

    def reset_status(self):
        self.history.clear()
        self.end_message = ""

    # --- AZIONI BOTTONI ---
    def handle_btn_click(self, pos):
        if self.btn_start.rect.collidepoint(pos) and not self.running:
            if self.cicli == 0:
                self.initial_cells = self.alive_cells.copy()
            self.reset_status()
            self.running = True
        elif self.btn_stop.rect.collidepoint(pos):
            self.running = False
        elif self.btn_reset.rect.collidepoint(pos):
            self.running = False
            self.alive_cells.clear()
            self.cicli = 0
            self.initial_cells.clear()
            self.reset_status()
            if not self.is_infinite:
                self.camera_x = self.w_center // 2 - (self.grid_w * self.cell_size) // 2
                self.camera_y = self.grid_view_h // 2 - (self.grid_h * self.cell_size) // 2
            else:
                self.camera_x = self.w_center // 2
                self.camera_y = self.grid_view_h // 2

        elif self.btn_load.rect.collidepoint(pos):
            self.load_selected_pattern()
        elif self.btn_save.rect.collidepoint(pos):
            self.save_pattern()
        elif self.btn_rename.rect.collidepoint(pos):
            self.rename_pattern()
        elif self.btn_delete.rect.collidepoint(pos):
            self.delete_pattern()

        elif self.btn_mode.rect.collidepoint(pos):
            self.is_infinite = not self.is_infinite
            self.update_mode_button()
            if not self.is_infinite:
                self.alive_cells = {c for c in self.alive_cells if 0 <= c[0] < self.grid_w and 0 <= c[1] < self.grid_h}
                self.reset_status()

        elif self.btn_resize.rect.collidepoint(pos) and not self.is_infinite:
            res = self.show_popup("Dimensioni", "Righe,Colonne (es: 100,100):", "input")
            if res:
                try:
                    r, c = map(int, res.split(','))
                    self.grid_w, self.grid_h = c, r
                    self.update_mode_button()
                    self.alive_cells = {cell for cell in self.alive_cells if 0 <= cell[0] < self.grid_w and 0 <= cell[1] < self.grid_h}
                except Exception:
                    self.show_popup("Errore", "Formato non valido.", "msg")

        elif self.btn_spd_up.rect.collidepoint(pos):
            self.speed_ms = max(10, self.speed_ms - 20)
        elif self.btn_spd_down.rect.collidepoint(pos):
            self.speed_ms = min(500, self.speed_ms + 20)
        elif self.btn_zoom_up.rect.collidepoint(pos):
            self.change_zoom(2)
        elif self.btn_zoom_down.rect.collidepoint(pos):
            self.change_zoom(-2)

    def change_zoom(self, delta):
        old_size = self.cell_size
        new_size = max(1, min(100, old_size + delta))
        if old_size != new_size:
            center_x_world = (self.w_center / 2 - self.camera_x) / old_size
            center_y_world = (self.grid_view_h / 2 - self.camera_y) / old_size
            self.cell_size = new_size
            self.camera_x = self.w_center / 2 - center_x_world * new_size
            self.camera_y = self.grid_view_h / 2 - center_y_world * new_size

    def rename_pattern(self):
        if not self.pattern_names:
            return
        old_name = self.pattern_names[self.selected_pattern_idx]
        new_name = self.show_popup("Rinomina", f"Nuovo nome per '{old_name}':", "input")
        if new_name and new_name.strip() != "":
            if "[Personale]" not in new_name:
                new_name = f"[Personale] {new_name.strip()}"
            self.patterns[new_name] = self.patterns.pop(old_name)
            self.salva_file_modelli()
            self.pattern_names = sorted(list(self.patterns.keys()))
            self.selected_pattern_idx = self.pattern_names.index(new_name)

    def delete_pattern(self):
        if not self.pattern_names:
            return
        name = self.pattern_names[self.selected_pattern_idx]
        if self.show_popup("Elimina", f"Eliminare '{name}'?", "yesno"):
            del self.patterns[name]
            self.salva_file_modelli()
            self.pattern_names = sorted(list(self.patterns.keys()))
            if self.selected_pattern_idx >= len(self.pattern_names):
                self.selected_pattern_idx = max(0, len(self.pattern_names) - 1)

    # --- INTERAZIONE GRIGLIA E MINIMAPPA ---
    def screen_to_world(self, sx, sy):
        wx = (sx - self.w_left - self.camera_x) // self.cell_size
        wy = (sy - self.top_bar_h - self.camera_y) // self.cell_size
        return int(wx), int(wy)

    def handle_grid_click(self, pos):
        x, y = pos
        if self.w_left <= x < self.w_left + self.w_center and y >= self.top_bar_h:
            wx, wy = self.screen_to_world(x, y)
            if not self.is_infinite and not (0 <= wx < self.grid_w and 0 <= wy < self.grid_h):
                return
            if (wx, wy) in self.alive_cells:
                self.brush_mode = 0
                self.alive_cells.remove((wx, wy))
            else:
                self.brush_mode = 1
                self.alive_cells.add((wx, wy))
            self.reset_status()

    def handle_grid_drag(self, pos):
        x, y = pos
        if self.w_left <= x < self.w_left + self.w_center and y >= self.top_bar_h:
            wx, wy = self.screen_to_world(x, y)
            if not self.is_infinite and not (0 <= wx < self.grid_w and 0 <= wy < self.grid_h):
                return
            if self.brush_mode == 1:
                self.alive_cells.add((wx, wy))
            elif self.brush_mode == 0 and (wx, wy) in self.alive_cells:
                self.alive_cells.remove((wx, wy))
            self.reset_status()

    def handle_minimap_click(self, pos):
        if not self.minimap_data:
            return
        min_x, min_y, scale, off_x, off_y = self.minimap_data
        mx, my = pos
        world_x = (mx - off_x) / scale + min_x
        world_y = (my - off_y) / scale + min_y
        self.camera_x = self.w_center / 2 - world_x * self.cell_size
        self.camera_y = self.grid_view_h / 2 - world_y * self.cell_size

    def load_selected_pattern(self):
        if not self.pattern_names:
            return
        name = self.pattern_names[self.selected_pattern_idx]
        coords = self.patterns[name]

        self.running = False
        self.alive_cells.clear()
        self.cicli = 0
        self.reset_status()

        if coords:
            max_r = max(r for r, c in coords)
            max_c = max(c for r, c in coords)
            if self.is_infinite:
                offset_x = -max_c // 2
                offset_y = -max_r // 2
                self.camera_x = self.w_center // 2
                self.camera_y = self.grid_view_h // 2
            else:
                offset_x = (self.grid_w - max_c) // 2
                offset_y = (self.grid_h - max_r) // 2
                self.camera_x = self.w_center // 2 - (self.grid_w * self.cell_size) // 2
                self.camera_y = self.grid_view_h // 2 - (self.grid_h * self.cell_size) // 2

            for r, c in coords:
                wx, wy = c + offset_x, r + offset_y
                if not self.is_infinite:
                    if 0 <= wx < self.grid_w and 0 <= wy < self.grid_h:
                        self.alive_cells.add((wx, wy))
                else:
                    self.alive_cells.add((wx, wy))

        self.initial_cells = self.alive_cells.copy()

    def save_pattern(self):
        cells_to_save = self.initial_cells if (self.cicli > 0 and self.initial_cells) else self.alive_cells
        if not cells_to_save:
            self.show_popup("Attenzione", "Nessuna cella da salvare!", "msg")
            return
        nome = self.show_popup("Salva Modello", "Nome:", "input")
        if not nome or nome.strip() == "":
            return
        nome_form = f"[Personale] {nome.strip()}"
        min_x = min(x for x, y in cells_to_save)
        min_y = min(y for x, y in cells_to_save)
        coords_norm = [[y - min_y, x - min_x] for x, y in cells_to_save]
        self.patterns[nome_form] = coords_norm
        self.salva_file_modelli()
        self.pattern_names = sorted(list(self.patterns.keys()))
        self.selected_pattern_idx = self.pattern_names.index(nome_form)
        self.show_popup("Successo", "Modello salvato!", "msg")

    # --- RENDERING ---
    def draw(self):
        self.screen.fill(BG_MAIN)

        # 1. GRIGLIA CENTRALE
        grid_clip = pygame.Rect(self.w_left, self.top_bar_h, self.w_center, self.grid_view_h)
        self.screen.set_clip(grid_clip)

        if self.is_infinite or self.cell_size >= 4:
            start_x = self.camera_x % self.cell_size
            for x in range(int(start_x), self.w_center, self.cell_size):
                pygame.draw.line(self.screen, GRID_COLOR, (self.w_left + x, self.top_bar_h), (self.w_left + x, self.height))
            start_y = self.camera_y % self.cell_size
            for y in range(int(start_y), self.grid_view_h, self.cell_size):
                pygame.draw.line(self.screen, GRID_COLOR, (self.w_left, self.top_bar_h + y), (self.w_left + self.w_center, self.top_bar_h + y))

        if not self.is_infinite:
            rect_x = self.w_left + self.camera_x
            rect_y = self.top_bar_h + self.camera_y
            rect_w = self.grid_w * self.cell_size
            rect_h = self.grid_h * self.cell_size
            pygame.draw.rect(self.screen, (35, 35, 52), (rect_x, rect_y, rect_w, rect_h))
            pygame.draw.rect(self.screen, BORDER_COLOR, (rect_x, rect_y, rect_w, rect_h), 2)

        for x, y in self.alive_cells:
            sx = self.w_left + x * self.cell_size + self.camera_x
            sy = self.top_bar_h + y * self.cell_size + self.camera_y
            if self.w_left - self.cell_size <= sx < self.w_left + self.w_center and self.top_bar_h - self.cell_size <= sy < self.height:
                if self.cell_size > 2:
                    inner_rect = pygame.Rect(sx + 1, sy + 1, self.cell_size - 2, self.cell_size - 2)
                    pygame.draw.rect(self.screen, CELL_ALIVE, inner_rect, border_radius=max(1, self.cell_size // 4))
                else:
                    pygame.draw.rect(self.screen, CELL_ALIVE, (sx, sy, self.cell_size, self.cell_size))

        self.screen.set_clip(None)

        # 2. PANNELLO LIBRERIA (Sinistra)
        pygame.draw.rect(self.screen, BG_PANEL, (0, self.top_bar_h, self.w_left, self.grid_view_h))
        self.screen.blit(self.font_title.render("LIBRERIA MODELLI", True, TEXT_COLOR), (20, self.top_bar_h + 15))

        list_rect = pygame.Rect(20, self.top_bar_h + 52, self.w_left - 40, self.grid_view_h - 270)
        pygame.draw.rect(self.screen, BG_MAIN, list_rect, border_radius=5)
        self.screen.set_clip(list_rect)
        y_offset = self.top_bar_h + 57 + self.scroll_y
        for i, name in enumerate(self.pattern_names):
            color = C_START if i == self.selected_pattern_idx else TEXT_COLOR
            txt = self.font_list.render(name, True, color)
            self.screen.blit(txt, (30, y_offset + (i * 25)))
        self.screen.set_clip(None)

        # 3. PANNELLO CONTROLLI E MINIMAPPA (Destra)
        right_start = self.w_left + self.w_center
        y0 = self.top_bar_h
        pygame.draw.rect(self.screen, BG_PANEL, (right_start, y0, self.w_right, self.grid_view_h))

        status_txt = "IN ESECUZIONE" if self.running else "IN PAUSA"
        status_color = C_START if self.running else C_STOP
        self.screen.blit(self.font_title.render(f"STATO: {status_txt}", True, status_color), (right_start + 20, y0 + 15))

        self.screen.blit(self.font_btn.render(f"Velocità: {self.speed_ms} ms", True, TEXT_COLOR), (right_start + 20, y0 + 236))
        self.screen.blit(self.font_btn.render(f"Zoom: {self.cell_size} px", True, TEXT_COLOR), (right_start + 20, y0 + 296))

        self.screen.blit(self.font_btn.render(f"Ciclo: {self.cicli}  |  Pop: {len(self.alive_cells)}", True, TEXT_COLOR), (right_start + 20, y0 + 365))
        if self.end_message:
            self.screen.blit(self.font_small.render(self.end_message, True, C_SAVE), (right_start + 20, y0 + 390))

        for btn in self.buttons:
            btn.draw(self.screen)

        self.draw_minimap(self.screen, self.minimap_rect)
        self.screen.blit(self.font_title.render("MINIMAPPA (Radar)", True, TEXT_COLOR), (right_start + 20, self.minimap_rect.y - 30))

        # 4. BARRA MENU SUPERIORE
        pygame.draw.rect(self.screen, BG_MENU, (0, 0, self.width, self.top_bar_h))
        pygame.draw.line(self.screen, GRID_COLOR, (0, self.top_bar_h), (self.width, self.top_bar_h))

        mouse_pos = pygame.mouse.get_pos()
        for key, m in self.menus.items():
            m_bg = C_BTN_HOV if (self.open_menu == key or m["rect"].collidepoint(mouse_pos)) else C_BTN_BG
            pygame.draw.rect(self.screen, m_bg, m["rect"], border_radius=4)
            self.screen.blit(self.font_btn.render(m["label"], True, TEXT_COLOR), (m["rect"].x + 12, m["rect"].y + 4))

        if self.open_menu in self.menus:
            m = self.menus[self.open_menu]
            drop_w = m["drop_w"]
            drop_h = len(m["items"]) * 32 + 8
            drop_rect = pygame.Rect(m["rect"].x, self.top_bar_h, drop_w, drop_h)
            pygame.draw.rect(self.screen, BG_MENU, drop_rect, border_radius=5)
            pygame.draw.rect(self.screen, GRID_COLOR, drop_rect, 1, border_radius=5)

            for idx, (label, _) in enumerate(m["items"]):
                item_rect = pygame.Rect(drop_rect.x + 4, drop_rect.y + 4 + idx * 32, drop_w - 8, 28)
                if item_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(self.screen, C_BTN_HOV, item_rect, border_radius=4)
                self.screen.blit(self.font_list.render(label, True, TEXT_COLOR), (item_rect.x + 10, item_rect.y + 5))

        pygame.display.flip()

    def draw_minimap(self, surface, rect):
        pygame.draw.rect(surface, BG_MAIN, rect, border_radius=5)
        pygame.draw.rect(surface, GRID_COLOR, rect, 2, border_radius=5)

        view_min_x = -self.camera_x / self.cell_size
        view_max_x = (self.w_center - self.camera_x) / self.cell_size
        view_min_y = -self.camera_y / self.cell_size
        view_max_y = (self.grid_view_h - self.camera_y) / self.cell_size

        if not self.alive_cells:
            min_x, max_x = view_min_x, view_max_x
            min_y, max_y = view_min_y, view_max_y
        else:
            min_x = min(c[0] for c in self.alive_cells)
            max_x = max(c[0] for c in self.alive_cells)
            min_y = min(c[1] for c in self.alive_cells)
            max_y = max(c[1] for c in self.alive_cells)

            min_x = min(min_x, view_min_x) - 10
            max_x = max(max_x, view_max_x) + 10
            min_y = min(min_y, view_min_y) - 10
            max_y = max(max_y, view_max_y) + 10

            if not self.is_infinite:
                min_x = min(min_x, 0) - 2
                max_x = max(max_x, self.grid_w) + 2
                min_y = min(min_y, 0) - 2
                max_y = max(max_y, self.grid_h) + 2

        world_w = max_x - min_x
        world_h = max_y - min_y
        if world_w == 0 or world_h == 0:
            return

        scale = min((rect.width - 10) / world_w, (rect.height - 10) / world_h)
        off_x = rect.x + (rect.width - world_w * scale) / 2
        off_y = rect.y + (rect.height - world_h * scale) / 2

        self.minimap_data = (min_x, min_y, scale, off_x, off_y)

        if not self.is_infinite:
            bx = off_x + (0 - min_x) * scale
            by = off_y + (0 - min_y) * scale
            bw = self.grid_w * scale
            bh = self.grid_h * scale
            pygame.draw.rect(surface, (50, 50, 70), (bx, by, bw, bh))

        for cx, cy in self.alive_cells:
            px = off_x + (cx - min_x) * scale
            py = off_y + (cy - min_y) * scale
            pygame.draw.rect(surface, CELL_ALIVE, (px, py, max(1, scale), max(1, scale)))

        vp_x = off_x + (view_min_x - min_x) * scale
        vp_y = off_y + (view_min_y - min_y) * scale
        vp_w = (view_max_x - view_min_x) * scale
        vp_h = (view_max_y - view_min_y) * scale
        pygame.draw.rect(surface, (255, 255, 255), (vp_x, vp_y, vp_w, vp_h), 1)

    def run(self):
        clock = pygame.time.Clock()

        while True:
            clock.tick(60)

            current_time = pygame.time.get_ticks()
            if self.running and current_time - self.last_update_time > self.speed_ms:
                self.update_generation()
                self.last_update_time = current_time

            mouse_pos = pygame.mouse.get_pos()
            for btn in self.buttons:
                btn.check_hover(mouse_pos)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        # 1. Click sui bottoni della barra menù
                        toggled_menu = False
                        for key, m in self.menus.items():
                            if m["rect"].collidepoint(mouse_pos):
                                self.open_menu = None if self.open_menu == key else key
                                toggled_menu = True
                                break
                        if toggled_menu:
                            continue

                        # 2. Click sulle voci del menù aperto
                        if self.open_menu in self.menus:
                            m = self.menus[self.open_menu]
                            drop_w = m["drop_w"]
                            clicked_item = False
                            for idx, (_, callback) in enumerate(m["items"]):
                                item_rect = pygame.Rect(m["rect"].x + 4, self.top_bar_h + 4 + idx * 32, drop_w - 8, 28)
                                if item_rect.collidepoint(mouse_pos):
                                    self.open_menu = None
                                    callback()
                                    clicked_item = True
                                    break
                            self.open_menu = None
                            if clicked_item:
                                continue

                        # 3. Resto dell'interfaccia
                        self.handle_btn_click(mouse_pos)

                        if self.minimap_rect.collidepoint(mouse_pos):
                            self.handle_minimap_click(mouse_pos)

                        list_rect = pygame.Rect(20, self.top_bar_h + 52, self.w_left - 40, self.grid_view_h - 270)
                        if list_rect.collidepoint(mouse_pos):
                            rel_y = mouse_pos[1] - (self.top_bar_h + 52) - self.scroll_y
                            idx = rel_y // 25
                            if 0 <= idx < len(self.pattern_names):
                                self.selected_pattern_idx = idx

                        self.handle_grid_click(mouse_pos)

                    elif event.button == 3:
                        self.open_menu = None
                        if self.w_left <= mouse_pos[0] < self.w_left + self.w_center and mouse_pos[1] >= self.top_bar_h:
                            self.is_panning = True
                            self.last_mouse_pos = mouse_pos

                    elif event.button in (4, 5):
                        list_rect = pygame.Rect(20, self.top_bar_h + 52, self.w_left - 40, self.grid_view_h - 270)
                        if list_rect.collidepoint(mouse_pos):
                            if event.button == 4:
                                self.scroll_y = min(0, self.scroll_y + 20)
                            elif event.button == 5:
                                max_scroll = -max(0, (len(self.pattern_names) * 25) - list_rect.height + 20)
                                self.scroll_y = max(max_scroll, self.scroll_y - 20)
                        elif self.w_left <= mouse_pos[0] < self.w_left + self.w_center and mouse_pos[1] >= self.top_bar_h:
                            if event.button == 4:
                                self.change_zoom(2)
                            elif event.button == 5:
                                self.change_zoom(-2)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.brush_mode = None
                    elif event.button == 3:
                        self.is_panning = False

                elif event.type == pygame.MOUSEMOTION:
                    if pygame.mouse.get_pressed()[0] and self.brush_mode is not None:
                        self.handle_grid_drag(mouse_pos)
                    elif pygame.mouse.get_pressed()[0] and self.minimap_rect.collidepoint(mouse_pos):
                        self.handle_minimap_click(mouse_pos)
                    elif self.is_panning:
                        dx = mouse_pos[0] - self.last_mouse_pos[0]
                        dy = mouse_pos[1] - self.last_mouse_pos[1]
                        self.camera_x += dx
                        self.camera_y += dy
                        self.last_mouse_pos = mouse_pos

            self.draw()


if __name__ == "__main__":
    game = GameOfLifePygame()
    game.run()
