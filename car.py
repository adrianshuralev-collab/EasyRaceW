# car.py
import math
import os
import pygame
from constants import SURFACE_TYPES

class Car:
    # car.py — обновлённый конструктор
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

        # Инициализируем изображение ТОЛЬКО если pygame.display уже инициализирован
        self.original_image = None
        try:
            # Проверяем, инициализирован ли дисплей
            if pygame.display.get_surface() is not None:
                self._init_image()
            else:
                self._init_dummy_image()
        except pygame.error:
            # Если pygame.display не готов — создаём заглушку
            self._init_dummy_image()

    def _init_dummy_image(self):
        """Создаём заглушку без привязки к дисплею"""
        self.original_image = pygame.Surface((100, 50), pygame.SRCALPHA)
        self.original_image.fill((255, 0, 0, 128))  # полупрозрачный красный

    def _init_image(self):
        """Загружаем реальное изображение (только при наличии дисплея)"""
        self.original_image = pygame.Surface((100, 50))
        self.original_image.fill((255, 0, 0))
        if os.path.exists('assets/car.png'):
            self.original_image = pygame.image.load('assets/car.png').convert_alpha()
            self.original_image = pygame.transform.scale(self.original_image, (100, 50))

    def update(self, keys, track):
        if keys[pygame.K_w]:
            self.speed += self.acceleration

        self.speed = max(-self.max_speed / 2, min(self.speed, self.max_speed))

        if not (keys[pygame.K_w] or keys[pygame.K_s]):
            if self.speed > 0:
                self.speed = max(0, self.speed - self.friction)
            elif self.speed < 0:
                self.speed = min(0, self.speed + self.friction)

        self.handbrake = keys[pygame.K_SPACE]

        if keys[pygame.K_s]:
            self.brake_factor *= 0.92
            self.brake_factor = max(0.0, self.brake_factor)
        else:
            self.brake_factor = 1.0

        if keys[pygame.K_a]:
            self.angle -= self.steering * (abs(self.speed) / self.max_speed)
        if keys[pygame.K_d]:
            self.angle += self.steering * (abs(self.speed) / self.max_speed)

        rad = math.radians(self.angle)
        dx = self.speed * math.cos(rad)
        dy = self.speed * math.sin(rad)

        surf = track.get_surface_info(self.x + dx, self.y + dy)
        base_traction = surf['traction']
        traction = base_traction * self.brake_factor

        if self.handbrake and traction > 0:
            traction *= 0.05

        self.x += dx * traction
        self.y += dy * traction