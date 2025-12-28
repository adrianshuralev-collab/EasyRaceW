# train_ai.py

import pygame
pygame.init()
pygame.display.set_mode((1, 1), pygame.HIDDEN)

import os
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.env_checker import check_env
from main import GymRacerEnv
import torch
torch.set_num_threads(torch.get_num_threads())
torch.set_num_threads(8)  #Количество используемых ядер процессора для обчуения

# === Настройки ===
track_path = "tracks/track_01.json" #трек на котором тренируется
model_save_dir = "./models/"
os.makedirs(model_save_dir, exist_ok=True)

# === Создание среды ===
env = GymRacerEnv(track_path)
print("Проверка среды...")
check_env(env, warn=True)
print("✅ Среда прошла проверку!")

checkpoint_callback = CheckpointCallback(
    save_freq=25_000, # раз в сколько шагов ИИ сохраняется
    save_path=model_save_dir,
    name_prefix="racer_model",
    save_replay_buffer=False,
    save_vecnormalize=False
)

# === Модель ===
model = PPO(
    "MlpPolicy",
    env,
    verbose=1,
    tensorboard_log="./logs/",
    learning_rate=3e-4,
    n_steps=4096,
    batch_size=128,
    n_epochs=10,
    gamma=0.99,
    gae_lambda=0.95,
    ent_coef=0.03,
)

# === Обучение  ===
print("🚀 Начало обучения")
model.learn(
    total_timesteps=2_000_000, #количество шагов обучения
    callback=checkpoint_callback,
    progress_bar=True,
    tb_log_name="racer_run"
)

# === Финальное сохранение ===
model.save(os.path.join(model_save_dir, "final_model"))
print("✅ Обучение завершено. Модель сохранена.")