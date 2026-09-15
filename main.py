# -*- coding: utf-8 -*-
"""一箭又一箭 —— 程序入口。

运行方式：
    python main.py
"""

from __future__ import annotations

import pygame

import settings as S
from backdrop import Backdrop
from game import GameState
from scenes import GameScene, StartScene


class App:
    """管理窗口、主循环与界面切换。"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(S.WINDOW_TITLE)
        self.screen = pygame.display.set_mode((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.backdrop = Backdrop((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.state = GameState(0)
        self.scene = StartScene(self)

    # ---------------------------------------------------------- 界面切换
    def start_new_game(self):
        """从第一关开始新的一局。"""
        self.state.load_level(0)
        self.scene = GameScene(self)

    def goto_start(self):
        """回到开始界面。"""
        self.state.load_level(0)
        self.scene = StartScene(self)

    def quit(self):
        self.running = False

    # ---------------------------------------------------------- 主循环
    def run(self):
        while self.running:
            dt = self.clock.tick(S.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.scene.on_escape()
                    continue
                self.scene.handle_event(event)
            if not self.running:
                break

            self.scene.update(dt)
            self.backdrop.update(dt)
            self.backdrop.draw(self.screen)
            self.scene.draw(self.screen)
            pygame.display.flip()

        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    main()
