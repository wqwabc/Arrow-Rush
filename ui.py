# -*- coding: utf-8 -*-
"""界面基础组件：字体、颜色工具、渐变与阴影、箭头贴图、按钮控件。

这一层不含任何游戏规则，只负责"画出来"和"接收点击"。
较贵的绘制结果（渐变、光晕、圆角面板、箭头贴图）全部做了缓存，
运行时每帧基本只剩 blit。
"""

from __future__ import annotations

import math
import os

import pygame

import audio
import settings as S

# ==================================================================== 颜色工具


def approach(current, target, speed, dt):
    """按指数速度把 current 逼近 target，用来做悬停之类的平滑过渡。

    用指数逼近而不是线性：速度与当前差距成正比，看起来自然，
    而且不依赖帧率（dt 变化时结果一致）。
    """
    if dt <= 0:
        return current
    return current + (target - current) * (1.0 - math.exp(-speed * dt))


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


# ==================================================================== 字体
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


def text_width(text, size, bold=False):
    return font(size, bold).size(text)[0]


def draw_text(surface, text, size, color, pos, anchor="center", bold=False):
    """画一行文字。anchor 支持 pygame.Rect 的各种锚点名，如 center / midleft。"""
    image = font(size, bold).render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


# ==================================================================== 渐变、形状、光晕
_gradient_cache = {}
_shape_cache = {}
_glow_cache = {}
_shadow_cache = {}


def vertical_gradient(size, top_color, bottom_color):
    """竖向渐变的不透明贴图。"""
    key = (size, top_color, bottom_color)
    if key not in _gradient_cache:
        width, height = max(1, int(size[0])), max(1, int(size[1]))
        surface = pygame.Surface((width, height))
        for y in range(height):
            t = y / max(1, height - 1)
            pygame.draw.line(surface, mix(top_color, bottom_color, t), (0, y), (width, y))
        _gradient_cache[key] = surface
    return _gradient_cache[key]


def round_rect_surface(size, radius, top_color, bottom_color=None,
                       border_color=None, border_width=0,
                       highlight=False, shade=False, recess=False):
    """带圆角、竖向渐变、可选描边和高光/暗边的贴图。

    highlight / shade 给凸起的面板用（上亮下暗）；
    recess 给内凹的凹槽用（上暗下亮），两者的光照方向相反。
    """
    key = (size, radius, top_color, bottom_color, border_color, border_width,
           highlight, shade, recess)
    if key in _shape_cache:
        return _shape_cache[key]

    width, height = max(1, int(size[0])), max(1, int(size[1]))
    radius = max(0, min(int(radius), width // 2, height // 2))
    bottom_color = top_color if bottom_color is None else bottom_color

    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), pygame.Rect(0, 0, width, height),
                     border_radius=radius)
    body = vertical_gradient((width, height), top_color, bottom_color).convert_alpha()
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    if width > radius * 2 + 4:
        edges = pygame.Surface((width, height), pygame.SRCALPHA)
        if highlight:
            pygame.draw.line(edges, (*lighten(top_color, 0.55), 74),
                             (radius, 1), (width - radius, 1), 1)
        if shade:
            pygame.draw.line(edges, (*darken(bottom_color, 0.40), 96),
                             (radius, height - 2), (width - radius, height - 2), 1)
        if recess:
            pygame.draw.line(edges, (0, 0, 0, 120),
                             (radius, 1), (width - radius, 1), 1)
            pygame.draw.line(edges, (*lighten(bottom_color, 0.30), 60),
                             (radius, height - 2), (width - radius, height - 2), 1)
        body.blit(edges, (0, 0))

    if border_color is not None and border_width > 0:
        pygame.draw.rect(body, border_color, pygame.Rect(0, 0, width, height),
                         width=border_width, border_radius=radius)

    _shape_cache[key] = body
    return body


def radial_glow(radius, color, alpha=90, layers=40):
    """柔和光晕。

    注意 pygame.draw 在 SRCALPHA 面上是"覆盖"而不是"混合"，
    所以不能靠层层叠加半透明圆来累积，必须由外向内画一圈圈
    互不重叠、透明度递增的圆环。
    """
    key = (radius, color, alpha, layers)
    if key not in _glow_cache:
        radius = max(2, int(radius))
        layers = max(2, int(layers))
        size = radius * 2
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        for i in range(layers):
            # i = 0 是最外圈（全透明），i = layers-1 是最内侧（最亮）
            outer = radius * (layers - i) / layers
            inner = radius * (layers - i - 1) / layers
            t = i / (layers - 1)
            ring_alpha = int(alpha * (t ** 1.6))
            pygame.draw.circle(surface, (*color[:3], ring_alpha), (radius, radius),
                               int(outer), max(1, int(outer - inner) + 1))
        _glow_cache[key] = surface
    return _glow_cache[key]


