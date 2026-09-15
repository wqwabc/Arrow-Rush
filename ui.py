# -*- coding: utf-8 -*-
"""界面基础组件：字体、颜色工具、圆角矩形与阴影、箭头图形、按钮。

这一层不含任何游戏规则，只负责"画出来"和"接收点击"。
"""

from __future__ import annotations

import os

import pygame

import settings as S

# ------------------------------------------------------------------ 颜色工具


def _clamp(value, low=0, high=255):
    return max(low, min(high, int(round(value))))


def lighten(color, amount):
    """让颜色变亮，amount 取 0~1。"""
    return tuple(_clamp(c + (255 - c) * amount) for c in color[:3])


def darken(color, amount):
    """让颜色变暗，amount 取 0~1。"""
    return tuple(_clamp(c * (1 - amount)) for c in color[:3])


def mix(color_a, color_b, t):
    """按比例 t（0~1）在两个颜色之间插值。"""
    return tuple(_clamp(a + (b - a) * t) for a, b in zip(color_a[:3], color_b[:3]))


# ------------------------------------------------------------------ 字体
# 中文必须指定字体文件，pygame 默认字体画不出汉字，所以按优先级找一个可用的。
_FONT_REGULAR_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",        # 微软雅黑
    r"C:\Windows\Fonts\simhei.ttf",      # 黑体
    r"C:\Windows\Fonts\simsun.ttc",      # 宋体
    r"C:\Windows\Fonts\Deng.ttf",        # 等线
    "/System/Library/Fonts/PingFang.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
)

_FONT_BOLD_CANDIDATES = (
    r"C:\Windows\Fonts\msyhbd.ttc",      # 微软雅黑 Bold
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\Dengb.ttf",
)

_font_path_cache = {}
_font_cache = {}


def _font_path(bold):
    """返回 (字体文件路径, 该文件本身是否就是粗体)。"""
    if bold not in _font_path_cache:
        found = next((p for p in _FONT_BOLD_CANDIDATES if os.path.exists(p)), "")
        if found:
            _font_path_cache[bold] = (found, True)
        else:                               # 没有粗体文件就退回常规字体，稍后合成加粗
            fallback = next((p for p in _FONT_REGULAR_CANDIDATES if os.path.exists(p)), "")
            _font_path_cache[bold] = (fallback, False)
    return _font_path_cache[bold]


def font(size, bold=False):
    """取一个字体对象（带缓存，避免每帧重复创建）。"""
    key = (size, bold)
    if key not in _font_cache:
        path, native_bold = _font_path(bold)
        if path:
            obj = pygame.font.Font(path, size)
            if bold and not native_bold:
                obj.set_bold(True)
        else:
            obj = pygame.font.SysFont("microsoftyahei,simhei,arial", size, bold=bold)
        _font_cache[key] = obj
    return _font_cache[key]


def draw_text(surface, text, size, color, pos, anchor="center", bold=False):
    """画一行文字。anchor 支持 pygame.Rect 的各种锚点名，如 center / midleft。"""
    image = font(size, bold).render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


# ------------------------------------------------------------------ 圆角矩形与阴影
_shadow_cache = {}


