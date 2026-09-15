# -*- coding: utf-8 -*-
"""游戏状态与规则判定：当前关卡、剩余箭头、失误计数、路径检测、重新开始。

路径检测是这一层的核心：箭头前进方向上、到棋盘边界之间只要还有别的箭头
就飞不出去；因为是单格箭头 + 同行同列直线判定，所以沿着方向向量逐格走即可。
"""

from __future__ import annotations

from levels import LEVELS

DIRECTION_NAMES = {"up": "上", "down": "下", "left": "左", "right": "右"}

# 屏幕坐标：行号向下增大，列号向右增大。
# 「上」= 行号减小，「左」= 列号减小。
DIRECTION_VECTORS = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}


class GameState:
    def __init__(self, level_index=0):
        self.level_index = 0
        self.level = LEVELS[0]
        self.initial_arrows = {}
        self.arrows = {}
        self.mistakes = 0
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

    @property
    def lost(self):
        return self.mistakes >= self.max_mistakes

    def arrow_at(self, row, col):
        """返回该格子上的箭头方向，没有则返回 None。"""
        return self.arrows.get((row, col))

    # ---------------------------------------------------------- 路径检测
    def blocker_at(self, row, col):
        """沿箭头方向逐格前进，返回第一个挡住它的箭头位置；一路通到边界则返回 None。"""
        direction = self.arrows.get((row, col))
        if direction is None:
            return None
        dr, dc = DIRECTION_VECTORS[direction]
        r, c = row + dr, col + dc
        while 0 <= r < self.rows and 0 <= c < self.cols:
            if (r, c) in self.arrows:
                return (r, c)
            r += dr
            c += dc
        return None

    def can_leave(self, row, col):
        """前方到棋盘边界之间没有其他箭头，该箭头就能飞出棋盘并消除。"""
        return (row, col) in self.arrows and self.blocker_at(row, col) is None

    def steps_to_edge(self, row, col):
        """箭头中心走到棋盘外沿所需的格数（不含自身所在格）。"""
        dr, dc = DIRECTION_VECTORS[self.arrows[(row, col)]]
        if dr < 0:
            return row
        if dr > 0:
            return self.rows - 1 - row
        if dc < 0:
            return col
        return self.cols - 1 - col

    def steps_to_blocker(self, row, col):
        """自身中心到阻挡箭头中心相隔几格；没有阻挡返回 None。"""
        blocker = self.blocker_at(row, col)
        if blocker is None:
            return None
        return abs(blocker[0] - row) + abs(blocker[1] - col)

    # ---------------------------------------------------------- 改动棋盘
    def remove(self, row, col):
        """把一个箭头移出棋盘。"""
        return self.arrows.pop((row, col), None)

    def add_mistake(self):
        """记一次失误，返回记完之后的失误总数。"""
        self.mistakes += 1
        return self.mistakes
