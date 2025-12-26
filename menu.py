# menu.py
import pygame
import sys
import os
from constants import FULLSCREEN_DEFAULT, FPS
from game import Game
from editor import run_track_editor

class Button:
    def __init__(self, x, y, w, h, text, color=(70, 130, 180), hover_color=(100, 180, 255)):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font = pygame.font.SysFont(None, 36)

    def draw(self, screen):
        mouse_pos = pygame.mouse.get_pos()
        color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2, border_radius=10)
        text_surf = self.font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surf,
                    (self.rect.centerx - text_surf.get_width() // 2, self.rect.centery - text_surf.get_height() // 2))

    def is_clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

def game_mode_selection(screen, w, h, font):
    modes = ["Свободный режим", "Режим с временем"]
    selected = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(modes)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(modes)
                if event.key == pygame.K_RETURN:
                    return selected == 1
                if event.key == pygame.K_ESCAPE:
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                return selected == 1

        screen.fill((30, 30, 50))
        title = font.render("Выберите режим", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 50))
        for i, mode in enumerate(modes):
            color = (255, 255, 100) if i == selected else (200, 200, 200)
            text = font.render(mode, True, color)
            screen.blit(text, (w // 2 - text.get_width() // 2, 150 + i * 40))
        hint = font.render("↑↓ / клик — выбрать, ENTER — начать, ESC — назад", True, (180, 180, 180))
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 50))
        pygame.display.flip()
        pygame.time.Clock().tick(FPS)

def track_selection_menu(fullscreen):
    info = pygame.display.Info()
    NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h

    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((800, 600))
        w, h = 800, 600

    font = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()
    track_files = sorted([f for f in os.listdir("tracks") if f.endswith(".json")])
    if not track_files:
        track_files = ["Нет трасс!"]

    selected = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, fullscreen, False
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(track_files)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(track_files)
                if event.key == pygame.K_RETURN:
                    if track_files[0] != "Нет трасс!":
                        mode_selected = game_mode_selection(screen, w, h, font)
                        if mode_selected is not None:
                            return os.path.join("tracks", track_files[selected]), fullscreen, mode_selected
            if event.type == pygame.MOUSEBUTTONDOWN:
                if track_files[0] != "Нет трасс!":
                    mode_selected = game_mode_selection(screen, w, h, font)
                    if mode_selected is not None:
                        return os.path.join("tracks", track_files[selected]), fullscreen, mode_selected

        screen.fill((30, 30, 50))
        title = font.render("Выберите трассу", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 50))
        for i, track in enumerate(track_files):
            color = (255, 255, 100) if i == selected else (200, 200, 200)
            text = font.render(track, True, color)
            screen.blit(text, (100, 150 + i * 40))
        hint = font.render("↑↓ / клик — выбрать, ENTER — играть, ESC — назад, F11 — полноэкранный", True, (180, 180, 180))
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 50))
        pygame.display.flip()
        clock.tick(FPS)

def slot_selection_menu(fullscreen):
    info = pygame.display.Info()
    NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h

    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((800, 600))
        w, h = 800, 600

    font = pygame.font.SysFont(None, 36)
    clock = pygame.time.Clock()
    slots = [f"track_{i:02d}.json" for i in range(1, 6)]
    selected = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None, fullscreen
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(slots)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(slots)
                if event.key == pygame.K_RETURN:
                    return slots[selected], fullscreen
            if event.type == pygame.MOUSEBUTTONDOWN:
                return slots[selected], fullscreen

        screen.fill((30, 50, 30))
        title = font.render("Выберите слот", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 50))
        for i, slot in enumerate(slots):
            exists = os.path.exists(os.path.join("tracks", slot))
            color = (100, 255, 100) if exists else (200, 200, 200)
            if i == selected:
                color = (255, 255, 100)
            text = font.render(slot + (" (есть)" if exists else ""), True, color)
            screen.blit(text, (100, 150 + i * 40))
        hint = font.render("↑↓ — выбрать, ENTER — открыть, ESC — назад, F11 — полноэкранный", True, (180, 180, 180))
        screen.blit(hint, (w // 2 - hint.get_width() // 2, h - 50))
        pygame.display.flip()
        clock.tick(FPS)

def main_menu():
    pygame.init()
    info = pygame.display.Info()
    NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h

    fullscreen = FULLSCREEN_DEFAULT
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
    else:
        screen = pygame.display.set_mode((800, 600))
        w, h = 800, 600

    pygame.display.set_caption("Top-Down Racer — Меню")
    clock = pygame.time.Clock()
    from constants import load_image
    bg_image = load_image("assets/menu_bg.png")
    bg_image = pygame.transform.scale(bg_image, (w, h))

    buttons = [
        Button(w // 2 - 150, 250, 300, 60, "Выбор трассы"),
        Button(w // 2 - 150, 330, 300, 60, "Редактор трасс"),
        Button(w // 2 - 150, 410, 300, 60, "Выход")
    ]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    buttons = [
                        Button(w // 2 - 150, 250, 300, 60, "Выбор трассы"),
                        Button(w // 2 - 150, 330, 300, 60, "Редактор трасс"),
                        Button(w // 2 - 150, 410, 300, 60, "Выход")
                    ]

            if buttons[0].is_clicked(event):
                track_path, fullscreen, time_trial_mode = track_selection_menu(fullscreen)
                if track_path:
                    game = Game(track_path, fullscreen, time_trial_mode)
                    game.run()
                    # После выхода из игры — пересоздаём экран меню
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    buttons = [
                        Button(w // 2 - 150, 250, 300, 60, "Выбор трассы"),
                        Button(w // 2 - 150, 330, 300, 60, "Редактор трасс"),
                        Button(w // 2 - 150, 410, 300, 60, "Выход")
                    ]

            if buttons[1].is_clicked(event):
                slot, fullscreen = slot_selection_menu(fullscreen)
                if slot:
                    run_track_editor(slot)
                    if fullscreen:
                        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        w, h = NATIVE_WIDTH, NATIVE_HEIGHT
                    else:
                        screen = pygame.display.set_mode((800, 600))
                        w, h = 800, 600
                    bg_image = pygame.transform.scale(bg_image, (w, h))
                    buttons = [
                        Button(w // 2 - 150, 250, 300, 60, "Выбор трассы"),
                        Button(w // 2 - 150, 330, 300, 60, "Редактор трасс"),
                        Button(w // 2 - 150, 410, 300, 60, "Выход")
                    ]

            if buttons[2].is_clicked(event):
                pygame.quit()
                sys.exit()

        screen.blit(bg_image, (0, 0))
        title_font = pygame.font.SysFont(None, 72)
        title = title_font.render("RACER GAME", True, (255, 255, 255))
        screen.blit(title, (w // 2 - title.get_width() // 2, 100))
        for btn in buttons:
            btn.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)