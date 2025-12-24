import pygame
import json
import os
import math
import sys

pygame.init()

# === Настройки экрана ===
FULLSCREEN_DEFAULT = True
info = pygame.display.Info()
NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h
FPS = 60
TILE_SIZE = 24

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

# === Классы игры (Car, Track, Game) ===
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
        self.brake_factor = 1.0
        self.braking = False
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = 0
        self.max_speed = 15.0
        self.acceleration = 0.1
        self.friction = 0.1
        self.steering = 3.0
        self.handbrake = False

        self.original_image = pygame.Surface((100, 50))
        self.original_image.fill((255, 0, 0))
        if os.path.exists('assets/car.png'):
            self.original_image = pygame.image.load('assets/car.png').convert_alpha()
            self.original_image = pygame.transform.scale(self.original_image, (100, 50))

    def update(self, keys, track):
        # Управление газом
        if keys[pygame.K_w]:
            self.speed += self.acceleration

        # Ограничение скорости
        self.speed = max(-self.max_speed / 2, min(self.speed, self.max_speed))

        # Фрикцион (плавное торможение), если не нажаты W/S
        if not (keys[pygame.K_w] or keys[pygame.K_s]):
            if self.speed > 0:
                self.speed = max(0, self.speed - self.friction)
            elif self.speed < 0:
                self.speed = min(0, self.speed + self.friction)

        # Ручной тормоз (пробел)
        self.handbrake = keys[pygame.K_SPACE]

        # Плавный тормоз на S: управление brake_factor
        if keys[pygame.K_s]:
            # Постепенно снижаем сцепление (экспоненциальное затухание)
            self.brake_factor *= 0.92  # можно настроить: 0.9 = медленнее, 0.8 = быстрее
            self.brake_factor = max(0.0, self.brake_factor)
        else:
            # Мгновенно восстанавливаем сцепление при отпускании
            self.brake_factor = 1.0

        # Поворот (руль)
        if keys[pygame.K_a]:
            self.angle -= self.steering * (abs(self.speed) / self.max_speed)
        if keys[pygame.K_d]:
            self.angle += self.steering * (abs(self.speed) / self.max_speed)

        # Физика движения
        rad = math.radians(self.angle)
        dx = self.speed * math.cos(rad)
        dy = self.speed * math.sin(rad)

        # Получаем базовое сцепление от трассы
        surf = track.get_surface_info(self.x + dx, self.y + dy)
        base_traction = surf['traction']

        # Применяем тормоз (плавное снижение сцепления)
        traction = base_traction * self.brake_factor

        # Ручной тормоз дополнительно снижает сцепление (если не обнулено)
        if self.handbrake and traction > 0:
            traction *= 0.05

        self.x += dx * traction
        self.y += dy * traction
class Game:
    def __init__(self, track_path, fullscreen):
        self.fullscreen = fullscreen
        self.set_display_mode()
        self.clock = pygame.time.Clock()
        self.running = True
        self.zoom = 1.5

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
        # Камера следует за машиной
        camera_x = self.car.x - self.display_width // (2 * self.zoom)
        camera_y = self.car.y - self.display_height // (2 * self.zoom)

        self.screen.fill((0, 0, 0))

        # Рисуем трассу с учётом масштаба
        for y in range(self.track.height):
            for x in range(self.track.width):
                tile_id = self.track.grid[y][x]
                color = SURFACE_TYPES[tile_id]['color']
                world_x = x * self.track.tile_size
                world_y = y * self.track.tile_size

                # Преобразуем мировые координаты в экранные с учётом zoom
                screen_x = (world_x - camera_x) * self.zoom
                screen_y = (world_y - camera_y) * self.zoom
                scaled_tile_size = self.track.tile_size * self.zoom

                rect = pygame.Rect(screen_x, screen_y, scaled_tile_size, scaled_tile_size)
                # Отрисовываем только то, что видно (с небольшим запасом)
                if -scaled_tile_size < screen_x < self.display_width and -scaled_tile_size < screen_y < self.display_height:
                    pygame.draw.rect(self.screen, color, rect)

        # Рисуем машину
        car_screen_x = (self.car.x - camera_x) * self.zoom
        car_screen_y = (self.car.y - camera_y) * self.zoom

        # Масштабируем изображение машины (опционально, для соответствия)
        scaled_car = pygame.transform.scale(
            self.car.original_image,
            (int(100 * self.zoom), int(50 * self.zoom))
        )
        rotated_image = pygame.transform.rotate(scaled_car, -self.car.angle)
        car_rect = rotated_image.get_rect(center=(car_screen_x, car_screen_y))
        self.screen.blit(rotated_image, car_rect.topleft)

        pygame.display.flip()

