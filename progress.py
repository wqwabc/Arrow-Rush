# -*- coding: utf-8 -*-
"""通关进度：记录哪些关卡已经通关，并存到本地文件。

存档读写全部包了异常处理——目录只读或存档损坏时游戏照常能玩，
只是进度不会保留，不会因为存档问题崩掉。
"""

from __future__ import annotations

import json
import os

SAVE_NAME = "progress.json"


def _default_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_NAME)


class Progress:
    def __init__(self, path=None):
        self.path = path or _default_path()
        self.cleared = set()

    # ---------------------------------------------------------- 读写
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            self.cleared = set()
            return self.cleared
        cleared = set()
        if isinstance(data, dict):
            for item in data.get("cleared", []):
                if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
                    cleared.add(item)
        self.cleared = cleared
        return self.cleared

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump({"cleared": sorted(self.cleared)}, handle, ensure_ascii=False)
        except OSError:
            pass

    # ---------------------------------------------------------- 查询
    def is_cleared(self, index):
        return index in self.cleared

    @property
    def cleared_count(self):
        return len(self.cleared)

    def is_unlocked(self, index, unlock_all=False):
        """第一关始终开放；其余关卡要前一关通关才解锁。"""
        if unlock_all or index <= 0:
            return True
        return (index - 1) in self.cleared

    def next_level_to_play(self, total):
        """返回第一个还没通关的关卡；全部通关了就回到第 1 关。"""
        for index in range(total):
            if index not in self.cleared:
                return index
        return 0

    # ---------------------------------------------------------- 记录
    def mark_cleared(self, index):
        """标记通关，返回是否是新通关（用于决定要不要写存档）。"""
        if index in self.cleared:
            return False
        self.cleared.add(index)
        self.save()
        return True

    def reset(self):
        self.cleared = set()
        self.save()
