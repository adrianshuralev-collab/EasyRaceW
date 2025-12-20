import pygame
import json
import os
import math
import sys

pygame.init()

# === Настройки экрана ===
FULLSCREEN_DEFAULT = True  # начальный режим
info = pygame.display.Info()
NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h
SCREEN_WIDTH = NATIVE_WIDTH if FULLSCREEN_DEFAULT else 800
SCREEN_HEIGHT = NATIVE_HEIGHT if FULLSCREEN_DEFAULT else 600

FPS = 60
TILE_SIZE = 16

# Типы покрытия
SURFACE_TYPES = {
    0: {"name": "offroad", "traction": 0.3, "color": (34, 139, 34)},
    1: {"name": "asphalt", "traction": 1.0, "color": (105, 105, 105)},
    2: {"name": "curb", "traction": 0.6, "color": (169, 169, 169)}
}

os.makedirs("tracks", exist_ok=True)
os.makedirs("assets", exist_ok=True)

# === Вспомогательные функции ===
def load_image(path, fallback_color=(100, 100, 100)):
    if os.path.exists(path):
        return pygame.image.load(path).convert()
    else:
        surf = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
        surf.fill(fallback_color)
        return surf

# === Классы игры ===
class Track:
    def __init__(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        self.name = data['name']
        self.width = data['width']
        self.height = data['height']
        self.tile_size = data['tile_size']
        self.grid = data['grid']
        self.start_pos = data['start_position']

    def get_tile(self, x, y):
        tile_x = int(x // self.tile_size)
        tile_y = int(y // self.tile_size)
        if 0 <= tile_x < self.width and 0 <= tile_y < self.height:
            return self.grid[tile_y][tile_x]
        return 2

    def get_surface_info(self, x, y):
        tile_id = self.get_tile(x, y)
        return SURFACE_TYPES.get(tile_id, SURFACE_TYPES[2])

class Car:
    def __init__(self, x, y, angle=0):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 0
        self.max_speed = 4.0
        self.acceleration = 0.15
        self.friction = 0.1
        self.steering = 2.5

        self.original_image = pygame.Surface((100, 50))
        self.original_image.fill((255, 0, 0))
        if os.path.exists('assets/car.png'):
            self.original_image = pygame.image.load('assets/car.png').convert_alpha()
            self.original_image = pygame.transform.scale(self.original_image, (100, 50))

    def update(self, keys, track):
        if keys[pygame.K_w]:
            self.speed += self.acceleration
        if keys[pygame.K_s]:
            self.speed -= self.acceleration * 0.7
        self.speed = max(-self.max_speed / 2, min(self.speed, self.max_speed))

        if not (keys[pygame.K_w] or keys[pygame.K_s]):
            if self.speed > 0:
                self.speed = max(0, self.speed - self.friction)
            elif self.speed < 0:
                self.speed = min(0, self.speed + self.friction)

        if keys[pygame.K_a]:
            self.angle -= self.steering * (abs(self.speed) / self.max_speed)
        if keys[pygame.K_d]:
            self.angle += self.steering * (abs(self.speed) / self.max_speed)

        rad = math.radians(self.angle)
        dx = self.speed * math.cos(rad)
        dy = self.speed * math.sin(rad)

        surf = track.get_surface_info(self.x + dx, self.y + dy)
        traction = surf['traction']

        self.x += dx * traction
        self.y += dy * traction

class Game:
    def __init__(self, track_path, fullscreen):
        self.fullscreen = fullscreen
        self.set_display_mode()
        self.clock = pygame.time.Clock()
        self.running = True

        self.track = Track(track_path)
        start = self.track.start_pos
        self.car = Car(
            start['x'] * self.track.tile_size + self.track.tile_size // 2,
            start['y'] * self.track.tile_size + self.track.tile_size // 2,
            start.get('angle', 0)
        )

    def set_display_mode(self):
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            self.display_width, self.display_height = NATIVE_WIDTH, NATIVE_HEIGHT
        else:
            self.screen = pygame.display.set_mode((800, 600))
            self.display_width, self.display_height = 800, 600

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.set_display_mode()

    def run(self):
        while self.running:
            keys = pygame.key.get_pressed()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    if event.key == pygame.K_F11:
                        self.toggle_fullscreen()

            self.car.update(keys, self.track)
            self.render()
            self.clock.tick(FPS)

    def render(self):
        camera_x = self.car.x - self.display_width // 2
        camera_y = self.car.y - self.display_height // 2
        self.screen.fill((0, 0, 0))

        for y in range(self.track.height):
            for x in range(self.track.width):
                tile_id = self.track.grid[y][x]
                color = SURFACE_TYPES[tile_id]['color']
                world_x = x * self.track.tile_size
                world_y = y * self.track.tile_size
                screen_x = world_x - camera_x
                screen_y = world_y - camera_y
                rect = pygame.Rect(screen_x, screen_y, self.track.tile_size, self.track.tile_size)
                if -self.track.tile_size < screen_x < self.display_width and -self.track.tile_size < screen_y < self.display_height:
                    pygame.draw.rect(self.screen, color, rect)

        car_screen_x = self.car.x - camera_x
        car_screen_y = self.car.y - camera_y
        rotated_image = pygame.transform.rotate(self.car.original_image, -self.car.angle)
        car_rect = rotated_image.get_rect(center=(car_screen_x, car_screen_y))
        self.screen.blit(rotated_image, car_rect.topleft)

        pygame.display.flip()

# === Редактор трасс ===
def run_track_editor(slot_name="track_01.json"):
    TILE_SIZE = 16
    GRID_WIDTH = 50
    GRID_HEIGHT = 30
    EDITOR_WIDTH = GRID_WIDTH * TILE_SIZE
    EDITOR_HEIGHT = GRID_HEIGHT * TILE_SIZE + 60

    screen = pygame.display.set_mode((EDITOR_WIDTH, EDITOR_HEIGHT))
    pygame.display.set_caption(f"Редактор трассы — {slot_name}")
    font = pygame.font.SysFont(None, 24)
    clock = pygame.time.Clock()

    track_path = os.path.join("tracks", slot_name)
    if os.path.exists(track_path):
        with open(track_path, 'r') as f:
            data = json.load(f)
            grid = data['grid']
            start_pos = data.get('start_position', {"x": GRID_WIDTH//2, "y": GRID_HEIGHT//2, "angle": 0})
    else:
        grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        start_pos = {"x": GRID_WIDTH//2, "y": GRID_HEIGHT//2, "angle": 0}

    current_type = 1
    running = True
    drawing = False

    while running:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        tile_x = mouse_x // TILE_SIZE
        tile_y = mouse_y // TILE_SIZE

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_1: current_type = 0
                if event.key == pygame.K_2: current_type = 1
                if event.key == pygame.K_3: current_type = 2
                if event.key == pygame.K_s:
                    track_data = {
                        "name": f"Custom Track - {slot_name}",
                        "width": GRID_WIDTH,
                        "height": GRID_HEIGHT,
                        "tile_size": TILE_SIZE,
                        "grid": grid,
                        "start_position": start_pos
                    }
                    with open(track_path, "w") as f:
                        json.dump(track_data, f, indent=2)
                    print(f"✅ Сохранено: {track_path}")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
                    grid[tile_y][tile_x] = current_type
                    drawing = True
                if event.button == 3 and 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
                    start_pos["x"] = tile_x
                    start_pos["y"] = tile_y

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                drawing = False
            if event.type == pygame.MOUSEMOTION and drawing:
                if 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
                    grid[tile_y][tile_x] = current_type

        screen.fill((0, 0, 0))
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                color = SURFACE_TYPES[grid[y][x]]["color"]
                rect = pygame.Rect(x*TILE_SIZE, y*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (50,50,50), rect, 1)

        sx = start_pos["x"] * TILE_SIZE + TILE_SIZE//2
        sy = start_pos["y"] * TILE_SIZE + TILE_SIZE//2
        pygame.draw.line(screen, (255,0,0), (sx-5, sy), (sx+5, sy), 2)
        pygame.draw.line(screen, (255,0,0), (sx, sy-5), (sx, sy+5), 2)

        status = f"Слот: {slot_name} | Тип: {SURFACE_TYPES[current_type]['name']} (1/2/3) | S=сохранить | ESC=назад"
        screen.blit(font.render(status, True, (255,255,255)), (10, EDITOR_HEIGHT - 30))

        pygame.display.flip()
        clock.tick(FPS)

# === Выбор трассы ===
def track_selection_menu(fullscreen):
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((800, 600))
        w, h = 800, 600

    font = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()

    track_files = sorted([f for f in os.listdir("tracks") if f.endswith(".json")])
    if not track_files:
        track_files = ["Нет трасс!"]

    selected = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, fullscreen
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(track_files)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(track_files)
                if event.key == pygame.K_RETURN:
                    if track_files[0] != "Нет трасс!":
                        return os.path.join("tracks", track_files[selected]), fullscreen
            if event.type == pygame.MOUSEBUTTONDOWN:
                if track_files[0] != "Нет трасс!":
                    return os.path.join("tracks", track_files[selected]), fullscreen

        screen.fill((30, 30, 50))
        title = font.render("Выберите трассу", True, (255, 255, 255))
        screen.blit(title, (w//2 - title.get_width()//2, 50))

        for i, track in enumerate(track_files):
            color = (255, 255, 100) if i == selected else (200, 200, 200)
            text = font.render(track, True, color)
            screen.blit(text, (100, 150 + i * 40))

        hint = font.render("↑↓ / клик — выбрать, ENTER — играть, ESC — назад, F11 — полноэкранный", True, (180, 180, 180))
        screen.blit(hint, (w//2 - hint.get_width()//2, h - 50))

        pygame.display.flip()
        clock.tick(FPS)

# === Выбор слота ===
def slot_selection_menu(fullscreen):
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((800, 600))
        w, h = 800, 600

    font = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()

    slots = [f"track_{i:02d}.json" for i in range(1, 6)]
    selected = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, fullscreen
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(slots)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(slots)
                if event.key == pygame.K_RETURN:
                    return slots[selected], fullscreen
            if event.type == pygame.MOUSEBUTTONDOWN:
                return slots[selected], fullscreen

        screen.fill((30, 50, 30))
        title = font.render("Выберите слот для редактирования", True, (255, 255, 255))
        screen.blit(title, (w//2 - title.get_width()//2, 50))

        for i, slot in enumerate(slots):
            exists = os.path.exists(os.path.join("tracks", slot))
            color = (100, 255, 100) if exists else (200, 200, 200)
            if i == selected:
                color = (255, 255, 100)
            text = font.render(slot + (" (есть)" if exists else " (новый)"), True, color)
            screen.blit(text, (100, 150 + i * 40))

        hint = font.render("↑↓ — выбрать, ENTER — открыть, ESC — назад, F11 — полноэкранный", True, (180, 180, 180))
        screen.blit(hint, (w//2 - hint.get_width()//2, h - 50))

        pygame.display.flip()
        clock.tick(FPS)

# === Кнопка ===
class Button:
    def __init__(self, x, y, w, h, text, color=(70, 130, 180), hover_color=(100, 180, 255)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font = pygame.font.SysFont(None, 36)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2, border_radius=10)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surf, (self.rect.centerx - text_surf.get_width()//2, self.rect.centery - text_surf.get_height()//2))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

# === Главное меню ===
def main_menu():
    fullscreen = FULLSCREEN_DEFAULT
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((800, 600))
        w, h = 800, 600

    pygame.display.set_caption("Top-Down Racer — Меню")
    clock = pygame.time.Clock()
    bg_image = load_image("assets/menu_bg.png")
    bg_image = pygame.transform.scale(bg_image, (w, h))

    buttons = [
        Button(w//2 - 150, 250, 300, 60, "Выбор трассы"),
        Button(w//2 - 150, 330, 300, 60, "Редактор трасс"),
        Button(w//2 - 150, 410, 300, 60, "Выход")
    ]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    # Обновить позиции кнопок
                    for i, text in enumerate(["Выбор трассы", "Редактор трасс", "Выход"]):
                        buttons[i] = Button(w//2 - 150, 250 + i*80, 300, 60, text)

            if buttons[0].is_clicked(event):
                track_path, fullscreen = track_selection_menu(fullscreen)
                if track_path:
                    game = Game(track_path, fullscreen)
                    game.run()
                    # После игры — восстановить экран меню
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    for i, text in enumerate(["Выбор трассы", "Редактор трасс", "Выход"]):
                        buttons[i] = Button(w//2 - 150, 250 + i*80, 300, 60, text)

            if buttons[1].is_clicked(event):
                slot, fullscreen = slot_selection_menu(fullscreen)
                if slot:
                    run_track_editor(slot)
                    # Вернуться в меню
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    for i, text in enumerate(["Выбор трассы", "Редактор трасс", "Выход"]):
                        buttons[i] = Button(w//2 - 150, 250 + i*80, 300, 60, text)

            if buttons[2].is_clicked(event):
                pygame.quit()
                sys.exit()

        screen.blit(bg_image, (0, 0))
        title_font = pygame.font.SysFont(None, 72)
        title = title_font.render("RACER GAME", True, (255, 255, 255))
        screen.blit(title, (w//2 - title.get_width()//2, 100))

        for btn in buttons:
            btn.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

# === ЗАПУСК ===
if __name__ == "__main__":
    main_menu()