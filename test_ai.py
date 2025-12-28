# run_ai.py
import pygame
import sys
import numpy as np
from stable_baselines3 import PPO
from main import Track, Car, Game, SURFACE_TYPES  # используем твою Game-логику

# === Класс AI-контроллера ===
class AIAgent:
    def __init__(self, model_path, track_path):
        self.model = PPO.load(model_path)
        self.track = Track(track_path)
        start = self.track.start_pos
        self.car = Car(
            start['x'] * self.track.tile_size + self.track.tile_size // 2,
            start['y'] * self.track.tile_size + self.track.tile_size // 2,
            start.get('angle', 0)
        )

    def get_action(self):
        # Получаем состояние (точно как в RacerEnv)
        norm_speed = (self.car.speed + self.car.max_speed / 2) / (1.5 * self.car.max_speed)
        norm_speed = np.clip(norm_speed, 0.0, 1.0)

        angle_rad = np.radians(self.car.angle)
        sin_a = (np.sin(angle_rad) + 1.0) / 2.0
        cos_a = (np.cos(angle_rad) + 1.0) / 2.0

        # Лучи
        def cast_ray(angle_offset, max_distance=200):
            rad = np.radians(self.car.angle + angle_offset)
            for d in range(0, max_distance, 4):
                x = self.car.x + d * np.cos(rad)
                y = self.car.y + d * np.sin(rad)
                tile = self.track.get_tile(x, y)
                if tile == 0 or tile == 2:
                    return d / max_distance
            return 1.0

        rays = [cast_ray(a) for a in [-90, -45, 0, 45, 90]]
        obs = np.array([norm_speed, sin_a, cos_a] + rays, dtype=np.float32)

        # Предсказание
        action, _ = self.model.predict(obs, deterministic=True)
        return int(action)

    def update_car(self, action):
        keys = self.action_to_keys(action)
        self.car.update(keys, self.track)

    def action_to_keys(self, action):
        keys = {
            pygame.K_w: False,
            pygame.K_s: False,
            pygame.K_a: False,
            pygame.K_d: False,
            pygame.K_SPACE: False
        }
        if action == 0: keys[pygame.K_w] = True
        elif action == 1: keys[pygame.K_s] = True
        elif action == 2: keys[pygame.K_a] = True
        elif action == 3: keys[pygame.K_d] = True
        elif action == 4: keys[pygame.K_w] = keys[pygame.K_a] = True
        elif action == 5: keys[pygame.K_w] = keys[pygame.K_d] = True
        elif action == 6: keys[pygame.K_s] = keys[pygame.K_a] = True
        elif action == 7: keys[pygame.K_s] = keys[pygame.K_d] = True
        elif action == 8: keys[pygame.K_SPACE] = True
        return keys


# === Запуск игры с ИИ ===
def run_ai_game(track_path="tracks/track_05.json", model_path="models/racer_model_1275000_steps.zip"):
    pygame.init()
    fullscreen = False
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("AI Driving — Press ESC to exit")
    clock = pygame.time.Clock()

    agent = AIAgent(model_path, track_path)
    track = agent.track
    car = agent.car
    zoom = 1.0
    display_width, display_height = 800, 600

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        action = agent.get_action()
        agent.update_car(action)

        # === Рендеринг ===
        camera_x = car.x - display_width // (2 * zoom)
        camera_y = car.y - display_height // (2 * zoom)
        screen.fill((0, 0, 0))

        for y in range(track.height):
            for x in range(track.width):
                tile_id = track.grid[y][x]
                color = SURFACE_TYPES[tile_id]['color']
                world_x = x * track.tile_size
                world_y = y * track.tile_size
                screen_x = (world_x - camera_x) * zoom
                screen_y = (world_y - camera_y) * zoom
                scaled_tile = track.tile_size * zoom
                rect = pygame.Rect(screen_x, screen_y, scaled_tile, scaled_tile)
                if -scaled_tile < screen_x < display_width and -scaled_tile < screen_y < display_height:
                    pygame.draw.rect(screen, color, rect)

        car_screen_x = (car.x - camera_x) * zoom
        car_screen_y = (car.y - camera_y) * zoom
        scaled_car = pygame.transform.scale(
            car.original_image,
            (int(100 * zoom), int(50 * zoom))
        )
        rotated = pygame.transform.rotate(scaled_car, -car.angle)
        rect = rotated.get_rect(center=(car_screen_x, car_screen_y))
        screen.blit(rotated, rect.topleft)

        # Информация
        font = pygame.font.SysFont(None, 24)
        action_names = ["Gas", "Brake", "Left", "Right", "Gas+L", "Gas+R", "Brake+L", "Brake+R"]
        action_text = font.render(f"Action: {action_names[action]}", True, (255, 255, 255))
        screen.blit(action_text, (10, 10))

        speed_text = font.render(f"Speed: {car.speed:.1f}", True, (255, 255, 255))
        screen.blit(speed_text, (10, 40))

        tile_id = track.get_tile(car.x, car.y)
        tile_name = SURFACE_TYPES[tile_id]["name"]
        tile_text = font.render(f"Surface: {tile_name}", True, (255, 255, 255))
        screen.blit(tile_text, (10, 70))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    run_ai_game()