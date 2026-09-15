# -*- coding: utf-8 -*-
"""通关进度与成绩：记录哪些关卡已通关、每关的最高分与最快用时，并存到本地文件。

存档读写全部包了异常处理——目录只读或存档损坏时游戏照常能玩，
只是进度不会保留，不会因为存档问题崩掉。

存档格式（旧版本只有 cleared 字段，缺 records 时按空处理，保证向下兼容）：

    {"cleared": [0, 1, 2],
     "records": {"0": {"score": 1845, "seconds": 12.4}, ...}}
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
        self.records = {}       # 关卡序号 -> {"score": int, "seconds": float}

    # ---------------------------------------------------------- 读写
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            self.cleared, self.records = set(), {}
            return self
        if not isinstance(data, dict):
            self.cleared, self.records = set(), {}
            return self

        cleared = set()
        for item in data.get("cleared", []):
            if isinstance(item, int) and not isinstance(item, bool) and item >= 0:
                cleared.add(item)

        records = {}
        raw = data.get("records", {})
        if isinstance(raw, dict):
            for key, value in raw.items():
                try:
                    index = int(key)
                except (TypeError, ValueError):
                    continue
                if index < 0 or not isinstance(value, dict):
                    continue
                score = value.get("score", 0)
                seconds = value.get("seconds")
                records[index] = {
                    "score": int(score) if isinstance(score, (int, float)) else 0,
                    "seconds": (float(seconds)
                                if isinstance(seconds, (int, float)) and seconds >= 0
                                else None),
                }
        self.cleared, self.records = cleared, records
        return self

    def save(self):
        payload = {
            "cleared": sorted(self.cleared),
            "records": {str(k): {"score": v["score"], "seconds": v["seconds"]}
                        for k, v in sorted(self.records.items())},
        }
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
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

    def best_score(self, index):
        entry = self.records.get(index)
        return entry["score"] if entry else 0

    def best_seconds(self, index):
        entry = self.records.get(index)
        return entry["seconds"] if entry else None

    @property
    def total_score(self):
        return sum(entry["score"] for entry in self.records.values())

    # ---------------------------------------------------------- 记录
    def record(self, index, score, seconds):
        """写入一次通关成绩，返回 (是否刷新最高分, 是否刷新最快用时)。"""
        entry = self.records.get(index)
        if entry is None:
            entry = {"score": 0, "seconds": None}
            self.records[index] = entry

        better_score = score > entry["score"]
        better_time = entry["seconds"] is None or seconds < entry["seconds"]
        if better_score:
            entry["score"] = int(score)
        if better_time:
            entry["seconds"] = round(float(seconds), 2)

        newly_cleared = index not in self.cleared
        self.cleared.add(index)
        if better_score or better_time or newly_cleared:
            self.save()
        return better_score, better_time

    def reset(self):
        self.cleared, self.records = set(), {}
        self.save()
