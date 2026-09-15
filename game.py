# -*- coding: utf-8 -*-
"""游戏状态：当前关卡、剩余箭头、失误计数、重新开始。

本文件只管"数据"，不管怎么画、也不管点击后的判定规则。
"""

from __future__ import annotations

from levels import LEVELS

DIRECTION_NAMES = {"up": "上", "down": "下", "left": "左", "right": "右"}


class GameState:
    def __init__(self, level_index=0):
        self.level_index = 0
        self.level = LEVELS[0]
        self.initial_arrows = {}
        self.arrows = {}
        self.mistakes = 0
        self.outcome = None          # None | "win" | "lose"
        self.load_level(level_index)

    # ---------------------------------------------------------- 关卡装载
    def load_level(self, index):
        index = max(0, min(index, len(LEVELS) - 1))
        self.level_index = index
        self.level = LEVELS[index]
        self.initial_arrows = {(row, col): direction
                               for row, col, direction in self.level.arrows}
        self.reset()

    def reset(self):
        """把当前关卡恢复到初始状态（"重新开始"和"重玩本关"都走这里）。"""
        self.arrows = dict(self.initial_arrows)
        self.mistakes = 0
        self.outcome = None

    # ---------------------------------------------------------- 查询
    @property
    def rows(self):
        return self.level.rows

    @property
    def cols(self):
        return self.level.cols

    @property
    def name(self):
        return self.level.name

    @property
    def total_levels(self):
        return len(LEVELS)

    @property
    def arrows_left(self):
        return len(self.arrows)

    @property
    def max_mistakes(self):
        return self.level.max_mistakes

    @property
    def mistakes_left(self):
        return max(0, self.max_mistakes - self.mistakes)

    @property
    def has_next_level(self):
        return self.level_index + 1 < len(LEVELS)

    def arrow_at(self, row, col):
        """返回该格子上的箭头方向，没有则返回 None。"""
        return self.arrows.get((row, col))