# === РЕДАКТОР ТРЕСС ===
def run_track_editor(slot_name="track_01.json"):
    MAX_GRID_WIDTH = 100
    MAX_GRID_HEIGHT = 100

    # 🔹 ВИЗУАЛЬНЫЙ размер тайла в редакторе (только для отрисовки и ввода!)
    EDITOR_PIXEL_SIZE = 8

    # 🔹 ЛОГИЧЕСКИЙ размер тайла (будет сохранён в файл и использован в игре)
    LOGICAL_TILE_SIZE = 24

    track_path = os.path.join("tracks", slot_name)

    # Загрузка существующей трассы (если есть)
    if os.path.exists(track_path):
        with open(track_path, 'r') as f:
            data = json.load(f)
        # ВСЕГДА используем LOGICAL_TILE_SIZE при загрузке!
        # Но сетка и размеры остаются те же
        width = min(data['width'], MAX_GRID_WIDTH)
        height = min(data['height'], MAX_GRID_HEIGHT)
        grid = data['grid']
        if len(grid) != height or len(grid[0]) != width:
            new_grid = [[0 for _ in range(width)] for _ in range(height)]
            for y in range(min(len(grid), height)):
                for x in range(min(len(grid[0]), width)):
                    new_grid[y][x] = grid[y][x]
            grid = new_grid
        start_pos = data.get('start_position', {"x": width//2, "y": height//2, "angle": 0})
    else:
        # Новая трасса
        width = 1000
        height = 500
        grid = [[0 for _ in range(width)] for _ in range(height)]
        start_pos = {"x": width//2, "y": height//2, "angle": 0}

    # Настройка окна редактора (ограничено, но масштабируемо)
    MAX_WIN_W = min(1200, NATIVE_WIDTH)
    MAX_WIN_H = min(800, NATIVE_HEIGHT - 100)
    win_w = min(width * EDITOR_PIXEL_SIZE, MAX_WIN_W)
    win_h = min(height * EDITOR_PIXEL_SIZE, MAX_WIN_H) + 60

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(f"Редактор — {slot_name} ({width}x{height})")
    font = pygame.font.SysFont(None, 24)
    clock = pygame.time.Clock()

    current_type = 1
    brush_size = 1
    drawing = False

    def apply_brush(cx, cy, size, value):
        radius = size // 2
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                nx, ny = cx + dx, cy + dy
                if 0 <= ny < height and 0 <= nx < width:
                    grid[ny][nx] = value

    running = True
    while running:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        # 🔹 Преобразуем ПИКСЕЛИ → КООРДИНАТЫ ТАЙЛОВ (через EDITOR_PIXEL_SIZE)
        tile_x = mouse_x // EDITOR_PIXEL_SIZE
        tile_y = mouse_y // EDITOR_PIXEL_SIZE

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if event.key == pygame.K_1: current_type = 0
                if event.key == pygame.K_2: current_type = 1
                if event.key == pygame.K_3: current_type = 2
                if event.key == pygame.K_q: brush_size = 1
                if event.key == pygame.K_w: brush_size = 3
                if event.key == pygame.K_e: brush_size = 5
                if event.key == pygame.K_s:
                    # 🔹 Сохраняем с LOGICAL_TILE_SIZE!
                    track_data = {
                        "name": f"Custom Track - {slot_name}",
                        "width": width,
                        "height": height,
                        "tile_size": LOGICAL_TILE_SIZE,  # ← ВАЖНО!
                        "grid": grid,
                        "start_position": start_pos
                    }
                    with open(track_path, "w") as f:
                        json.dump(track_data, f, indent=2)
                    print(f"✅ Сохранено: {track_path} (tile_size={LOGICAL_TILE_SIZE})")

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and 0 <= tile_x < width and 0 <= tile_y < height:
                    apply_brush(tile_x, tile_y, brush_size, current_type)
                    drawing = True
                if event.button == 3 and 0 <= tile_x < width and 0 <= tile_y < height:
                    start_pos["x"] = tile_x
                    start_pos["y"] = tile_y

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                drawing = False
            if event.type == pygame.MOUSEMOTION and drawing:
                if 0 <= tile_x < width and 0 <= tile_y < height:
                    apply_brush(tile_x, tile_y, brush_size, current_type)

        # 🔹 Отрисовка: используем EDITOR_PIXEL_SIZE для размера тайлов на экране
        screen.fill((0, 0, 0))
        for y in range(height):
            for x in range(width):
                screen_x = x * EDITOR_PIXEL_SIZE
                screen_y = y * EDITOR_PIXEL_SIZE
                if 0 <= screen_x < win_w and 0 <= screen_y < win_h - 60:  # учитываем панель статуса
                    color = SURFACE_TYPES[grid[y][x]]["color"]
                    rect = pygame.Rect(screen_x, screen_y, EDITOR_PIXEL_SIZE, EDITOR_PIXEL_SIZE)
                    pygame.draw.rect(screen, color, rect)
                    pygame.draw.rect(screen, (50, 50, 50), rect, 1)

        # Стартовая позиция (отображается в редакторе)
        sx = start_pos["x"] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
        sy = start_pos["y"] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
        if 0 <= sx < win_w and 0 <= sy < win_h - 60:
            pygame.draw.line(screen, (255, 0, 0), (sx - 3, sy), (sx + 3, sy), 2)
            pygame.draw.line(screen, (255, 0, 0), (sx, sy - 3), (sx, sy + 3), 2)

        status = (
            f"Слот: {slot_name} | {width}x{height} | "
            f"Тип: {SURFACE_TYPES[current_type]['name']} (1/2/3) | "
            f"Кисть: {brush_size}x{brush_size} (Q/W/E) | S=сохранить | "
            f"Экран: {EDITOR_PIXEL_SIZE}px/тайл → Файл: {LOGICAL_TILE_SIZE}"
        )
        screen.blit(font.render(status, True, (255, 255, 255)), (10, win_h - 30))

        pygame.display.flip()
        clock.tick(60)

# === МЕНЮ ===
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
        title = font.render("Выберите слот", True, (255, 255, 255))
        screen.blit(title, (w//2 - title.get_width()//2, 50))
        for i, slot in enumerate(slots):
            exists = os.path.exists(os.path.join("tracks", slot))
            color = (100, 255, 100) if exists else (200, 200, 200)
            if i == selected:
                color = (255, 255, 100)
            text = font.render(slot + (" (есть)" if exists else ""), True, color)
            screen.blit(text, (100, 150 + i * 40))
        hint = font.render("↑↓ — выбрать, ENTER — открыть, ESC — назад, F11 — полноэкранный", True, (180, 180, 180))
        screen.blit(hint, (w//2 - hint.get_width()//2, h - 50))
        pygame.display.flip()
        clock.tick(FPS)

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
                    for i, text in enumerate(["Выбор трассы", "Редактор трасс", "Выход"]):
                        buttons[i] = Button(w//2 - 150, 250 + i*80, 300, 60, text)

            if buttons[0].is_clicked(event):
                track_path, fullscreen = track_selection_menu(fullscreen)
                if track_path:
                    game = Game(track_path, fullscreen)
                    game.run()
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
                    run_track_editor(slot)  # ← Теперь используется ОБНОВЛЁННЫЙ редактор!
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

