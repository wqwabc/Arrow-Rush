# -*- coding: utf-8 -*-
"""三个界面：开始界面、游戏界面，以及叠在游戏界面上的通关/失败结算浮层。

界面的职责只有"显示"和"把点击翻译成动作"，不含消除判定规则。
"""

from __future__ import annotations

import math

import pygame

import settings as S
import ui
from game import DIRECTION_NAMES
from ui import Button

# 顶部信息栏做成一张浮起的卡片，而不是通栏色块
TOP_BAR_CARD = pygame.Rect(20, 12, S.WINDOW_WIDTH - 40, 72)

# 开始界面说明行的图标顺序
RULE_DIRECTIONS = ("up", "down", "left", "right")

RULE_LINES = (
    "点击棋盘上的箭头，它会沿着自己的方向前进。",
    "前方到棋盘边界没有其他箭头 → 箭头飞出棋盘并消失。",
    "前方有其他箭头阻挡 → 无法消除，并消耗一次失误机会。",
    "清空全部箭头进入下一关；失误次数耗尽则本关失败。",
)


# ==================================================================== 棋盘布局
def board_layout(rows, cols):
    """按关卡行列数算出棋盘外框、格子区域与格子边长（自动居中、自适应）。"""
    area = pygame.Rect(
        S.BOARD_MARGIN_X,
        S.TOP_BAR_HEIGHT + S.BOARD_MARGIN_TOP,
        S.WINDOW_WIDTH - 2 * S.BOARD_MARGIN_X,
        S.WINDOW_HEIGHT - S.TOP_BAR_HEIGHT - S.BOARD_MARGIN_TOP
        - S.BOTTOM_BAR_HEIGHT - S.BOARD_MARGIN_BOTTOM,
    )
    pad = S.BOARD_PADDING
    cell = min((area.width - 2 * pad) / cols, (area.height - 2 * pad) / rows)
    panel = pygame.Rect(0, 0, round(cell * cols) + 2 * pad, round(cell * rows) + 2 * pad)
    panel.center = area.center
    grid = pygame.Rect(panel.x + pad, panel.y + pad,
                       panel.width - 2 * pad, panel.height - 2 * pad)
    return panel, grid, cell


def cell_rect(grid, cell, row, col):
    """第 row 行第 col 列格子的矩形（用两次 round 保证相邻格子不重叠、不留缝）。"""
    left = round(grid.x + col * cell)
    top = round(grid.y + row * cell)
    right = round(grid.x + (col + 1) * cell)
    bottom = round(grid.y + (row + 1) * cell)
    return pygame.Rect(left, top, right - left, bottom - top)


