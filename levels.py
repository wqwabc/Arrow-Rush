# -*- coding: utf-8 -*-
"""关卡数据。

用 ASCII 图描述棋盘，改关卡时最直观：

    .   空格子        ^   向上箭头
    v   向下箭头      <   向左箭头      >   向右箭头

每一行对应棋盘的同一行，写在最上面的那一行就是棋盘最上面的一行。

本文件只负责"棋盘长什么样"，不含任何规则逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass

CHAR_TO_DIR = {
    "^": "up",
    "v": "down",
    "<": "left",
    ">": "right",
}

DIR_TO_CHAR = {value: key for key, value in CHAR_TO_DIR.items()}


@dataclass(frozen=True)
class Level:
    """一个关卡：名称、棋盘尺寸、允许的失误次数、初始箭头布局。"""

    name: str
    rows: int
    cols: int
    max_mistakes: int
    arrows: tuple  # ((row, col, direction), ...)


def _level(name: str, max_mistakes: int, art: str) -> Level:
    lines = art.strip("\n").split("\n")
    rows = len(lines)
    cols = max(len(line) for line in lines)
    arrows = []
    for row, line in enumerate(lines):
        for col, char in enumerate(line):
            direction = CHAR_TO_DIR.get(char)
            if direction is not None:
                arrows.append((row, col, direction))
    return Level(name=name, rows=rows, cols=cols,
                 max_mistakes=max_mistakes, arrows=tuple(arrows))


# 三关的难度递进：先只有一条依赖链，再变成两条，最后三条同时交织。
LEVELS = [
    _level("初出茅庐", 3, """
..<..
....^
v.>.^
.....
..<..
"""),
    _level("环环相扣", 4, """
...v..
.>...>
...v..
..<...
.^..>.
...v..
"""),
    _level("连锁反应", 5, """
..v...
.>.>.>
....v.
..v.v.
.<.>..
..v.v.
"""),
]