def _shadow_surface(width, height, radius, spread, alpha):
    key = (width, height, radius, spread, alpha)
    if key not in _shadow_cache:
        layer_alpha = max(1, alpha // max(1, spread))
        surface = pygame.Surface((width + spread * 2, height + spread * 2), pygame.SRCALPHA)
        for i in range(spread, 0, -1):
            rect = pygame.Rect(spread - i, spread - i, width + i * 2, height + i * 2)
            pygame.draw.rect(surface, (0, 0, 0, layer_alpha), rect,
                             border_radius=radius + i)
        _shadow_cache[key] = surface
    return _shadow_cache[key]


def draw_shadow(surface, rect, radius=16, spread=12, alpha=90, offset=(0, 5)):
    """在矩形下方叠一层渐隐阴影，让面板浮起来。"""
    shadow = _shadow_surface(rect.width, rect.height, radius, spread, alpha)
    surface.blit(shadow, (rect.x - spread + offset[0], rect.y - spread + offset[1]))


def draw_round_rect(surface, rect, color, radius=12, border_color=None, border_width=2):
    """画圆角矩形（可选描边）。radius 会自动收敛，避免小矩形画崩。"""
    rect = pygame.Rect(rect)
    radius = max(0, min(int(radius), rect.width // 2, rect.height // 2))
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color is not None and border_width > 0:
        pygame.draw.rect(surface, border_color, rect,
                         width=border_width, border_radius=radius)
    return rect


# ------------------------------------------------------------------ 箭头图形
# 归一化坐标下的"向上"箭头轮廓：箭尖在上，箭杆在下。
# 换成其它方向只需把坐标绕中心旋转 90° 的整数倍。
_ARROW_SHAPE = (
    (0.00, -0.34),   # 箭尖
    (0.22, -0.06),   # 箭头右角
    (0.09, -0.06),   # 箭杆右上
    (0.09, 0.32),    # 箭杆右下
    (-0.09, 0.32),   # 箭杆左下
    (-0.09, -0.06),  # 箭杆左上
    (-0.22, -0.06),  # 箭头左角
)

_DIR_TURNS = {"up": 0, "right": 1, "down": 2, "left": 3}


def arrow_polygon(center, size, direction):
    """算出某个方向上箭头的多边形顶点。"""
    cx, cy = center
    turns = _DIR_TURNS[direction]
    points = []
    for x, y in _ARROW_SHAPE:
        for _ in range(turns):
            x, y = -y, x        # 屏幕坐标下顺时针旋转 90°
        points.append((cx + x * size, cy + y * size))
    return points


def draw_arrow(surface, center, size, direction, color, shadow=True):
    """画一个箭头：先铺一层向下的投影，再画主体，最后加一圈亮边。"""
    points = arrow_polygon(center, size, direction)
    if shadow:
        offset = max(2.0, size * 0.055)
        pygame.draw.polygon(surface, darken(color, 0.72),
                            [(x, y + offset) for x, y in points])
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, lighten(color, 0.38), points,
                        width=max(2, int(size * 0.03)))


# ------------------------------------------------------------------ 按钮
class Button:
    """一个矩形按钮：支持悬停、按下、禁用三种状态。"""

    def __init__(self, rect, label, on_click=None, *,
                 style="normal", font_size=22, bold=True, radius=12):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.style = style              # normal | primary | danger
        self.font_size = font_size
        self.bold = bold
        self.radius = radius
        self.hovered = False
        self.pressed = False
        self.enabled = True

    # -------------------------------------------------- 交互
    def handle_event(self, event):
        if not self.enabled:
            self.hovered = self.pressed = False
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self.pressed
            self.pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    # -------------------------------------------------- 绘制
    def _palette(self):
        if self.style == "primary":
            base = S.COLOR_ACCENT_DARK
            border = S.COLOR_ACCENT
            text = (255, 255, 255)
        elif self.style == "danger":
            base = S.COLOR_DANGER_DARK
            border = S.COLOR_DANGER
            text = (255, 255, 255)
        else:
            base = S.COLOR_BTN_BG
            border = S.COLOR_BTN_BORDER
            text = S.COLOR_BTN_TEXT
        if self.hovered and not self.pressed:
            base = lighten(base, 0.22)
            border = lighten(border, 0.25)
        if self.pressed:
            base = darken(base, 0.12)
        return base, border, text

    def draw(self, surface):
        base, border, text_color = self._palette()
        rect = self.rect.copy()
        if not self.enabled:
            base = mix(base, S.COLOR_BG_BOTTOM, 0.55)
            border = mix(border, S.COLOR_BG_BOTTOM, 0.55)
            text_color = S.COLOR_TEXT_FAINT
        else:
            if self.pressed:
                rect.y += 2
            elif self.hovered:
                rect.y -= 1
            draw_shadow(surface, rect, radius=self.radius, spread=8, alpha=80, offset=(0, 3))
        draw_round_rect(surface, rect, base, self.radius, border, 2)
        draw_text(surface, self.label, self.font_size, text_color, rect.center, bold=self.bold)
