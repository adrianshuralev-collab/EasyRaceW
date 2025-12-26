# game.py
import pygame
import sys
import math
from car import Car
from track import Track
from constants import FPS, SURFACE_TYPES

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

        self.lap_start_time = None
        self.last_lap_time = None
        self.current_lap_time = 0
        self.best_lap_time = None
        self.checkpoints_passed = set()
        self.laps_completed = 0
        self.race_started = False
        self.crossed_start_finish = False
        self.start_line_crossed = False
        self.required_checkpoints = len(self.track.checkpoints)
        self.last_tile = None

    def set_display_mode(self):
        info = pygame.display.Info()
        NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h
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

            if self.time_trial_mode and self.race_started:
                self.current_lap_time = (pygame.time.get_ticks() - self.lap_start_time) / 1000.0

            if self.time_trial_mode:
                current_tile = self.track.get_tile(self.car.x, self.car.y)

                if current_tile == 3:
                    if not self.start_line_crossed:
                        self.start_line_crossed = True
                        self.race_started = True
                        self.lap_start_time = pygame.time.get_ticks()
                        self.checkpoints_passed = set()
                    elif self.crossed_start_finish and len(self.checkpoints_passed) == self.required_checkpoints:
                        lap_time = self.current_lap_time
                        if self.best_lap_time is None or lap_time < self.best_lap_time:
                            self.best_lap_time = lap_time
                        self.last_lap_time = lap_time
                        self.laps_completed += 1
                        self.lap_start_time = pygame.time.get_ticks()
                        self.checkpoints_passed = set()

                checkpoint_id = self.track.is_checkpoint(self.car.x, self.car.y)
                if checkpoint_id is not None and checkpoint_id not in self.checkpoints_passed:
                    self.checkpoints_passed.add(checkpoint_id)

                if self.last_tile != 3 and current_tile == 3:
                    self.crossed_start_finish = True
                elif self.last_tile == 3 and current_tile != 3:
                    self.crossed_start_finish = False

                self.last_tile = current_tile

            self.car.update(keys, self.track)
            self.render()
            self.clock.tick(FPS)

    def render(self):
        camera_x = self.car.x - self.display_width // (2 * self.zoom)
        camera_y = self.car.y - self.display_height // (2 * self.zoom)

        self.screen.fill((0, 0, 0))

        for y in range(self.track.height):
            for x in range(self.track.width):
                tile_id = self.track.grid[y][x]
                color = SURFACE_TYPES[tile_id]['color']
                world_x = x * self.track.tile_size
                world_y = y * self.track.tile_size

                screen_x = (world_x - camera_x) * self.zoom
                screen_y = (world_y - camera_y) * self.zoom
                scaled_tile_size = self.track.tile_size * self.zoom

                rect = pygame.Rect(screen_x, screen_y, scaled_tile_size, scaled_tile_size)
                if -scaled_tile_size < screen_x < self.display_width and -scaled_tile_size < screen_y < self.display_height:
                    pygame.draw.rect(self.screen, color, rect)

        area_size = 2
        for cp in self.track.checkpoints:
            center_x = (cp['x'] * self.track.tile_size + self.track.tile_size // 2 - camera_x) * self.zoom
            center_y = (cp['y'] * self.track.tile_size + self.track.tile_size // 2 - camera_y) * self.zoom
            radius = int(self.track.tile_size * self.zoom * (area_size + 0.5))

            if (center_x - radius < self.display_width and center_x + radius > 0 and
                    center_y - radius < self.display_height and center_y + radius > 0):
                pygame.draw.circle(self.screen, (0, 255, 255), (center_x, center_y), radius, max(1, int(2 * self.zoom)))
                font = pygame.font.SysFont(None, int(self.track.tile_size * self.zoom * 0.5))
                text = font.render(str(cp['id']), True, (0, 0, 0))
                text_rect = text.get_rect(center=(center_x, center_y))
                self.screen.blit(text, text_rect)

        car_screen_x = (self.car.x - camera_x) * self.zoom
        car_screen_y = (self.car.y - camera_y) * self.zoom

        scaled_car = pygame.transform.scale(
            self.car.original_image,
            (int(100 * self.zoom), int(50 * self.zoom))
        )
        rotated_image = pygame.transform.rotate(scaled_car, -self.car.angle)
        car_rect = rotated_image.get_rect(center=(car_screen_x, car_screen_y))
        self.screen.blit(rotated_image, car_rect.topleft)

        if self.time_trial_mode:
            font = pygame.font.SysFont(None, 24)
            lap_text = font.render(f"Время круга: {self.current_lap_time:.2f}s", True, (255, 255, 255))
            self.screen.blit(lap_text, (10, 10))

            if self.last_lap_time:
                last_lap_text = font.render(f"Последний круг: {self.last_lap_time:.2f}s", True, (200, 200, 255))
                self.screen.blit(last_lap_text, (10, 40))

            if self.best_lap_time:
                best_lap_text = font.render(f"Лучший круг: {self.best_lap_time:.2f}s", True, (255, 255, 100))
                self.screen.blit(best_lap_text, (10, 70))

            laps_text = font.render(f"Круги: {self.laps_completed}", True, (100, 255, 100))
            self.screen.blit(laps_text, (10, 100))

            progress_text = font.render(f"Чекпоинты: {len(self.checkpoints_passed)}/{self.required_checkpoints}", True,
                                        (200, 255, 200))
            self.screen.blit(progress_text, (10, 130))

            status = "ГОНКА НАЧАТА" if self.race_started else "ПЕРЕСЕКИТЕ СТАРТ"
            status_color = (0, 255, 0) if self.race_started else (255, 255, 0)
            status_text = font.render(status, True, status_color)
            self.screen.blit(status_text, (10, 160))

        pygame.display.flip()