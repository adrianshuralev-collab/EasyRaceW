# train_ai.py — с промежуточным сохранением
from stable_baselines3 import PPO
from racer_env import RacerEnv
from stable_baselines3.common.callbacks import CheckpointCallback
import os

# Убедимся, что папка для моделей существует
os.makedirs("models", exist_ok=True)

# Создаём среду
env = RacerEnv(track_path="tracks/track_01.json", render_mode=None)

# Создаём callback для сохранения
checkpoint_callback = CheckpointCallback(
    save_freq=50_000,           # сохранять каждые 50k шагов
    save_path="models/",        # папка
    name_prefix="racer_agent",  # имя файла: racer_agent_50000.zip и т.д.
    save_replay_buffer=False,   # не обязательно, но можно
    save_vecnormalize=False
)

# Создаём модель
model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    tensorboard_log="./racer_logs/",
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.01
)

print("🚀 Начинаю обучение с промежуточным сохранением...")
model.learn(
    total_timesteps=300_000,
    callback=checkpoint_callback,  # ← подключаем callback
    progress_bar=True
)

# Сохраняем финальную модель (опционально — последний чекпоинт уже есть)
model.save("models/racer_agent_final")
print("✅ Обучение завершено. Модель сохранена.")