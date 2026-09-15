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
from levels import LEVELS
from progress import Progress
from scenes import GameScene, SelectScene, StartScene
from session import Session


class App:
    """管理窗口、主循环、成绩存档、单局存档与界面切换。"""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(S.WINDOW_TITLE)
        self.screen = pygame.display.set_mode((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.backdrop = Backdrop((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.progress = Progress()
        self.progress.load()
        self.session = Session()
        self.session.load()
        self.state = GameState(0)
        self.scene = StartScene(self)

    # ---------------------------------------------------------- 界面切换
    def start_new_game(self):
        """从头开始：清掉旧存档，跳到第一个还没通关的关卡。"""
        self.session.clear()
        self.start_level(self.progress.next_level_to_play(len(LEVELS)))

    def continue_game(self):
        """读取单局存档，接着上次的进度打。"""
        payload = self.session.data
        if not payload:
            self.start_new_game()
            return
        self.state.load_level(min(payload["level"], len(LEVELS) - 1))
        scene = GameScene(self)
        scene.restore(payload)
        self.scene = scene

    def start_level(self, index):
        """开始指定关卡（选关界面用），并立刻写一次存档。"""
        self.state.load_level(index)
        self.scene = GameScene(self)
        self.scene.save_progress()

    def goto_select(self):
        self.scene = SelectScene(self)

    def goto_start(self):
        self.scene = StartScene(self)

    def save_current(self):
        """把当前这一关的状态落盘，关窗口也不会丢。"""
        if isinstance(self.scene, GameScene):
            self.scene.save_progress()

    def quit(self):
        self.save_current()
        self.running = False

    # ---------------------------------------------------------- 主循环
    def run(self):
        while self.running:
            dt = self.clock.tick(S.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_current()
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
