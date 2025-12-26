# editor.py
import pygame
import json
import os
from constants import SURFACE_TYPES

def run_track_editor(slot_name="track_01.json"):
    pygame.init()  # editor сам инициализирует pygame
    info = pygame.display.Info()
    NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h

    MAX_GRID_WIDTH = 100
    MAX_GRID_HEIGHT = 100
    EDITOR_PIXEL_SIZE = 8
    LOGICAL_TILE_SIZE = 24

    track_path = os.path.join("tracks", slot_name)

    if os.path.exists(track_path):
        with open(track_path, 'r') as f:
            data = json.load(f)
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
        width = 100
        height = 80
        grid = [[0 for _ in range(width)] for _ in range(height)]
        start_pos = {"x": width // 2, "y": height // 2, "angle": 0}
        checkpoints = []

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
        tile_x = mouse_x // EDITOR_PIXEL_SIZE
        tile_y = mouse_y // EDITOR_PIXEL_SIZE

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if event.key == pygame.K_1: current_type = 0
                if event.key == pygame.K_2: current_type = 1
                if event.key == pygame.K_3: current_type = 2
                if event.key == pygame.K_4: current_type = 3
                if event.key == pygame.K_q: brush_size = 1
                if event.key == pygame.K_w: brush_size = 3
                if event.key == pygame.K_e: brush_size = 5
                if event.key == pygame.K_s:
                    track_data = {
                        "name": f"Custom Track - {slot_name}",
                        "width": width,
                        "height": height,
                        "tile_size": LOGICAL_TILE_SIZE,
                        "grid": grid,
                        "start_position": start_pos,
                        "checkpoints": checkpoints
                    }
                    with open(track_path, "w") as f:
                        json.dump(track_data, f, indent=2)
                    print(f"✅ Сохранено: {track_path} (tile_size={LOGICAL_TILE_SIZE})")
                if event.key == pygame.K_c:
                    if 0 <= tile_x < width and 0 <= tile_y < height:
                        exists = any(cp['x'] == tile_x and cp['y'] == tile_y for cp in checkpoints)
                        if not exists:
                            checkpoints.append({'id': checkpoint_counter, 'x': tile_x, 'y': tile_y})
                            checkpoint_counter += 1
                        else:
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

        screen.fill((0, 0, 0))
        for y in range(height):
            for x in range(width):
                screen_x = x * EDITOR_PIXEL_SIZE
                screen_y = y * EDITOR_PIXEL_SIZE
                if 0 <= screen_x < win_w and 0 <= screen_y < win_h - 60:
                    tile_id = grid[y][x]
                    color = SURFACE_TYPES[tile_id]["color"]
                    rect = pygame.Rect(screen_x, screen_y, EDITOR_PIXEL_SIZE, EDITOR_PIXEL_SIZE)
                    pygame.draw.rect(screen, color, rect)
                    pygame.draw.rect(screen, (50, 50, 50), rect, 1)

                    for cp in checkpoints:
                        if cp['x'] - 1 <= x <= cp['x'] + 1 and cp['y'] - 1 <= y <= cp['y'] + 1:
                            center_x = cp['x'] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
                            center_y = cp['y'] * EDITOR_PIXEL_SIZE + EDITOR_PIXEL_SIZE // 2
                            radius = int(EDITOR_PIXEL_SIZE * 1.5)
                            pygame.draw.circle(screen, (0, 255, 255), (center_x, center_y), radius, 2)
                            text = font.render(str(cp['id']), True, (0, 0, 0))
                            text_rect = text.get_rect(center=(center_x, center_y))
                            screen.blit(text, text_rect)

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