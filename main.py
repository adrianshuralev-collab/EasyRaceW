import pygame
import json
import os
import math
import sys
from datetime import datetime

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
    2: {"name": "curb", "traction": 0.6, "color": (169, 169, 169)},
    3: {"name": "start_finish", "traction": 1.0, "color": (255, 255, 0)},  # Желтый
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
        # Чекпоинты теперь хранятся как области
        self.checkpoints = data.get('checkpoints', [])

    def get_tile(self, x, y):
        tile_x = int(x // self.tile_size)
        tile_y = int(y // self.tile_size)
        if 0 <= tile_x < self.width and 0 <= tile_y < self.height:
            return self.grid[tile_y][tile_x]
        return 2

    def get_surface_info(self, x, y):
        tile_id = self.get_tile(x, y)
        return SURFACE_TYPES.get(tile_id, SURFACE_TYPES[2])

    def is_checkpoint(self, x, y):
        """Проверяет, находится ли точка на чекпоинте, и возвращает его ID"""
        tile_x = int(x // self.tile_size)
        tile_y = int(y // self.tile_size)

        for cp in self.checkpoints:
            # Проверяем, находится ли точка в 5x5 области чекпоинта
            area_size = 2.5  # Радиус области (для 5x5 это 2)
            if cp['x'] - area_size <= tile_x <= cp['x'] + area_size and cp['y'] - area_size <= tile_y <= cp[
                'y'] + area_size:
                return cp['id']
        return None


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
    def __init__(self, track_path, fullscreen, time_trial_mode=False):
        self.fullscreen = fullscreen
        self.time_trial_mode = time_trial_mode
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

        # Переменные для таймера
        self.lap_start_time = None
        self.last_lap_time = None
        self.current_lap_time = 0
        self.best_lap_time = None
        self.checkpoints_passed = set()  # Пройденные чекпоинты
        self.laps_completed = 0
        self.race_started = False
        self.crossed_start_finish = False
        self.start_line_crossed = False  # Новое состояние для отслеживания пересечения старта
        self.required_checkpoints = len(self.track.checkpoints)  # Количество чекпоинтов на трассе
        self.last_tile = None  # Тайл под машиной в предыдущем кадре

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

            # Обновление таймера
            if self.time_trial_mode and self.race_started:
                self.current_lap_time = (pygame.time.get_ticks() - self.lap_start_time) / 1000.0

            # Проверка пересечения линий
            if self.time_trial_mode:
                current_tile = self.track.get_tile(self.car.x, self.car.y)

                # Проверяем, пересекли ли мы старт/финиш
                if current_tile == 3:  # start_finish
                    if not self.start_line_crossed:
                        # Первый раз пересекаем стартовую линию - начинаем гонку
                        self.start_line_crossed = True
                        self.race_started = True
                        self.lap_start_time = pygame.time.get_ticks()
                        self.checkpoints_passed = set()
                    elif self.crossed_start_finish and len(self.checkpoints_passed) == self.required_checkpoints:
                        # Завершаем круг (пересекаем финиш после прохождения всех чекпоинтов)
                        lap_time = self.current_lap_time
                        if self.best_lap_time is None or lap_time < self.best_lap_time:
                            self.best_lap_time = lap_time
                        self.last_lap_time = lap_time
                        self.laps_completed += 1

                        # Сброс для нового круга
                        self.lap_start_time = pygame.time.get_ticks()
                        self.checkpoints_passed = set()

                # Проверяем, пересекли ли мы чекпоинт
                checkpoint_id = self.track.is_checkpoint(self.car.x, self.car.y)
                if checkpoint_id is not None and checkpoint_id not in self.checkpoints_passed:
                    self.checkpoints_passed.add(checkpoint_id)

                # Обновляем флаг пересечения старт/финиш
                if self.last_tile != 3 and current_tile == 3:
                    self.crossed_start_finish = True
                elif self.last_tile == 3 and current_tile != 3:
                    self.crossed_start_finish = False

                self.last_tile = current_tile

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

        # Рисуем чекпоинты как области (всего один раз для каждой области)
        area_size = 2  # Радиус области (для 5x5 это 2)
        for cp in self.track.checkpoints:
            # Центр чекпоинта
            center_x = (cp['x'] * self.track.tile_size + self.track.tile_size // 2 - camera_x) * self.zoom
            center_y = (cp['y'] * self.track.tile_size + self.track.tile_size // 2 - camera_y) * self.zoom
            radius = int(self.track.tile_size * self.zoom * (area_size + 0.5))

            # Проверяем, видна ли область на экране
            if (center_x - radius < self.display_width and center_x + radius > 0 and
                    center_y - radius < self.display_height and center_y + radius > 0):
                pygame.draw.circle(self.screen, (0, 255, 255), (center_x, center_y), radius, max(1, int(2 * self.zoom)))
                # Рисуем номер чекпоинта в центре
                font = pygame.font.SysFont(None, int(self.track.tile_size * self.zoom * 0.5))
                text = font.render(str(cp['id']), True, (0, 0, 0))
                text_rect = text.get_rect(center=(center_x, center_y))
                self.screen.blit(text, text_rect)

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

        # Отрисовка информации о времени (если в режиме гонки)
        if self.time_trial_mode:
            font = pygame.font.SysFont(None, 24)

            # Текущее время круга
            lap_text = font.render(f"Время круга: {self.current_lap_time:.2f}s", True, (255, 255, 255))
            self.screen.blit(lap_text, (10, 10))

            # Последнее время круга
            if self.last_lap_time:
                last_lap_text = font.render(f"Последний круг: {self.last_lap_time:.2f}s", True, (200, 200, 255))
                self.screen.blit(last_lap_text, (10, 40))

            # Лучшее время круга
            if self.best_lap_time:
                best_lap_text = font.render(f"Лучший круг: {self.best_lap_time:.2f}s", True, (255, 255, 100))
                self.screen.blit(best_lap_text, (10, 70))

            # Количество пройденных кругов
            laps_text = font.render(f"Круги: {self.laps_completed}", True, (100, 255, 100))
            self.screen.blit(laps_text, (10, 100))

            # Прогресс чекпоинтов
            progress_text = font.render(f"Чекпоинты: {len(self.checkpoints_passed)}/{self.required_checkpoints}", True,
                                        (200, 255, 200))
            self.screen.blit(progress_text, (10, 130))

            # Статус гонки
            status = "ГОНКА НАЧАТА" if self.race_started else "ПЕРЕСЕКИТЕ СТАРТ"
            status_color = (0, 255, 0) if self.race_started else (255, 255, 0)
            status_text = font.render(status, True, status_color)
            self.screen.blit(status_text, (10, 160))

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
        start_pos = data.get('start_position', {"x": width // 2, "y": height // 2, "angle": 0})
        checkpoints = data.get('checkpoints', [])
    else:
        # Новая трасса
        width = 100
        height = 80
        grid = [[0 for _ in range(width)] for _ in range(height)]
        start_pos = {"x": width // 2, "y": height // 2, "angle": 0}
        checkpoints = []

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
    placing_checkpoint = False
    checkpoint_counter = len(checkpoints) + 1

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
                if event.key == pygame.K_1: current_type = 0  # offroad
                if event.key == pygame.K_2: current_type = 1  # asphalt
                if event.key == pygame.K_3: current_type = 2  # curb
                if event.key == pygame.K_4: current_type = 3  # start_finish
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
                        "start_position": start_pos,
                        "checkpoints": checkpoints
                    }
                    with open(track_path, "w") as f:
                        json.dump(track_data, f, indent=2)
                    print(f"✅ Сохранено: {track_path} (tile_size={LOGICAL_TILE_SIZE})")
                if event.key == pygame.K_c:  # Поставить чекпоинт
                    if 0 <= tile_x < width and 0 <= tile_y < height:
                        # Проверяем, нет ли уже чекпоинта в этой позиции
                        exists = False
                        for cp in checkpoints:
                            if cp['x'] == tile_x and cp['y'] == tile_y:
                                exists = True
                                break

                        if not exists:
                            checkpoints.append({
                                'id': checkpoint_counter,
                                'x': tile_x,
                                'y': tile_y
                            })
                            checkpoint_counter += 1
                        else:
                            # Удаляем чекпоинт если уже есть
                            checkpoints = [cp for cp in checkpoints if not (cp['x'] == tile_x and cp['y'] == tile_y)]

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
                    tile_id = grid[y][x]
                    color = SURFACE_TYPES[tile_id]["color"]
                    rect = pygame.Rect(screen_x, screen_y, EDITOR_PIXEL_SIZE, EDITOR_PIXEL_SIZE)
                    pygame.draw.rect(screen, color, rect)
                    pygame.draw.rect(screen, (50, 50, 50), rect, 1)

                    # Рисуем чекпоинты как 3x3 области
                    for cp in checkpoints:
                        if cp['x'] - 1 <= x <= cp['x'] + 1 and cp['y'] - 1 <= y <= cp['y'] + 1:
                            # Рисуем кольцо вокруг чекпоинта
                            center_x = cp['x'] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
                            center_y = cp['y'] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
                            radius = int(EDITOR_PIXEL_SIZE * 1.5)
                            pygame.draw.circle(screen, (0, 255, 255), (center_x, center_y), radius, 2)
                            # Рисуем номер чекпоинта в центре
                            text = font.render(str(cp['id']), True, (0, 0, 0))
                            text_rect = text.get_rect(center=(center_x, center_y))
                            screen.blit(text, text_rect)

        # Стартовая позиция (отображается в редакторе)
        sx = start_pos["x"] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
        sy = start_pos["y"] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
        if 0 <= sx < win_w and 0 <= sy < win_h - 60:
            pygame.draw.line(screen, (255, 0, 0), (sx - 3, sy), (sx + 3, sy), 2)
            pygame.draw.line(screen, (255, 0, 0), (sx, sy - 3), (sx, sy + 3), 2)

        status = (
            f"Слот: {slot_name} | {width}x{height} | "
            f"Тип: {SURFACE_TYPES[current_type]['name']} (1/2/3/4) | "
            f"Кисть: {brush_size}x{brush_size} (Q/W/E) | S=сохранить | "
            f"C=чекпоинт | "
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
        screen.blit(text_surf,
                    (self.rect.centerx - text_surf.get_width() // 2, self.rect.centery - text_surf.get_height() // 2))

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
                    return None, fullscreen, False  # Вернуться в меню
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
                        # Спрашиваем режим игры
                        mode_selected = game_mode_selection(screen, w, h, font)
                        if mode_selected is not None:
                            return os.path.join("tracks", track_files[selected]), fullscreen, mode_selected
            if event.type == pygame.MOUSEBUTTONDOWN:
                if track_files[0] != "Нет трасс!":
                    # Спрашиваем режим игры
                    mode_selected = game_mode_selection(screen, w, h, font)
                    if mode_selected is not None:
                        return os.path.join("tracks", track_files[selected]), fullscreen, mode_selected

        screen.fill((30, 30, 50))
        title = font.render("Выберите трассу", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 50))
        for i, track in enumerate(track_files):
            color = (255, 255, 100) if i == selected else (200, 200, 200)
            text = font.render(track, True, color)
            screen.blit(text, (100, 150 + i * 40))
        hint = font.render("↑↓ / клик — выбрать, ENTER — играть, ESC — назад, F11 — полноэкранный", True,
                           (180, 180, 180))
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 50))
        pygame.display.flip()
        clock.tick(FPS)


def game_mode_selection(screen, w, h, font):
    """Выбор режима игры: свободный или с временем"""
    modes = ["Свободный режим", "Режим с временем"]
    selected = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(modes)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(modes)
                if event.key == pygame.K_RETURN:
                    return selected == 1  # True для режима с временем
                if event.key == pygame.K_ESCAPE:
                    return None  # Вернуться к выбору трассы
            if event.type == pygame.MOUSEBUTTONDOWN:
                return selected == 1

        screen.fill((30, 30, 50))
        title = font.render("Выберите режим", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 50))

        for i, mode in enumerate(modes):
            color = (255, 255, 100) if i == selected else (200, 200, 200)
            text = font.render(mode, True, color)
            screen.blit(text, (w // 2 - text.get_width() // 2, 150 + i * 40))

        hint = font.render("↑↓ / клик — выбрать, ENTER — начать, ESC — назад", True, (180, 180, 180))
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 50))
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)


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
        screen.blit(title, (w // 2 - title.get_width() // 2, 50))
        for i, slot in enumerate(slots):
            exists = os.path.exists(os.path.join("tracks", slot))
            color = (100, 255, 100) if exists else (200, 200, 200)
            if i == selected:
                color = (255, 255, 100)
            text = font.render(slot + (" (есть)" if exists else ""), True, color)
            screen.blit(text, (100, 150 + i * 40))
        hint = font.render("↑↓ — выбрать, ENTER — открыть, ESC — назад, F11 — полноэкранный", True, (180, 180, 180))
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 50))
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
        Button(w // 2 - 150, 250, 300, 60, "Выбор трассы"),
        Button(w // 2 - 150, 330, 300, 60, "Редактор трасс"),
        Button(w // 2 - 150, 410, 300, 60, "Выход")
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
                        buttons[i] = Button(w // 2 - 150, 250 + i * 80, 300, 60, text)

            if buttons[0].is_clicked(event):
                track_path, fullscreen, time_trial_mode = track_selection_menu(fullscreen)
                if track_path:
                    game = Game(track_path, fullscreen, time_trial_mode)
                    game.run()
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    for i, text in enumerate(["Выбор трассы", "Редактор трасс", "Выход"]):
                        buttons[i] = Button(w // 2 - 150, 250 + i * 80, 300, 60, text)

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
                        buttons[i] = Button(w // 2 - 150, 250 + i * 80, 300, 60, text)

            if buttons[2].is_clicked(event):
                pygame.quit()
                sys.exit()

        screen.blit(bg_image, (0, 0))
        title_font = pygame.font.SysFont(None, 72)
        title = title_font.render("RACER GAME", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 100))
        for btn in buttons:
            btn.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


# === ЗАПУСК ===
if __name__ == "__main__":
    main_menu()
