# racer_env.py
import gymnasium as gym
import numpy as np
import pygame
from car import Car
from track import Track
from constants import SURFACE_TYPES

class RacerEnv(gym.Env):
    metadata = {"render_modes": ["human"], "render_fps": 60}

    def __init__(self, track_path="tracks/track_01.json", render_mode=None):
        super().__init__()
        self.track_path = track_path
        self.track = Track(track_path)
        self.render_mode = render_mode
        self.idle_steps = 0

        # Инициализируем машину в стартовой позиции
        start = self.track.start_pos
        self.car = Car(
            start['x'] * self.track.tile_size + self.track.tile_size // 2,
            start['y'] * self.track.tile_size + self.track.tile_size // 2,
            start.get('angle', 0)
        )

        # Пространство наблюдений (состояний)
        self.observation_space = gym.spaces.Box(
            low=np.array([
                0,                                    # x
                0,                                    # y
                -180,                                 # угол
                -15,                                  # скорость
                0,                                    # тип поверхности (0-3)
                0,                                    # ID следующего чекпоинта
                0.0                                   # прогресс (0.0–1.0)
            ], dtype=np.float32),
            high=np.array([
                self.track.width * self.track.tile_size,
                self.track.height * self.track.tile_size,
                180,
                15,
                3,
                max(1, len(self.track.checkpoints)),
                1.0
            ], dtype=np.float32)
        )

        # Дискретные действия (6 штук)
        self.action_space = gym.spaces.Discrete(5)

        self.checkpoints_passed = set()
        self.total_checkpoints = len(self.track.checkpoints)
        self.steps = 0
        self.max_steps = 3000  # чтобы избежать бесконечного круга
        self.lap_start_time = 0

        # Для рендеринга (если нужно)
        if self.render_mode == "human":
            pygame.init()
            self.screen = pygame.display.set_mode((800, 600))
            pygame.display.set_caption("Racer AI")
            self.clock = pygame.time.Clock()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        start = self.track.start_pos
        self.car = Car(
            start['x'] * self.track.tile_size + self.track.tile_size // 2,
            start['y'] * self.track.tile_size + self.track.tile_size // 2,
            start.get('angle', 0)
        )
        self.checkpoints_passed = set()
        self.steps = 0
        self.lap_start_time = 0
        return self._get_obs(), {}

    def _get_obs(self):
        x, y = self.car.x, self.car.y
        angle = self.car.angle % 360
        speed = self.car.speed
        surface_id = self.track.get_tile(x, y)
        next_cp_id = len(self.checkpoints_passed)  # ID следующего чекпоинта (0,1,2...)
        progress = len(self.checkpoints_passed) / max(1, self.total_checkpoints)
        return np.array([x, y, angle, speed, surface_id, next_cp_id, progress], dtype=np.float32)

    def step(self, action):
        self.steps += 1

        # Преобразуем дискретное действие в клавиши
        keys = [0] * 512  # pygame.K_* идёт до ~500
        if action == 0:   # Вперёд
            keys[pygame.K_w] = 1
        elif action == 1: # Влево
            keys[pygame.K_a] = 1
        elif action == 2: # Вправо
            keys[pygame.K_d] = 1
        elif action == 3: # Вперёд + влево
            keys[pygame.K_w] = keys[pygame.K_a] = 1
        elif action == 4: # Вперёд + вправо
            keys[pygame.K_w] = keys[pygame.K_d] = 1

        # Обновляем состояние машины
        self.car.update(keys, self.track)

        # Награда и флаги завершения
        reward = 0.0
        terminated = False
        truncated = False

        # Штраф за offroad
        if self.track.get_tile(self.car.x, self.car.y) == 0:  # offroad
            reward = -100.0
            terminated = True
        else:
            # Небольшая награда за скорость (только на дороге!)
            reward += self.car.speed * 0.1

        if self.track.get_tile(self.car.x, self.car.y) == 0:  # offroad
            reward = -100.0
            terminated = True
        else:
            # Штраф за отсутствие движения
            if abs(self.car.speed) < 0.1:  # почти стоит
                reward = -10.0
            else:
                # Небольшая награда за движение (опционально)
                reward = 0.1  # или даже 0.0 — штрафа за простой уже достаточно

        # Проверка чекпоинтов
        cp_id = self.track.is_checkpoint(self.car.x, self.car.y)
        if cp_id is not None and cp_id not in self.checkpoints_passed:
            self.checkpoints_passed.add(cp_id)
            reward += 10.0

        # Проверка завершения круга
        if len(self.checkpoints_passed) == self.total_checkpoints:
            # Упрощённо: считаем, что круг завершён
            reward += 200.0  # бонус за завершение
            terminated = True

        # Ограничение по шагам
        if self.steps >= self.max_steps:
            truncated = True

        # Рендеринг (если нужно)
        if self.render_mode == "human":
            self._render_frame()

        if self.track.get_tile(self.car.x, self.car.y) == 0:
            reward = -100.0
            terminated = True
        else:
            if abs(self.car.speed) < 0.1:
                self.idle_steps += 1
                if self.idle_steps > 2:  # первые 2 шага не штрафуем
                    reward = -10.0
                else:
                    reward = 0.0
            else:
                self.idle_steps = 0
                reward = 0.1

        return self._get_obs(), reward, terminated, truncated, {}

    def _render_frame(self):
        self.screen.fill((0, 0, 0))
        # Рисуем трассу
        for y in range(self.track.height):
            for x in range(self.track.width):
                tile_id = self.track.grid[y][x]
                color = SURFACE_TYPES[tile_id]["color"]
                rect = pygame.Rect(x * self.track.tile_size // 3, y * self.track.tile_size // 3, 8, 8)
                pygame.draw.rect(self.screen, color, rect)
        # Рисуем машину (просто точку)
        car_x = int(self.car.x / 3)
        car_y = int(self.car.y / 3)
        pygame.draw.circle(self.screen, (255, 0, 0), (car_x, car_y), 5)
        pygame.display.flip()
        self.clock.tick(60)

    def render(self):
        if self.render_mode == "human":
            self._render_frame()

    def close(self):
        if hasattr(self, 'screen'):
            pygame.quit()