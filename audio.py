# -*- coding: utf-8 -*-
"""音效：全部用代码合成波形，不依赖任何音频资源文件。

没有声卡、驱动不可用、mixer 初始化失败时，所有接口都降级成空操作，
游戏照常运行，不会因为音频问题崩掉。

采样率跟着 mixer 实际初始化出来的配置走，所以即使系统只接受默认配置，
生成出来的音高也是对的。

合成有两条路径：装了 numpy 就向量化生成（几十毫秒），
没装就退回逐样本的纯 Python 版本（半秒左右，只影响启动）。
"""

from __future__ import annotations

import array
import math
import random

import pygame

import settings as S

try:                                    # 可选依赖，只用来加速波形合成
    import numpy as _np
except ImportError:                     # pragma: no cover - 取决于运行环境
    _np = None

TAU = math.pi * 2

_sounds = {}
_ready = False
_muted = False
_rate = 44100
_channels = 1


# ==================================================================== 波形合成
def _pack(values):
    """numpy 的 int16 数组 → array('h')。"""
    buf = array.array("h")
    buf.frombytes(values.tobytes())
    return buf


def _sweep(duration, freq_from, freq_to, *, curve=1.0, decay=1.8,
           harmonics=(), noise=0.0, amp=0.45):
    """一段带指数衰减包络的扫频音。

    相位必须逐样本累加，不能写成 sin(2π f t)——频率在变的时候那样会算错。
    """
    total = max(1, int(_rate * duration))

    if _np is not None:
        t = _np.linspace(0.0, 1.0, total)
        freq = freq_from + (freq_to - freq_from) * _np.power(t, curve)
        phase = _np.cumsum(freq) * (TAU / _rate)
        value = _np.sin(phase)
        for multiple, weight in harmonics:
            value += _np.sin(phase * multiple) * weight
        if noise:
            value += (_np.random.rand(total) * 2.0 - 1.0) * noise
        value *= _np.power(1.0 - t, decay) * amp
        samples = _np.clip(value, -1.0, 1.0) * 32000.0
        return _pack(samples.astype(_np.int16))

    data = array.array("h")
    phase = 0.0
    for index in range(total):
        t = index / (total - 1) if total > 1 else 1.0
        freq = freq_from + (freq_to - freq_from) * (t ** curve)
        phase += TAU * freq / _rate
        value = math.sin(phase)
        for multiple, weight in harmonics:
            value += math.sin(phase * multiple) * weight
        if noise:
            value += (random.random() * 2.0 - 1.0) * noise
        data.append(int(max(-1.0, min(1.0, value * (1.0 - t) ** decay * amp)) * 32000))
    return data


def _arpeggio(notes, step, *, amp=0.36, decay=5.0, tail=0.35):
    """一串依次响起、各自衰减的音，用来做通关/失败提示音。"""
    total = max(1, int(_rate * (step * len(notes) + tail)))

    if _np is not None:
        now = _np.arange(total) / _rate
        value = _np.zeros(total)
        for order, freq in enumerate(notes):
            local = _np.maximum(now - order * step, 0.0)   # 还没响的部分 local=0 → 包络 0
            env = _np.exp(-local * decay) * _np.minimum(1.0, local * 220.0)
            value += _np.sin(TAU * freq * local) * env
            value += _np.sin(TAU * freq * 2.0 * local) * env * 0.22
        samples = _np.clip(value * amp, -1.0, 1.0) * 32000.0
        return _pack(samples.astype(_np.int16))

    data = array.array("h")
    for index in range(total):
        now = index / _rate
        value = 0.0
        for order, freq in enumerate(notes):
            local = now - order * step
            if local < 0.0:
                continue
            env = math.exp(-local * decay) * min(1.0, local * 220.0)
            value += math.sin(TAU * freq * local) * env
            value += math.sin(TAU * freq * 2.0 * local) * env * 0.22
        data.append(int(max(-1.0, min(1.0, value * amp)) * 32000))
    return data


def _to_sound(samples):
    """单声道样本 → mixer 需要的声音对象（多声道时复制到各声道）。"""
    if _channels > 1:
        if _np is not None:
            data = _np.frombuffer(samples.tobytes(), dtype=_np.int16)
            samples = _pack(_np.repeat(data, _channels))
        else:
            expanded = array.array("h")
            for value in samples:
                for _ in range(_channels):
                    expanded.append(value)
            samples = expanded
    return pygame.mixer.Sound(buffer=samples.tobytes())


def _build():
    """生成全部音效。"""
    return {
        # 箭头飞出：向上的气流声，带一点噪声
        "fly": _to_sound(_sweep(0.20, 360, 1150, curve=0.8, decay=1.7,
                                noise=0.18, amp=0.42)),
        # 被挡住：低沉的闷响
        "block": _to_sound(_sweep(0.20, 215, 78, curve=1.3, decay=2.2,
                                  harmonics=((2.0, 0.40), (3.0, 0.20)), amp=0.52)),
        # 提示：清脆的铃声
        "hint": _to_sound(_sweep(0.42, 988, 988, decay=3.4,
                                 harmonics=((2.0, 0.28), (3.01, 0.10)), amp=0.32)),
        # 撤销：短促的上滑音
        "undo": _to_sound(_sweep(0.15, 330, 780, curve=0.9, decay=2.6, amp=0.34)),
        # 选中 / 点按钮：极短的一声
        "pick": _to_sound(_sweep(0.09, 700, 1180, decay=3.0, amp=0.26)),
        # 通关：上行琶音
        "win": _to_sound(_arpeggio((523.25, 659.25, 783.99, 1046.50), 0.105,
                                   amp=0.36, decay=5.0)),
        # 失败：下行琶音
        "lose": _to_sound(_arpeggio((392.00, 329.63, 261.63), 0.17,
                                    amp=0.34, decay=3.6)),
    }


# ==================================================================== 对外接口
def init():
    """初始化音频并生成音效。失败就静默降级，返回是否可用。"""
    global _sounds, _ready, _rate, _channels
    if _ready:
        return True
    try:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    except pygame.error:
        try:                                  # 退回 pygame 默认配置再试一次
            pygame.mixer.init()
        except pygame.error:
            _ready = False
            return False

    info = pygame.mixer.get_init()
    if not info:
        _ready = False
        return False
    _rate, _, _channels = info
    try:
        _sounds = _build()
    except (pygame.error, MemoryError):
        _sounds = {}
        _ready = False
        return False

    set_volume(S.SFX_VOLUME)
    _ready = True
    return True


def set_volume(volume):
    for sound in _sounds.values():
        sound.set_volume(max(0.0, min(1.0, volume)))


def play(name):
    """播放一个音效。音频不可用或已静音时静默忽略。"""
    if not _ready or _muted:
        return
    sound = _sounds.get(name)
    if sound is not None:
        sound.play()


def toggle_mute():
    """静音开关，返回切换后是否处于静音状态。"""
    global _muted
    _muted = not _muted
    return _muted


def is_muted():
    return _muted


def is_ready():
    return _ready


def backend():
    """当前用的是哪条合成路径，便于排查环境问题。"""
    return "numpy" if _np is not None else "python"
