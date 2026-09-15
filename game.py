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


def _blocker_on(board, rows, cols, cell):
    """在给定的棋盘上，沿箭头方向找第一个挡住它的箭头。

    注意必须按"当前棋盘"逐格往前找。写成"先在满棋盘上找到第一个阻挡者、
    再看它是否还在盘上"是错的——万一那个已经被消掉了，后面的第二个阻挡者
    就被漏掉了，会误判成可以飞出。
    """
    direction = board.get(cell)
    if direction is None:
        return None
    dr, dc = DIRECTION_VECTORS[direction]
    r, c = cell[0] + dr, cell[1] + dc
    while 0 <= r < rows and 0 <= c < cols:
        if (r, c) in board:
            return (r, c)
        r += dr
        c += dc
    return None


class GameState:
    def __init__(self, level_index=0):
        self.level_index = 0
        self.level = LEVELS[0]
        self.initial_arrows = {}
        self.arrows = {}
        self.mistakes = 0
        self.elapsed = 0.0          # 本关已用时（秒）
        self.final_time = None      # 本关结束时的用时；None 表示还在计时
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
        self.elapsed = 0.0
        self.final_time = None

    # ---------------------------------------------------------- 计时
    def tick(self, dt):
        """累加用时；本关一旦结束就停表。"""
        if self.final_time is None:
            self.elapsed += dt

    def stop_clock(self):
        """停表并返回最终用时。重复调用返回同一个值。"""
        if self.final_time is None:
            self.final_time = self.elapsed
        return self.final_time

    @property
    def seconds(self):
        """界面上应该显示的用时：已结束就是最终用时，否则是当前用时。"""
        return self.final_time if self.final_time is not None else self.elapsed

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
        return _blocker_on(self.arrows, self.rows, self.cols, (row, col))

    def can_leave(self, row, col):
        """前方到棋盘边界之间没有其他箭头，该箭头就能飞出棋盘并消除。"""
        return (row, col) in self.arrows and self.blocker_at(row, col) is None

    def free_arrows(self, board=None):
        """当前所有能直接飞出棋盘的箭头。"""
        board = self.arrows if board is None else board
        return [cell for cell in board
                if _blocker_on(board, self.rows, self.cols, cell) is None]

    def hint(self):
        """挑一个当前可以消掉的箭头作为提示；没有可消的则返回 None。

        这个游戏不存在"点错就死"——箭头能飞出的性质是单调的：消掉别的箭头只会
        让路径更空，所以此刻能飞出的箭头以后一定还能飞出。因此随便挑一个都安全。
        这里优先挑"消掉之后能让最多同伴变成可飞出"的那个，提示更有用一些。
        """
        free = self.free_arrows()
        if not free:
            return None
        best, best_gain = free[0], -1
        for cell in free:
            trial = dict(self.arrows)
            del trial[cell]
            gain = len(self.free_arrows(trial))
            if gain > best_gain:
                best, best_gain = cell, gain
        return best

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

    def restore(self, cell, direction):
        """把箭头放回棋盘（撤销用）。"""
        self.arrows[cell] = direction

    def refund_mistake(self):
        """退回一次失误（撤销用）。"""
        self.mistakes = max(0, self.mistakes - 1)
        return self.mistakes

    def add_mistake(self):
        """记一次失误，返回记完之后的失误总数。"""
        self.mistakes += 1
        return self.mistakes