def cell_at(pos, grid, cell, rows, cols):
    """把鼠标坐标换算成格子坐标，落在棋盘外返回 None。"""
    if not grid.collidepoint(pos):
        return None
    col = int((pos[0] - grid.x) // cell)
    row = int((pos[1] - grid.y) // cell)
    if 0 <= row < rows and 0 <= col < cols:
        return row, col
    return None


def draw_panel(surface, rect, radius=20, top_color=None, bottom_color=None,
               border_color=None, border_width=2, shadow_alpha=100, shadow_offset=(0, 8)):
    """画一张浮起的面板：阴影 + 渐变底 + 描边 + 顶部高光。"""
    ui.draw_shadow(surface, rect, radius=radius, spread=max(10, radius // 2),
                   alpha=shadow_alpha, offset=shadow_offset)
    body = ui.round_rect_surface(
        rect.size, radius,
        S.COLOR_PANEL_TOP if top_color is None else top_color,
        S.COLOR_PANEL_BOTTOM if bottom_color is None else bottom_color,
        S.COLOR_PANEL_BORDER if border_color is None else border_color,
        border_width, highlight=True)
    surface.blit(body, rect.topleft)


# ==================================================================== 开始界面
class StartScene:
    def __init__(self, app):
        self.app = app
        self.time = 0.0
        cx = S.WINDOW_WIDTH // 2
        self.buttons = [
            Button((cx - 150, 556, 300, 66), "开 始 游 戏", self.app.start_new_game,
                   style="primary", font_size=27),
            Button((cx - 95, 640, 190, 50), "退出游戏", self.app.quit, font_size=20),
        ]

    def on_escape(self):
        self.app.quit()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt):
        self.time += dt

    def draw(self, surface):
        cx = S.WINDOW_WIDTH // 2

        # 标题背后的柔光
        ui.draw_glow(surface, (cx, 240), 300, S.COLOR_ACCENT, alpha=34, layers=34)

        # 四个方向的装饰箭头，错开相位上下浮动
        for index, direction in enumerate(RULE_DIRECTIONS):
            x = cx + (index - 1.5) * 110
            bob = math.sin(self.time * 1.8 + index * 0.8) * 7
            ui.draw_arrow(surface, (x, 120 + bob), 48, direction, S.ARROW_COLORS[direction])

        ui.draw_text_gradient(surface, "一箭又一箭", 84,
                              S.COLOR_TITLE_TOP, S.COLOR_TITLE_BOTTOM,
                              (cx, 236), bold=True)
        ui.draw_text(surface, "Arrow Escape", 21, S.COLOR_TEXT_DIM, (cx, 296))
        pygame.draw.line(surface, ui.mix(S.COLOR_ACCENT, S.COLOR_BG_BOTTOM, 0.62),
                         (cx - 150, 318), (cx + 150, 318), 2)

        # 玩法说明面板
        panel = pygame.Rect(0, 0, 740, 206)
        panel.center = (cx, 433)
        draw_panel(surface, panel)
        ui.draw_round_rect(surface, pygame.Rect(panel.x + 22, panel.y + 34, 4, 24),
                           S.COLOR_ACCENT, 2)
        ui.draw_text(surface, "玩 法 说 明", 20, S.COLOR_ACCENT,
                     (panel.x + 38, panel.y + 46), anchor="midleft", bold=True)

        for index, line in enumerate(RULE_LINES):
            y = panel.y + 90 + index * 30
            direction = RULE_DIRECTIONS[index]
            ui.draw_arrow(surface, (panel.x + 48, y), 13, direction,
                          S.ARROW_COLORS[direction])
            ui.draw_text(surface, line, 18, S.COLOR_TEXT_DIM,
                         (panel.x + 70, y), anchor="midleft")

        for button in self.buttons:
            button.draw(surface)

        ui.draw_text(surface, "按 Esc 退出游戏", 16, S.COLOR_TEXT_FAINT, (cx, 730))


# ==================================================================== 游戏界面
class GameScene:
    def __init__(self, app):
        self.app = app
        self.time = 0.0

        self.overlay = None              # None | "win" | "lose"
        self.overlay_buttons = []

        self.hover_cell = None
        self.selected = None             # 被点中的格子，用于画选中脉冲
        self.select_timer = 0.0

        self.toast_text = ""
        self.toast_color = S.COLOR_TEXT
        self.toast_timer = 0.0

        right = TOP_BAR_CARD.right - 20
        self.buttons = [
            Button((right - 260, TOP_BAR_CARD.y + 14, 124, 44), "重新开始",
                   self.restart_level, font_size=19),
            Button((right - 124, TOP_BAR_CARD.y + 14, 124, 44), "返回菜单",
                   self.back_to_menu, font_size=19),
        ]

    # ---------------------------------------------------------- 对外动作
    @property
    def state(self):
        return self.app.state

    def restart_level(self):
        """重新开始：把当前关卡恢复到初始状态。"""
        self.state.reset()
        self.clear_feedback()
        self.close_overlay()
        self.show_toast("已重新开始本关", S.COLOR_ACCENT)

    def goto_next_level(self):
        if self.state.has_next_level:
            self.state.load_level(self.state.level_index + 1)
            self.clear_feedback()
            self.close_overlay()
            self.show_toast(f"进入第 {self.state.level_index + 1} 关", S.COLOR_ACCENT)

    def replay_all(self):
        self.app.start_new_game()

    def back_to_menu(self):
        self.app.goto_start()

    # ---------------------------------------------------------- 界面反馈
    def show_toast(self, text, color=S.COLOR_TEXT, duration=1.8):
        self.toast_text = text
        self.toast_color = color
        self.toast_timer = duration

    def clear_feedback(self):
        self.selected = None
        self.select_timer = 0.0
        self.hover_cell = None
        self.toast_timer = 0.0

    def open_overlay(self, kind):
        self.overlay = kind
        self.overlay_buttons = self.build_overlay_buttons(kind)

    def close_overlay(self):
        self.overlay = None
        self.overlay_buttons = []

    # ---------------------------------------------------------- 事件
    def on_escape(self):
        if self.overlay:            # 结算浮层只能用按钮关闭，避免误触后卡住
            return
        self.back_to_menu()

    def handle_event(self, event):
        if self.overlay:
            for button in self.overlay_buttons:
                button.handle_event(event)
            return

        for button in self.buttons:
            button.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self.update_hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.on_board_click(event.pos)
        elif event.type == pygame.KEYDOWN and S.DEV_PREVIEW:
            if event.key == pygame.K_F1:
                self.open_overlay("win")
            elif event.key == pygame.K_F2:
                self.open_overlay("lose")

    def update_hover(self, pos):
        _, grid, cell = self.layout()
        hover = cell_at(pos, grid, cell, self.state.rows, self.state.cols)
        if hover is not None and self.state.arrow_at(*hover) is None:
            hover = None
        self.hover_cell = hover

    def on_board_click(self, pos):
        """界面阶段：点击箭头只做选中反馈，消除/碰撞判定留到下一步接入。"""
        _, grid, cell = self.layout()
        target = cell_at(pos, grid, cell, self.state.rows, self.state.cols)
        if target is None:
            return
        direction = self.state.arrow_at(*target)
        if direction is None:
            return
        self.selected = target
        self.select_timer = 0.5
        self.show_toast(f"已选中「{DIRECTION_NAMES[direction]}」向箭头", S.COLOR_ACCENT, 1.2)

    def update(self, dt):
        self.time += dt
        if self.select_timer > 0:
            self.select_timer = max(0.0, self.select_timer - dt)
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)

    # ---------------------------------------------------------- 绘制
    def layout(self):
        return board_layout(self.state.rows, self.state.cols)

    def draw(self, surface):
        self.draw_top_bar(surface)
        self.draw_board(surface)
        self.draw_bottom_bar(surface)
        self.draw_toast(surface)
        if self.overlay:
            self.draw_overlay(surface)

    # -------------------------------------------------- 顶部信息栏
    def draw_top_bar(self, surface):
        state = self.state
        card = TOP_BAR_CARD
        draw_panel(surface, card, radius=20, top_color=S.COLOR_TOP_BAR_TOP,
                   bottom_color=S.COLOR_TOP_BAR_BOTTOM, border_color=S.COLOR_TOP_BAR_LINE,
                   shadow_alpha=105, shadow_offset=(0, 7))

        # 关卡信息：左侧强调条 + 主标题 + 副标题
        ui.draw_round_rect(surface, pygame.Rect(card.x + 20, card.centery - 21, 5, 42),
                           S.COLOR_ACCENT, 2)
        ui.draw_text(surface, f"第 {state.level_index + 1} 关", 28, S.COLOR_TEXT,
                     (card.x + 38, card.centery - 10), anchor="midleft", bold=True)
        ui.draw_text(surface, f"共 {state.total_levels} 关 · {state.name}", 16,
                     S.COLOR_TEXT_DIM, (card.x + 38, card.centery + 18), anchor="midleft")

        left = state.mistakes_left
        mistake_color = (S.COLOR_SUCCESS if left > 1 else
                         S.COLOR_WARN if left == 1 else S.COLOR_DANGER)
        self.draw_stat_chip(surface, (296, card.y + 8, 146, 56), "剩余箭头",
                            str(state.arrows_left), S.COLOR_ACCENT)
        self.draw_stat_chip(surface, (452, card.y + 8, 146, 56), "剩余失误",
                            f"{left} / {state.max_mistakes}", mistake_color)

        for button in self.buttons:
            button.draw(surface)

    @staticmethod
    def draw_stat_chip(surface, rect, label, value, value_color):
        rect = pygame.Rect(rect)
        surface.blit(ui.round_rect_surface(rect.size, 14, S.COLOR_CHIP_TOP,
                                           S.COLOR_CHIP_BOTTOM, S.COLOR_CHIP_BORDER, 1,
                                           highlight=True), rect.topleft)
        ui.draw_round_rect(surface, pygame.Rect(rect.x + 13, rect.centery - 15, 4, 30),
                           value_color, 2)
        ui.draw_text(surface, label, 14, S.COLOR_TEXT_FAINT,
                     (rect.x + 27, rect.y + 18), anchor="midleft")
        ui.draw_text(surface, value, 25, value_color,
                     (rect.x + 27, rect.y + 39), anchor="midleft", bold=True)

    # -------------------------------------------------- 棋盘
    def draw_board(self, surface):
        state = self.state
        panel, grid, cell = self.layout()
        tile_px = int(round(cell)) - S.CELL_GAP
        tile_radius = max(6, int(tile_px * 0.20))

        ui.draw_shadow(surface, panel, radius=26, spread=22, alpha=115, offset=(0, 12))
        surface.blit(ui.round_rect_surface(panel.size, 26, S.COLOR_BOARD_TOP,
                                           S.COLOR_BOARD_BOTTOM, S.COLOR_BOARD_BORDER, 2,
                                           highlight=True), panel.topleft)

        # 内凹的格子井，让格子看起来是嵌在棋盘里的
        well = grid.inflate(14, 14)
        surface.blit(ui.round_rect_surface(well.size, 18, S.COLOR_BOARD_WELL_TOP,
                                           S.COLOR_BOARD_WELL_BOTTOM,
                                           S.COLOR_BOARD_WELL_EDGE, 1, recess=True),
                     well.topleft)

        tile = ui.round_rect_surface((tile_px, tile_px), tile_radius, S.COLOR_TILE_TOP,
                                     S.COLOR_TILE_BOTTOM, S.COLOR_TILE_EDGE, 1,
                                     highlight=True, shade=True)
        tile_hover = ui.round_rect_surface((tile_px, tile_px), tile_radius,
                                           S.COLOR_TILE_HOVER_TOP, S.COLOR_TILE_HOVER_BOTTOM,
                                           S.COLOR_ACCENT, 2,
                                           highlight=True, shade=True)

        for row in range(state.rows):
            for col in range(state.cols):
                center = cell_rect(grid, cell, row, col).center
                hovered = self.hover_cell == (row, col)
                if hovered:
                    ui.draw_glow(surface, center, int(tile_px * 0.95), S.COLOR_ACCENT,
                                 alpha=40, layers=22)
                surface.blit(tile_hover if hovered else tile, tile.get_rect(center=center))

        for (row, col), direction in state.arrows.items():
            center = cell_rect(grid, cell, row, col).center
            hovered = self.hover_cell == (row, col)
            ui.draw_arrow(surface, center, cell * S.ARROW_SCALE, direction,
                          S.ARROW_COLORS[direction], scale=1.06 if hovered else 1.0)

        self.draw_selection(surface, grid, cell, tile_px, tile_radius)

    def draw_selection(self, surface, grid, cell, tile_px, tile_radius):
        """点中箭头后扩散一圈同色光环。"""
        if self.selected is None or self.select_timer <= 0:
            return
        direction = self.state.arrow_at(*self.selected)
        color = S.ARROW_COLORS.get(direction, S.COLOR_ACCENT)
        center = cell_rect(grid, cell, *self.selected).center
        t = 1.0 - self.select_timer / 0.5           # 0 → 1
        grow = int(4 + t * 18)
        ring = pygame.Surface((tile_px + grow * 2, tile_px + grow * 2), pygame.SRCALPHA)
        pygame.draw.rect(ring, (*color, int(215 * (1 - t))), ring.get_rect(),
                         width=3, border_radius=tile_radius + grow)
        surface.blit(ring, ring.get_rect(center=center))

    # -------------------------------------------------- 底部提示栏
    def draw_bottom_bar(self, surface):
        line_y = S.WINDOW_HEIGHT - S.BOTTOM_BAR_HEIGHT
        pygame.draw.line(surface, S.COLOR_TOP_BAR_LINE,
                         (60, line_y), (S.WINDOW_WIDTH - 60, line_y), 1)

        # toast 和提示文字占同一行，两者同时画会互相压字，所以 toast 显示时让位
        if self.toast_timer <= 0:
            text = "点击箭头：前方无阻挡 → 飞出棋盘；有阻挡 → 消耗 1 次失误"
            width = ui.text_width(text, 18) + 46
            pill = pygame.Rect(0, 0, width, 38)
            pill.center = (S.WINDOW_WIDTH // 2, line_y + 24)
            surface.blit(ui.round_rect_surface(pill.size, 19, S.COLOR_CHIP_TOP,
                                               S.COLOR_CHIP_BOTTOM, S.COLOR_CHIP_BORDER, 1),
                         pill.topleft)
            ui.draw_text(surface, text, 18, S.COLOR_TEXT_DIM, pill.center)

        if S.DEV_PREVIEW:
            ui.draw_text(surface,
                         "【界面阶段】点击箭头目前只做选中反馈，消除 / 碰撞判定待接入 · "
                         "F1 预览通关 · F2 预览失败",
                         15, S.COLOR_WARN, (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT - 18))

    def draw_toast(self, surface):
        if self.toast_timer <= 0 or not self.toast_text:
            return
        alpha = int(255 * min(1.0, self.toast_timer / 0.4))
        image = ui.font(19, bold=True).render(self.toast_text, True, self.toast_color)
        pill = image.get_rect().inflate(48, 22)
        pill.center = (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT - S.BOTTOM_BAR_HEIGHT + 24)

        layer = pygame.Surface(pill.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*S.COLOR_BOARD_BOTTOM, min(240, alpha)),
                         layer.get_rect(), border_radius=pill.height // 2)
        pygame.draw.rect(layer, (*self.toast_color, int(alpha * 0.75)), layer.get_rect(),
                         width=2, border_radius=pill.height // 2)
        image.set_alpha(alpha)
        layer.blit(image, image.get_rect(center=(pill.width // 2, pill.height // 2)))
        surface.blit(layer, pill)

    # -------------------------------------------------- 结算浮层
    @staticmethod
    def overlay_panel_rect():
        panel = pygame.Rect(0, 0, 520, 368)
        panel.center = (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT // 2 - 8)
        return panel

    def build_overlay_buttons(self, kind):
        panel = self.overlay_panel_rect()
        if kind == "win":
            if self.state.has_next_level:
                entries = [("下一关", self.goto_next_level, "primary"),
                           ("重玩本关", self.restart_level, "normal"),
                           ("返回菜单", self.back_to_menu, "normal")]
            else:
                entries = [("再玩一遍", self.replay_all, "primary"),
                           ("重玩本关", self.restart_level, "normal"),
                           ("返回菜单", self.back_to_menu, "normal")]
            width, gap = 146, 16
        else:
            entries = [("再试一次", self.restart_level, "primary"),
                       ("返回菜单", self.back_to_menu, "normal")]
            width, gap = 168, 18

        total = len(entries) * width + (len(entries) - 1) * gap
        x = panel.centerx - total // 2
        y = panel.bottom - 76
        buttons = []
        for label, callback, style in entries:
            buttons.append(Button((x, y, width, 50), label, callback,
                                  style=style, font_size=20))
            x += width + gap
        return buttons

    @staticmethod
    def draw_result_badge(surface, center, radius, color, kind):
        """结算面板顶部的圆形徽章：通关画对勾，失败画叉。"""
        ui.draw_glow(surface, center, int(radius * 2.0), color, alpha=70, layers=26)
        pygame.draw.circle(surface, darken_soft(color, 0.78), center, radius)
        pygame.draw.circle(surface, color, center, radius, width=3)
        width = max(4, int(radius * 0.17))
        cx, cy = center
        if kind == "win":
            points = [(cx - radius * 0.42, cy + radius * 0.02),
                      (cx - radius * 0.13, cy + radius * 0.32),
                      (cx + radius * 0.44, cy - radius * 0.34)]
            pygame.draw.lines(surface, color, False, points, width)
            for point in points:
                pygame.draw.circle(surface, color, point, width // 2)
        else:
            offset = radius * 0.36
            for dx, dy in ((-1, -1), (-1, 1)):
                start = (cx + dx * offset, cy + dy * offset)
                end = (cx - dx * offset, cy - dy * offset)
                pygame.draw.line(surface, color, start, end, width)
                pygame.draw.circle(surface, color, start, width // 2)
                pygame.draw.circle(surface, color, end, width // 2)

    def draw_overlay(self, surface):
        win = self.overlay == "win"
        state = self.state
        accent = S.COLOR_SUCCESS if win else S.COLOR_DANGER

        dim = pygame.Surface((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        dim.set_alpha(S.COLOR_OVERLAY[3])
        dim.fill(S.COLOR_OVERLAY[:3])
        surface.blit(dim, (0, 0))

        panel = self.overlay_panel_rect()
        ui.draw_glow(surface, panel.center, 340, accent, alpha=42, layers=32)
        draw_panel(surface, panel, radius=24, border_color=accent, border_width=2,
                   shadow_alpha=130, shadow_offset=(0, 12))

        self.draw_result_badge(surface, (panel.centerx, panel.y + 74), 34, accent,
                               "win" if win else "lose")

        ui.draw_text_gradient(surface, "通 关 ！" if win else "闯 关 失 败", 46,
                              S.COLOR_TITLE_TOP, accent,
                              (panel.centerx, panel.y + 148), bold=True)

        if win:
            detail = (f"第 {state.level_index + 1} 关「{state.name}」已完成 · "
                      f"剩余失误 {state.mistakes_left} 次")
            note = "全部关卡已通关，厉害！" if not state.has_next_level else "准备进入下一关"
        else:
            detail = f"失误次数已耗尽（共 {state.max_mistakes} 次）"
            note = "再试一次，注意箭头的方向"

        ui.draw_text(surface, detail, 19, S.COLOR_TEXT_DIM, (panel.centerx, panel.y + 198))
        ui.draw_text(surface, note, 17, S.COLOR_TEXT_FAINT, (panel.centerx, panel.y + 230))

        for button in self.overlay_buttons:
            button.draw(surface)


def darken_soft(color, amount):
    """ui.darken 的薄封装，让徽章底色不至于全黑。"""
    return ui.mix(color, (10, 12, 20), amount)
