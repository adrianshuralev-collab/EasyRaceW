import pygame
import os

pygame.init()
info = pygame.display.Info()
NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h

# Настройки
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

FULLSCREEN_DEFAULT = True
