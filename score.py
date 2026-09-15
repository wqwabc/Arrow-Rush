# -*- coding: utf-8 -*-
"""计时与计分规则。

本关得分 = 基础分 + 速度奖励 + 失误奖励

    基础分   = SCORE_BASE + 难度分 × SCORE_PER_DIFFICULTY
               难度分是关卡自带的（见 levels.Level.difficulty），越难的关基础分越高
    速度奖励 = max(0, 目标用时 - 实际用时) × SCORE_TIME_RATE
               目标用时 = 箭头数 × SCORE_TARGET_PER_ARROW，超时只是没有奖励，不倒扣
    失误奖励 = 剩余失误次数 × SCORE_PER_SPARE_MISTAKE

规则集中在这里，改分数只需要动 settings.py 里的几个系数。
"""

from __future__ import annotations

import settings as S


def target_seconds(level):
    """这一关的目标用时（秒）。"""
    return len(level.arrows) * S.SCORE_TARGET_PER_ARROW


def base_score(difficulty):
    return S.SCORE_BASE + difficulty * S.SCORE_PER_DIFFICULTY


def time_bonus(level, seconds):
    return max(0, int((target_seconds(level) - seconds) * S.SCORE_TIME_RATE))


def mistake_bonus(mistakes_left):
    return max(0, mistakes_left) * S.SCORE_PER_SPARE_MISTAKE


def breakdown(level, seconds, mistakes_left):
    """返回 (总分, [(名称, 分数), ...])，明细给结算面板展示。"""
    difficulty = getattr(level, "difficulty", 0)
    base = base_score(difficulty)
    speed = time_bonus(level, seconds)
    spare = mistake_bonus(mistakes_left)
    return base + speed + spare, [
        ("基础分", base),
        ("速度奖励", speed),
        ("失误奖励", spare),
    ]


def format_clock(seconds):
    """把秒数格式化成 MM:SS。"""
    total = int(max(0.0, seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def format_score(value):
    """千位分隔，方便读数。"""
    return f"{int(value):,}"
