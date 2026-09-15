# -*- coding: utf-8 -*-
"""单局存档：把没打完的这一关存下来，下次打开能接着玩。

和 progress.py 的分工：

    progress.json   长期成绩——哪些关通关了、每关最高分 / 最快用时
    save.json       当前这一局——打到第几关、盘面还剩哪些箭头、失误数、
                    已用时、还剩几次提示 / 撤销、以及操作历史（撤销要用）

读写全部做容错：目录只读或文件损坏时游戏照常能玩，只是不能续关。
存档为空、关卡序号非法、或盘面已经清空（说明这关打完了）都视为无效存档。
"""

from __future__ import annotations

import json
import os

from game import DIRECTION_NAMES

SAVE_NAME = "save.json"


def _default_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), SAVE_NAME)


def encode_arrows(arrows):
    """{(r, c): 方向} → {"r,c": 方向}，JSON 的键必须是字符串。"""
    return {f"{row},{col}": direction for (row, col), direction in arrows.items()}


def decode_arrows(raw):
    arrows = {}
    if not isinstance(raw, dict):
        return arrows
    for key, direction in raw.items():
        if not isinstance(key, str) or direction not in DIRECTION_NAMES:
            continue
        parts = key.split(",")
        if len(parts) != 2:
            continue
        try:
            row, col = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if row >= 0 and col >= 0:
            arrows[(row, col)] = direction
    return arrows


def encode_history(history):
    out = []
    for action in history:
        entry = {"kind": action["kind"], "cell": list(action["cell"])}
        if action["kind"] == "launch":
            entry["direction"] = action["direction"]
        out.append(entry)
    return out


def decode_history(raw):
    out = []
    if not isinstance(raw, list):
        return out
    for action in raw:
        if not isinstance(action, dict):
            continue
        cell = action.get("cell")
        if not isinstance(cell, list) or len(cell) != 2:
            continue
        try:
            cell = (int(cell[0]), int(cell[1]))
        except (TypeError, ValueError):
            continue
        kind = action.get("kind")
        if kind == "launch" and action.get("direction") in DIRECTION_NAMES:
            out.append({"kind": "launch", "cell": cell,
                        "direction": action["direction"]})
        elif kind == "block":
            out.append({"kind": "block", "cell": cell})
    return out


class Session:
    """当前这一局的存档。data 为 None 表示没有可续的存档。"""

    def __init__(self, path=None):
        self.path = path or _default_path()
        self.data = None

    @property
    def exists(self):
        return self.data is not None

    @property
    def level_index(self):
        return self.data["level"] if self.data else 0

    # ---------------------------------------------------------- 读写
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, ValueError):
            self.data = None
            return self
        self.data = self._sanitize(raw)
        return self

    @staticmethod
    def _sanitize(raw):
        """把磁盘上的原始数据整理成可信的结构；任何不对劲都当作没有存档。"""
        if not isinstance(raw, dict):
            return None
        try:
            level = int(raw.get("level", -1))
            mistakes = max(0, int(raw.get("mistakes", 0)))
            elapsed = max(0.0, float(raw.get("elapsed", 0.0)))
            hints_left = max(0, int(raw.get("hints_left", 0)))
            undos_left = max(0, int(raw.get("undos_left", 0)))
        except (TypeError, ValueError):
            return None
        arrows = decode_arrows(raw.get("arrows"))
        if level < 0 or not arrows:
            return None          # 盘面清空说明这关已经打完，或数据不可信
        return {
            "level": level,
            "arrows": arrows,
            "mistakes": mistakes,
            "elapsed": elapsed,
            "hints_left": hints_left,
            "undos_left": undos_left,
            "history": decode_history(raw.get("history")),
        }

    def save(self, *, level, arrows, mistakes, elapsed, hints_left, undos_left, history):
        payload = {
            "level": level,
            "arrows": dict(arrows),
            "mistakes": mistakes,
            "elapsed": elapsed,
            "hints_left": hints_left,
            "undos_left": undos_left,
            "history": list(history),
        }
        self.data = payload                    # 内存里保留原始类型，取用方便
        disk = dict(payload)
        disk["arrows"] = encode_arrows(payload["arrows"])
        disk["history"] = encode_history(payload["history"])
        try:
            with open(self.path, "w", encoding="utf-8") as handle:
                json.dump(disk, handle, ensure_ascii=False)
        except OSError:
            pass

    def clear(self):
        self.data = None
        try:
            os.remove(self.path)
        except OSError:
            pass
