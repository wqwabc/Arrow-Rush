# -*- coding: utf-8 -*-
"""箭头动画与缓动函数。

动画对象只负责算"沿方向移动了多少格""晃动多少""颜色闪多亮""缩放多少"，
像素换算交给界面层，这样动画逻辑和布局解耦。
"""

from __future__ import annotations

import math

from game import DIRECTION_VECTORS

TAU = math.pi * 2


# ==================================================================== 缓动
def ease_in_quad(t):
    """慢起快收。"""
    return t * t


def ease_out_cubic(t):
    """快起慢收。"""
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t):
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def ease_out_back(t, overshoot=1.7):
    """冲过头一点再回弹，适合入场动画。"""
    c3 = overshoot + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + overshoot * (t - 1.0) ** 2


def clamp01(value):
    return 0.0 if value < 0.0 else (1.0 if value > 1.0 else value)


# ==================================================================== 动画对象
class FlyOut:
    """箭头飞出棋盘的动画：起步带一点爆发，随后越来越快，快出屏时淡出并拉长。"""

    kind = "fly"

    def __init__(self, cell, direction, distance, color):
        self.cell = cell
        self.direction = direction
        self.distance = distance            # 需要移动的总格数
        self.color = color
        self.duration = 0.20 + 0.045 * distance
        self.elapsed = 0.0

    @property
    def progress(self):
        return min(1.0, self.elapsed / self.duration)

    @property
    def traveled(self):
        """已经飞出的格数。

        用 1.55 次方而不是平方：起步那一下不至于太黏，
        后半段仍然明显加速，看起来像被"射"出去。
        """
        return (self.progress ** 1.55) * self.distance

    @property
    def alpha(self):
        t = self.progress
        if t < 0.7:
            return 255
        return max(0, int(255 * (1.0 - (t - 0.7) / 0.3)))

    @property
    def scale(self):
        """飞行中略微放大，暗示速度感。"""
        return 1.0 + 0.10 * math.sin(self.progress * math.pi)

    def update(self, dt):
        self.elapsed += dt
        return self.progress >= 1.0


class ArrowAppear:
    """关卡开局时箭头逐个弹出的入场动画。"""

    kind = "appear"

    def __init__(self, cell, delay):
        self.cell = cell
        self.delay = delay
        self.duration = 0.30
        self.elapsed = 0.0

    @property
    def progress(self):
        if self.elapsed <= self.delay:
            return 0.0
        return min(1.0, (self.elapsed - self.delay) / self.duration)

    @property
    def scale(self):
        return 0.55 + 0.45 * ease_out_back(self.progress)

    @property
    def alpha(self):
        return int(255 * clamp01(self.progress * 1.6))

    def update(self, dt):
        self.elapsed += dt
        return self.elapsed >= self.delay + self.duration


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
            return self.reach * ease_out_cubic(t / 0.28)
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

    @property
    def scale(self):
        return 1.0 + 0.06 * self.flash

    def offset(self):
        """返回 (行方向位移, 列方向位移)，单位是格。"""
        dr, dc = DIRECTION_VECTORS[self.direction]
        # 晃动方向 = 前进方向旋转 90°
        return (dr * self.forward - dc * self.sway,
                dc * self.forward + dr * self.sway)

    def update(self, dt):
        self.elapsed += dt
        return self.progress >= 1.0
