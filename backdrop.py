# -*- coding: utf-8 -*-
"""动态背景：渐变底 + 大光晕 + 缓浮粒子 + 四角压暗。

静态部分只在初始化时算一次，运行时每帧只做几十次 blit。
"""

from __future__ import annotations

import math
import random

import pygame

import settings as S
import ui


class Backdrop:
    def __init__(self, size, particle_count=S.PARTICLE_COUNT, seed=20260101):
        self.size = size
        self.time = 0.0
        self._rng = random.Random(seed)
        self.static = self._build_static(size)
        # 三种大小的柔和光点，用同一个贴图重复 blit
        self._sprites = {radius: ui.radial_glow(radius * 4, (196, 218, 255),
                                               alpha=64, layers=16)
                         for radius in (1, 2, 3)}
        self.particles = [self._spawn(initial=True) for _ in range(particle_count)]

    # ---------------------------------------------------------- 构建
    def _spawn(self, initial=False):
        width, height = self.size
        return {
            "x": self._rng.uniform(0, width),
            "y": self._rng.uniform(0, height) if initial
                 else height + self._rng.uniform(0, 80),
            "radius": self._rng.choice((1, 2, 3)),
            "speed": self._rng.uniform(6.0, 22.0),
            "sway": self._rng.uniform(6.0, 24.0),
            "phase": self._rng.uniform(0, math.tau),
            "alpha": self._rng.randint(26, 76),
        }

    def _build_static(self, size):
        width, height = size
        surface = ui.vertical_gradient(size, S.COLOR_BG_TOP, S.COLOR_BG_BOTTOM).copy()
        # 顶部中央一片冷色光晕，把视线引向棋盘
        glow = ui.radial_glow(int(width * 0.60), S.COLOR_BG_GLOW, alpha=30, layers=46)
        surface.blit(glow, glow.get_rect(center=(width // 2, int(height * 0.30))))
        surface.blit(self._build_vignette(size), (0, 0))
        return surface

    @staticmethod
    def _build_vignette(size):
        """四边线性压暗，做出暗角。"""
        width, height = size
        layer = pygame.Surface(size, pygame.SRCALPHA)
        steps = 90
        for i in range(steps):
            t = i / (steps - 1)
            alpha = int(78 * (t ** 2.4))
            dy = int(height * 0.28 * t)
            dx = int(width * 0.20 * t)
            pygame.draw.line(layer, (0, 0, 0, alpha), (0, dy), (width, dy))
            pygame.draw.line(layer, (0, 0, 0, alpha), (0, height - 1 - dy), (width, height - 1 - dy))
            a2 = int(60 * (t ** 2.4))
            pygame.draw.line(layer, (0, 0, 0, a2), (dx, 0), (dx, height))
            pygame.draw.line(layer, (0, 0, 0, a2), (width - 1 - dx, 0), (width - 1 - dx, height))
        return layer

    # ---------------------------------------------------------- 运行
    def update(self, dt):
        self.time += dt
        for index, particle in enumerate(self.particles):
            particle["y"] -= particle["speed"] * dt
            if particle["y"] < -24:
                self.particles[index] = self._spawn()

    def draw(self, surface):
        surface.blit(self.static, (0, 0))
        for particle in self.particles:
            sprite = self._sprites[particle["radius"]]
            sprite.set_alpha(particle["alpha"])
            x = particle["x"] + math.sin(self.time * 0.6 + particle["phase"]) * particle["sway"]
            surface.blit(sprite, sprite.get_rect(center=(x, particle["y"])))
