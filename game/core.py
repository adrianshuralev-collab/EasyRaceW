import pygame
import json
import math
import os
from .constants import SURFACE_TYPES, TILE_SIZE

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
            self.clock.tick(self.track.FPS if hasattr(self.track, 'FPS') else 60)

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
