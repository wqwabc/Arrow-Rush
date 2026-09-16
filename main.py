# -*- coding: utf-8 -*-
"""一箭又一箭 —— 程序入口。

运行方式：
    python main.py
"""

from __future__ import annotations

import pygame

import audio
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
        audio.init()
        pygame.display.set_caption(S.WINDOW_TITLE)
        self.screen = pygame.display.set_mode((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True
        self.fade = 1.0                  # 切界面时从黑场淡入
        self.veil = pygame.Surface((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.veil.fill((6, 8, 14))
        self.backdrop = Backdrop((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        self.progress = Progress()
        self.progress.load()
        self.session = Session()
        self.session.load()
        self.state = GameState(0)
        self.scene = StartScene(self)

    # ---------------------------------------------------------- 界面切换
    def switch_scene(self, scene):
        """换界面并重新拉一次黑场，让切换不至于硬切。"""
        self.scene = scene
        self.fade = 1.0

    def start_play(self):
        """没有存档时的「开始游戏」：从第一个还没通关的关卡打起。"""
        self.session.clear()
        self.start_level(self.progress.next_level_to_play(len(LEVELS)))

    def start_new_game(self):
        """「新游戏」：清空通关记录与成绩，从第 1 关重新开始。

        不能做成"跳到第一个未通关的关卡"——那一关往往正是存档所在的那一关，
        点下去盘面毫无变化，看起来像按钮失灵。
        """
        self.progress.reset()
        self.session.clear()
        self.start_level(0, notice="新游戏 · 已清空通关记录，从第 1 关开始")

    def restart_playthrough(self):
        """全部通关后的「再玩一遍」：保留成绩，从第 1 关重打一轮。"""
        self.session.clear()
        self.start_level(0, notice="再来一轮 · 从第 1 关开始")

    def continue_game(self):
        """读取单局存档，接着上次的进度打。"""
        payload = self.session.data
        if not payload:
            self.start_play()
            return
        self.state.load_level(min(payload["level"], len(LEVELS) - 1))
        scene = GameScene(self)
        scene.restore(payload)
        scene.show_toast(f"已读取存档 · 第 {self.state.level_index + 1} 关",
                         S.COLOR_ACCENT, 1.8)
        self.switch_scene(scene)

    def start_level(self, index, notice=None):
        """开始指定关卡（选关界面用），并立刻写一次存档。"""
        self.state.load_level(index)
        scene = GameScene(self)
        scene.save_progress()
        if notice:
            scene.show_toast(notice, S.COLOR_ACCENT, 2.0)
        self.switch_scene(scene)

    def goto_select(self):
        # 离开关卡前先落一次盘，否则最后一次操作之后流逝的时间会丢
        self.save_current()
        self.switch_scene(SelectScene(self))

    def goto_start(self):
        self.save_current()
        self.switch_scene(StartScene(self))

    def save_current(self):
        """把当前这一关的状态落盘，关窗口也不会丢。"""
        if isinstance(self.scene, GameScene):
            self.scene.save_progress()

    def quit(self):
        self.save_current()
        self.running = False

    # ---------------------------------------------------------- 主循环
    def handle_event(self, event):
        """处理单个事件。全局快捷键先拦，剩下的交给当前界面。"""
        if event.type == pygame.QUIT:
            self.save_current()
            self.running = False
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.scene.on_escape()
            return
        self.scene.handle_event(event)

    def toggle_mute(self):
        """音效开关（由各界面上的「音效」按钮调用）。

        音效本来就不可用时（没声卡 / 驱动没起来）要明说，
        否则点了按钮只会觉得"没反应"。
        """
        if not audio.is_ready():
            self.notify("音效不可用（未检测到可用音频设备）")
            return None
        muted = audio.toggle_mute()
        if not muted:
            audio.play("pick")               # 开启时给一声，能直接听出来
        self.notify("已静音（点「音效」按钮可开启）" if muted else "音效已开启")
        return muted

    def notify(self, text):
        show = getattr(self.scene, "show_notice", None)
        if show:
            show(text)

    def frame(self, dt):
        """推进并绘制一帧。"""
        self.scene.update(dt)
        self.backdrop.update(dt)
        self.backdrop.draw(self.screen)
        self.scene.draw(self.screen)
        if self.fade > 0:
            self.fade = max(0.0, self.fade - dt / S.SCENE_FADE_SECONDS)
            self.veil.set_alpha(int(255 * self.fade ** 1.4))
            self.screen.blit(self.veil, (0, 0))
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(S.FPS) / 1000.0
            for event in pygame.event.get():
                self.handle_event(event)
            if not self.running:
                break
            self.frame(dt)
        pygame.quit()


def main():
    App().run()


if __name__ == "__main__":
    main()
