# test_ai.py
import pygame
from stable_baselines3 import PPO
from racer_env import RacerEnv

def main():
    model = PPO.load("models/racer_agent_100000_steps")
    env = RacerEnv(track_path="tracks/track_01.json", render_mode="human")

    obs, _ = env.reset()
    reward = 0  # ← инициализируем
    clock = pygame.time.Clock()

    try:
        while True:
            # Обработка закрытия окна
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return

            # Получаем действие от агента
            action, _ = model.predict(obs, deterministic=True)

            # Делаем шаг
            obs, reward, terminated, truncated, info = env.step(action)

            # Отладочный вывод — ПОСЛЕ step()
            print(f"Obs: x={obs[0]:.1f}, y={obs[1]:.1f}, angle={obs[2]:.1f}, "
                  f"speed={obs[3]:.2f}, surface={int(obs[4])}, reward={reward:.1f}, action={action}")

            if terminated or truncated:
                print("🔄 Эпизод завершён. Сброс.")
                obs, _ = env.reset()

            clock.tick(60)

    finally:
        env.close()
        pygame.quit()

if __name__ == "__main__":
    main()