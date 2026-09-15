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


# ==================================================================== 背景
def make_background(size):
    """生成一次性渐变背景（只算一次，之后每帧直接 blit）。"""
    width, height = size
    surface = pygame.Surface(size)
    for y in range(height):
        t = y / max(1, height - 1)
        pygame.draw.line(surface, ui.mix(S.COLOR_BG_TOP, S.COLOR_BG_BOTTOM, t),
                         (0, y), (width, y))
    return surface


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
    """第 row 行第 col 列格子的矩形（用两次 round 保证格子之间无缝隙）。"""
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


# ==================================================================== 开始界面
class StartScene:
    def __init__(self, app):
        self.app = app
        self.time = 0.0
        cx = S.WINDOW_WIDTH // 2
        self.buttons = [
            Button((cx - 140, 552, 280, 64), "开 始 游 戏", self.app.start_new_game,
                   style="primary", font_size=26),
            Button((cx - 90, 632, 180, 48), "退出游戏", self.app.quit, font_size=20),
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

        # 顶部一排四个方向的装饰箭头，轻微上下浮动
        for index, direction in enumerate(("up", "down", "left", "right")):
            x = cx + (index - 1.5) * 96
            bob = math.sin(self.time * 2.0 + index * 0.7) * 6
            ui.draw_arrow(surface, (x, 126 + bob), 44, direction, S.ARROW_COLORS[direction])

        ui.draw_text(surface, "一箭又一箭", 78, S.COLOR_TEXT, (cx, 230), bold=True)
        ui.draw_text(surface, "Arrow Escape · Python 基础版", 22, S.COLOR_TEXT_DIM, (cx, 286))

        # 玩法说明面板
        panel = pygame.Rect(0, 0, 700, 196)
        panel.center = (cx, 404)
        ui.draw_shadow(surface, panel, radius=18, spread=14, alpha=90, offset=(0, 6))
        ui.draw_round_rect(surface, panel, S.COLOR_PANEL, 18, S.COLOR_PANEL_BORDER, 2)
        ui.draw_text(surface, "玩 法 说 明", 21, S.COLOR_ACCENT,
                     (panel.centerx, panel.y + 30), bold=True)
        for index, line in enumerate((
            "点击棋盘上的箭头，它会沿着自己的方向前进。",
            "前方到棋盘边界没有其他箭头 → 箭头飞出棋盘并消失。",
            "前方有其他箭头阻挡 → 无法消除，并消耗一次失误机会。",
            "清空全部箭头进入下一关；失误次数耗尽则本关失败。",
        )):
            ui.draw_text(surface, line, 19, S.COLOR_TEXT_DIM,
                         (panel.x + 36, panel.y + 70 + index * 31), anchor="midleft")

        for button in self.buttons:
            button.draw(surface)

        ui.draw_text(surface, "按 Esc 退出游戏", 17, S.COLOR_TEXT_FAINT,
                     (cx, S.WINDOW_HEIGHT - 22))


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

        right = S.WINDOW_WIDTH - 32
        self.buttons = [
            Button((right - 260, 26, 124, 44), "重新开始", self.restart_level, font_size=19),
            Button((right - 124, 26, 124, 44), "返回菜单", self.back_to_menu, font_size=19),
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
        bar = pygame.Rect(0, 0, S.WINDOW_WIDTH, S.TOP_BAR_HEIGHT)
        pygame.draw.rect(surface, S.COLOR_TOP_BAR, bar)
        pygame.draw.line(surface, S.COLOR_TOP_BAR_LINE,
                         (0, bar.bottom - 1), (bar.right, bar.bottom - 1), 2)

        ui.draw_text(surface, f"第 {state.level_index + 1} 关", 28, S.COLOR_TEXT,
                     (32, 34), anchor="midleft", bold=True)
        ui.draw_text(surface, f"共 {state.total_levels} 关 · {state.name}", 17,
                     S.COLOR_TEXT_DIM, (32, 68), anchor="midleft")

        self.draw_stat_chip(surface, (274, 20, 148, 56), "剩余箭头",
                            str(state.arrows_left), S.COLOR_ACCENT)
        left = state.mistakes_left
        color = (S.COLOR_SUCCESS if left > 1 else
                 S.COLOR_WARN if left == 1 else S.COLOR_DANGER)
        self.draw_stat_chip(surface, (438, 20, 148, 56), "剩余失误",
                            f"{left} / {state.max_mistakes}", color)

        for button in self.buttons:
            button.draw(surface)

    @staticmethod
    def draw_stat_chip(surface, rect, label, value, value_color):
        rect = pygame.Rect(rect)
        ui.draw_round_rect(surface, rect, S.COLOR_CHIP_BG, 12, S.COLOR_CHIP_BORDER, 2)
        ui.draw_text(surface, label, 15, S.COLOR_TEXT_FAINT, (rect.centerx, rect.y + 17))
        ui.draw_text(surface, value, 25, value_color, (rect.centerx, rect.y + 39), bold=True)

    # -------------------------------------------------- 棋盘
    def draw_board(self, surface):
        state = self.state
        panel, grid, cell = self.layout()
        radius = max(4, int(cell * 0.16))

        ui.draw_shadow(surface, panel, radius=20, spread=16, alpha=100, offset=(0, 8))
        ui.draw_round_rect(surface, panel, S.COLOR_BOARD_BG, 20, S.COLOR_BOARD_BORDER, 3)

        # 1) 底板格子
        for row in range(state.rows):
            for col in range(state.cols):
                rect = cell_rect(grid, cell, row, col).inflate(-S.CELL_GAP, -S.CELL_GAP)
                base = S.COLOR_CELL_BG if (row + col) % 2 == 0 else S.COLOR_CELL_BG_ALT
                if self.hover_cell == (row, col):
                    base = ui.lighten(base, 0.18)
                ui.draw_round_rect(surface, rect, base, radius)
                if self.hover_cell == (row, col):
                    pygame.draw.rect(surface, S.COLOR_ACCENT, rect,
                                     width=3, border_radius=radius)

        # 2) 箭头
        for (row, col), direction in state.arrows.items():
            ui.draw_arrow(surface, cell_rect(grid, cell, row, col).center,
                          cell * S.ARROW_SCALE, direction, S.ARROW_COLORS[direction])

        # 3) 选中脉冲
        if self.selected is not None and self.select_timer > 0:
            rect = cell_rect(grid, cell, *self.selected).inflate(-S.CELL_GAP, -S.CELL_GAP)
            t = 1.0 - self.select_timer / 0.5          # 0 → 1
            grow = int(2 + t * 14)
            ring = pygame.Surface((rect.width + grow * 2, rect.height + grow * 2),
                                  pygame.SRCALPHA)
            pygame.draw.rect(ring, (*S.COLOR_ACCENT, int(220 * (1 - t))),
                             ring.get_rect(), width=4, border_radius=radius + grow)
            surface.blit(ring, (rect.x - grow, rect.y - grow))

    # -------------------------------------------------- 底部提示栏
    def draw_bottom_bar(self, surface):
        # toast 和提示文字占同一行，两者同时画会互相压字，所以 toast 显示时让位
        if self.toast_timer <= 0:
            ui.draw_text(surface, "点击箭头：前方无阻挡 → 飞出棋盘；有阻挡 → 消耗 1 次失误",
                         18, S.COLOR_TEXT_DIM,
                         (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT - 46))
        if S.DEV_PREVIEW:
            ui.draw_text(surface,
                         "【界面阶段】点击箭头目前只做选中反馈，消除 / 碰撞判定待接入 · "
                         "F1 预览通关 · F2 预览失败",
                         15, S.COLOR_WARN, (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT - 20))

    def draw_toast(self, surface):
        if self.toast_timer <= 0 or not self.toast_text:
            return
        alpha = int(255 * min(1.0, self.toast_timer / 0.4))
        image = ui.font(20, bold=True).render(self.toast_text, True, self.toast_color)
        pill = image.get_rect().inflate(40, 20)
        pill.center = (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT - 46)

        layer = pygame.Surface(pill.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*S.COLOR_BOARD_BG, min(235, alpha)),
                         layer.get_rect(), border_radius=pill.height // 2)
        pygame.draw.rect(layer, (*S.COLOR_ACCENT, alpha), layer.get_rect(),
                         width=2, border_radius=pill.height // 2)
        image.set_alpha(alpha)
        layer.blit(image, image.get_rect(center=(pill.width // 2, pill.height // 2)))
        surface.blit(layer, pill)

    # -------------------------------------------------- 结算浮层
    @staticmethod
    def overlay_panel_rect():
        panel = pygame.Rect(0, 0, 500, 336)
        panel.center = (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT // 2 - 6)
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
            width, gap = 140, 16
        else:
            entries = [("再试一次", self.restart_level, "primary"),
                       ("返回菜单", self.back_to_menu, "normal")]
            width, gap = 160, 18

        total = len(entries) * width + (len(entries) - 1) * gap
        x = panel.centerx - total // 2
        y = panel.bottom - 84
        buttons = []
        for label, callback, style in entries:
            buttons.append(Button((x, y, width, 50), label, callback,
                                  style=style, font_size=20))
            x += width + gap
        return buttons

    def draw_overlay(self, surface):
        win = self.overlay == "win"
        state = self.state

        dim = pygame.Surface((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        dim.set_alpha(S.COLOR_OVERLAY[3])
        dim.fill(S.COLOR_OVERLAY[:3])
        surface.blit(dim, (0, 0))

        panel = self.overlay_panel_rect()
        border = S.COLOR_SUCCESS if win else S.COLOR_DANGER
        ui.draw_shadow(surface, panel, radius=22, spread=20, alpha=120, offset=(0, 10))
        ui.draw_round_rect(surface, panel, S.COLOR_BOARD_BG, 22, border, 3)

        ui.draw_text(surface, "通 关 ！" if win else "闯 关 失 败", 48, border,
                     (panel.centerx, panel.y + 78), bold=True)

        if win:
            detail = (f"第 {state.level_index + 1} 关「{state.name}」已完成 · "
                      f"剩余失误 {state.mistakes_left} 次")
            note = "全部关卡已通关，厉害！" if not state.has_next_level else "准备进入下一关"
        else:
            detail = f"失误次数已耗尽（共 {state.max_mistakes} 次）"
            note = "再试一次，注意箭头的方向"

        ui.draw_text(surface, detail, 19, S.COLOR_TEXT_DIM, (panel.centerx, panel.y + 140))
        ui.draw_text(surface, note, 18, S.COLOR_TEXT_FAINT, (panel.centerx, panel.y + 178))

        for button in self.overlay_buttons:
            button.draw(surface)
