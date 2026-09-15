# -*- coding: utf-8 -*-
"""箭头动画：飞出棋盘、被挡住时的前冲回弹。

动画对象只负责算"沿方向移动了多少格""晃动多少""颜色闪多亮"，
像素换算交给界面层，这样动画逻辑和布局解耦。
"""

from __future__ import annotations

import math

from game import DIRECTION_VECTORS


def _ease_in_quad(t):
    return t * t


def _ease_out_cubic(t):
    return 1.0 - (1.0 - t) ** 3


class FlyOut:
    """箭头飞出棋盘的动画：越飞越快，快要出屏时淡出。"""

    kind = "fly"

    def __init__(self, cell, direction, distance, color):
        self.cell = cell
        self.direction = direction
        self.distance = distance            # 需要移动的总格数
        self.color = color
        self.duration = 0.18 + 0.05 * distance
        self.elapsed = 0.0

    @property
    def progress(self):
        return min(1.0, self.elapsed / self.duration)

    @property
    def traveled(self):
        """已经飞出的格数。"""
        return _ease_in_quad(self.progress) * self.distance

    @property
    def alpha(self):
        t = self.progress
        if t < 0.6:
            return 255
        return max(0, int(255 * (1.0 - (t - 0.6) / 0.4)))

    def update(self, dt):
        self.elapsed += dt
        return self.progress >= 1.0


class Bounce:
    """被挡住时的碰撞动画：朝阻挡方向冲一下 → 带回弹地退回 → 左右晃动 → 闪白。

    动画播完箭头仍然留在原格，只是不再计入动画列表。
    """

    kind = "bounce"

    def __init__(self, cell, direction, gap, color):
        self.cell = cell
        self.direction = direction
        self.color = color
        # 冲出去的距离：离阻挡物越远冲得越明显，但不贴到阻挡物上
        self.reach = 0.12 if not gap else max(0.12, min(0.42, (gap - 1) * 0.42))
        self.duration = 0.52
        self.elapsed = 0.0

    @property
    def progress(self):
        return min(1.0, self.elapsed / self.duration)

    @property
    def forward(self):
        """朝阻挡方向的位移（格）。"""
        t = self.progress
        if t < 0.28:                        # 前冲
            return self.reach * _ease_out_cubic(t / 0.28)
        p = (t - 0.28) / 0.72               # 阻尼振荡着退回
        return self.reach * math.cos(p * math.pi * 1.7) * (1.0 - p) ** 1.7

    @property
    def sway(self):
        """垂直于前进方向的晃动（格）。"""
        t = self.progress
        return 0.055 * math.sin(t * 30.0) * (1.0 - t) ** 1.2

    @property
    def flash(self):
        """变色强度：刚撞上时 1，随后回到 0。"""
        return max(0.0, 1.0 - self.progress / 0.45)

    def offset(self):
        """返回 (行方向位移, 列方向位移)，单位是格。"""
        dr, dc = DIRECTION_VECTORS[self.direction]
        # 晃动方向 = 前进方向旋转 90°
        return (dr * self.forward - dc * self.sway,
                dc * self.forward + dr * self.sway)

    def update(self, dt):
        self.elapsed += dt
        return self.progress >= 1.0
