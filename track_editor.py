import pygame
import json
import os

# === Настройки ===
TILE_SIZE = 16
GRID_WIDTH = 50
GRID_HEIGHT = 30
SCREEN_WIDTH = GRID_WIDTH * TILE_SIZE
SCREEN_HEIGHT = GRID_HEIGHT * TILE_SIZE + 50  # + панель статуса

# Типы покрытия
SURFACE_TYPES = {
    0: {"name": "offroad", "color": (34, 139, 34)},   # Трава
    1: {"name": "asphalt", "color": (105, 105, 105)}, # Асфальт
    2: {"name": "curb", "color": (169, 169, 169)}     # Бордюр
}

# Инициализация
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Track Editor - кликай! 1/2/3 = тип, S = сохранить")
font = pygame.font.SysFont(None, 24)

# Создаём пустую сетку (по умолчанию — трава)
grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

# Стартовая позиция (тайлы)
start_pos = {"x": GRID_WIDTH // 2, "y": GRID_HEIGHT // 2, "angle": 0}

# Текущий тип для рисования
current_type = 1  # по умолчанию — асфальт

running = True
drawing = False

while running:
    mouse_x, mouse_y = pygame.mouse.get_pos()
    tile_x = mouse_x // TILE_SIZE
    tile_y = mouse_y // TILE_SIZE

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Смена типа покрытия
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                current_type = 0
            elif event.key == pygame.K_2:
                current_type = 1
            elif event.key == pygame.K_3:
                current_type = 2
            elif event.key == pygame.K_s:
                # Сохранение
                track_data = {
                    "name": "Custom Track",
                    "width": GRID_WIDTH,
                    "height": GRID_HEIGHT,
                    "tile_size": TILE_SIZE,
                    "grid": grid,
                    "start_position": start_pos
                }
                os.makedirs("tracks", exist_ok=True)
                with open("tracks/track_01.json", "w") as f:
                    json.dump(track_data, f, indent=2)
                print("✅ Трасса сохранена в tracks/track_01.json")

        # Рисование
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # ЛКМ
                if 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
                    grid[tile_y][tile_x] = current_type
                    drawing = True
            elif event.button == 3:  # ПКМ — установить старт
                if 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
                    start_pos["x"] = tile_x
                    start_pos["y"] = tile_y
                    print(f"🏁 Старт установлен: ({tile_x}, {tile_y})")

        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                drawing = False

        if event.type == pygame.MOUSEMOTION and drawing:
            if 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
                grid[tile_y][tile_x] = current_type

    # Отрисовка
    screen.fill((0, 0, 0))

    # Сетка
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            tile_type = grid[y][x]
            color = SURFACE_TYPES[tile_type]["color"]
            rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (50, 50, 50), rect, 1)  # сетка

    # Стартовая позиция (красный крестик)
    sx = start_pos["x"] * TILE_SIZE + TILE_SIZE // 2
    sy = start_pos["y"] * TILE_SIZE + TILE_SIZE // 2
    pygame.draw.line(screen, (255, 0, 0), (sx - 5, sy), (sx + 5, sy), 2)
    pygame.draw.line(screen, (255, 0, 0), (sx, sy - 5), (sx, sy + 5), 2)

    # Панель статуса
    status = f"Текущий тип: {SURFACE_TYPES[current_type]['name']} (1=трава, 2=асфальт, 3=бордюр). S=сохранить. ПКМ=старт."
    text = font.render(status, True, (255, 255, 255))
    screen.blit(text, (10, SCREEN_HEIGHT - 30))

    pygame.display.flip()

pygame.quit()