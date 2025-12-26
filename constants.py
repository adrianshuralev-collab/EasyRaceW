# constants.py
import os
import pygame

# === Настройки экрана (только значения, без инициализации pygame!) ===
FULLSCREEN_DEFAULT = True
FPS = 60
TILE_SIZE = 24

# === Глобальные константы ===
SURFACE_TYPES = {
    0: {"name": "offroad", "traction": 0.3, "color": (34, 139, 34)},
    1: {"name": "asphalt", "traction": 1.0, "color": (105, 105, 105)},
    2: {"name": "curb", "traction": 0.6, "color": (169, 169, 169)},
    3: {"name": "start_finish", "traction": 1.0, "color": (255, 255, 0)},
}

# Создаём директории
os.makedirs("tracks", exist_ok=True)
os.makedirs("assets", exist_ok=True)

# === Вспомогательные функции ===
def load_image(path, fallback_color=(100, 100, 100)):
    if os.path.exists(path):
        return pygame.image.load(path).convert()
    else:
        # ВНИМАНИЕ: NATIVE_WIDTH/HEIGHT доступны только после pygame.init()
        # Поэтому используем безопасный fallback
        surf = pygame.Surface((800, 600))
        surf.fill(fallback_color)
        return surf