def draw_glow(surface, center, radius, color, alpha=90, layers=40):
    """在某个位置叠一团柔和光晕。"""
    glow = radial_glow(int(radius), color, alpha=alpha, layers=layers)
    surface.blit(glow, glow.get_rect(center=center))


def _shadow_surface(width, height, radius, spread, alpha):
    key = (width, height, radius, spread, alpha)
    if key not in _shadow_cache:
        layer_alpha = max(1, alpha // max(1, spread))
        surface = pygame.Surface((width + spread * 2, height + spread * 2), pygame.SRCALPHA)
        for i in range(spread, 0, -1):
            rect = pygame.Rect(spread - i, spread - i, width + i * 2, height + i * 2)
            pygame.draw.rect(surface, (0, 0, 0, layer_alpha), rect, border_radius=radius + i)
        _shadow_cache[key] = surface
    return _shadow_cache[key]


def draw_shadow(surface, rect, radius=16, spread=12, alpha=90, offset=(0, 5)):
    """在矩形下方叠一层渐隐阴影，让面板浮起来。"""
    shadow = _shadow_surface(rect.width, rect.height, radius, spread, alpha)
    surface.blit(shadow, (rect.x - spread + offset[0], rect.y - spread + offset[1]))


def draw_round_rect(surface, rect, color, radius=12, border_color=None, border_width=2):
    """画一个纯色圆角矩形（用于一次性、不值得缓存的场合）。"""
    rect = pygame.Rect(rect)
    radius = max(0, min(int(radius), rect.width // 2, rect.height // 2))
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border_color is not None and border_width > 0:
        pygame.draw.rect(surface, border_color, rect, width=border_width, border_radius=radius)
    return rect


# ==================================================================== 渐变文字
_text_cache = {}


def gradient_text_surface(text, size, top_color, bottom_color, bold=False):
    """把文字当作蒙版，和竖向渐变相乘，得到渐变文字。"""
    key = ("grad", text, size, top_color, bottom_color, bold)
    if key not in _text_cache:
        base = font(size, bold).render(text, True, (255, 255, 255))
        grad = vertical_gradient(base.get_size(), top_color, bottom_color).convert_alpha()
        grad.blit(base, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        _text_cache[key] = grad
    return _text_cache[key]


def draw_text_gradient(surface, text, size, top_color, bottom_color, pos,
                       anchor="center", bold=False):
    image = gradient_text_surface(text, size, top_color, bottom_color, bold)
    rect = image.get_rect()
    setattr(rect, anchor, pos)
    surface.blit(image, rect)
    return rect


# ==================================================================== 箭头
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

_arrow_cache = {}


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


def _build_arrow_sprite(direction, size, color):
    """把外发光、落地投影、渐变主体、亮边预先合成到一张贴图上。"""
    base = arrow_polygon((0, 0), size, direction)
    xs = [p[0] for p in base]
    ys = [p[1] for p in base]
    pad = size * 0.42
    width = int((max(abs(min(xs)), abs(max(xs))) + pad) * 2)
    height = int((max(abs(min(ys)), abs(max(ys))) + pad) * 2)
    cx, cy = width / 2.0, height / 2.0
    points = [(x + cx, y + cy) for x, y in base]

    sprite = pygame.Surface((width, height), pygame.SRCALPHA)

    # 1) 外发光：把略放大一圈的轮廓缩小再放大做出真实模糊，然后染成箭头颜色。
    #    直接按比例缩放多边形做不出均匀光晕（细箭杆几乎不增长），所以走模糊这条路。
    glow_mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(glow_mask, (255, 255, 255, 255),
                        arrow_polygon((cx, cy), size * 1.12, direction))
    step = (max(1, width // 7), max(1, height // 7))
    blur = pygame.transform.smoothscale(glow_mask, step)
    blur = pygame.transform.smoothscale(blur, (width, height))
    blur = pygame.transform.smoothscale(blur, step)
    blur = pygame.transform.smoothscale(blur, (width, height))
    blur.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    for _ in range(2):                  # blit 是混合语义，叠两次加深光晕
        sprite.blit(blur, (0, 0))

    # 2) 落地投影：几层偏移的暗色轮廓
    for dy, alpha in ((size * 0.12, 20), (size * 0.08, 26), (size * 0.04, 34)):
        pygame.draw.polygon(sprite, (3, 5, 12, alpha),
                            [(x, y + dy) for x, y in points])

    # 3) 主体：竖向渐变（上亮下暗）
    mask = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), points)
    body = vertical_gradient((width, height),
                             lighten(color, 0.30), darken(color, 0.24)).convert_alpha()
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    sprite.blit(body, (0, 0))

    # 4) 亮边 + 内侧暗边，做出一点厚度
    pygame.draw.polygon(sprite, (*lighten(color, 0.60), 205), points,
                        width=max(2, int(size * 0.030)))
    pygame.draw.polygon(sprite, (*darken(color, 0.45), 90),
                        arrow_polygon((cx, cy), size * 0.90, direction),
                        width=max(1, int(size * 0.018)))
    return sprite


def arrow_sprite(direction, size, color):
    key = (direction, int(round(size)), color)
    if key not in _arrow_cache:
        _arrow_cache[key] = _build_arrow_sprite(direction, size, color)
    return _arrow_cache[key]


def draw_arrow(surface, center, size, direction, color, alpha=255, scale=1.0):
    """在指定位置画一个箭头。

    scale 用于悬停放大、入场弹出等效果。这里会把 scale 量化——它是逐帧变化的，
    不量化的话贴图缓存会被无数个"差一点点"的尺寸撑爆。alpha 小于 255 时
    复制一份贴图再叠加透明度（Sprite 数量有限，开销可以接受）。
    """
    if scale != 1.0:
        scale = max(0.2, round(scale * 20) / 20)
    sprite = arrow_sprite(direction, size * scale, color)
    if alpha < 255:
        sprite = sprite.copy()
        sprite.set_alpha(max(0, alpha))
    surface.blit(sprite, sprite.get_rect(center=center))


# ==================================================================== 按钮
class Button:
    """一个矩形按钮：支持悬停、按下、禁用三种状态。"""

    def __init__(self, rect, label, on_click=None, *,
                 style="normal", font_size=22, bold=True, radius=14):
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
        self.hover_anim = 0.0           # 0→1 的悬停过渡，避免颜色硬切
        self.press_anim = 0.0           # 按下时的下沉量

    # -------------------------------------------------- 动画
    def update(self, dt):
        """每帧推进悬停/按下的过渡。"""
        self.hover_anim = approach(self.hover_anim, 1.0 if self.hovered else 0.0,
                                   S.BUTTON_LERP, dt)
        self.press_anim = approach(self.press_anim, 1.0 if self.pressed else 0.0,
                                   S.BUTTON_LERP * 1.6, dt)

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
                audio.play("pick")
                if self.on_click:
                    self.on_click()
                return True
        return False

    # -------------------------------------------------- 绘制
    def _palette(self):
        """返回 (渐变上端, 渐变下端, 描边色, 文字色, 光晕色)。"""
        if self.style == "primary":
            top, bottom = S.COLOR_BTN_PRIMARY_TOP, S.COLOR_BTN_PRIMARY_BOTTOM
            border, text = S.COLOR_BTN_PRIMARY_BORDER, (255, 255, 255)
            glow = S.COLOR_ACCENT
        elif self.style == "danger":
            top, bottom = S.COLOR_BTN_DANGER_TOP, S.COLOR_BTN_DANGER_BOTTOM
            border, text = S.COLOR_BTN_DANGER_BORDER, (255, 255, 255)
            glow = S.COLOR_DANGER
        else:
            top, bottom = S.COLOR_BTN_TOP, S.COLOR_BTN_BOTTOM
            border, text = S.COLOR_BTN_BORDER, S.COLOR_BTN_TEXT
            glow = S.COLOR_ACCENT
        return top, bottom, border, text, glow

    def draw(self, surface):
        top, bottom, border, text_color, glow = self._palette()
        rect = self.rect.copy()
        lift = self.hover_anim - self.press_anim * 1.6

        if not self.enabled:
            top = mix(top, S.COLOR_BG_BOTTOM, 0.60)
            bottom = mix(bottom, S.COLOR_BG_BOTTOM, 0.60)
            border = mix(border, S.COLOR_BG_BOTTOM, 0.60)
            text_color = S.COLOR_TEXT_FAINT
            draw_shadow(surface, rect, radius=self.radius, spread=6, alpha=60, offset=(0, 2))
        else:
            if self.hover_anim > 0.01:
                top = lighten(top, 0.16 * self.hover_anim)
                bottom = lighten(bottom, 0.16 * self.hover_anim)
                border = lighten(border, 0.20 * self.hover_anim)
                draw_glow(surface, rect.center, int(rect.width * 0.62), glow,
                          alpha=int(34 * self.hover_anim), layers=22)
            if self.press_anim > 0.01:
                top = darken(top, 0.12 * self.press_anim)
                bottom = darken(bottom, 0.12 * self.press_anim)
            rect.y += int(round(-lift))
            draw_shadow(surface, rect, radius=self.radius, spread=9,
                        alpha=int(95 - 30 * self.hover_anim), offset=(0, 4))

        body = round_rect_surface(rect.size, self.radius, top, bottom,
                                  border, 2, highlight=True)
        surface.blit(body, rect.topleft)
        draw_text(surface, self.label, self.font_size, text_color, rect.center, bold=self.bold)
