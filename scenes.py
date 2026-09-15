# -*- coding: utf-8 -*-
"""三个界面：开始界面、游戏界面，以及叠在游戏界面上的通关/失败结算浮层。

界面的职责只有"显示"和"把点击翻译成动作"，不含消除判定规则。
"""

from __future__ import annotations

import math

import pygame

import settings as S
import score
import ui
from effects import Bounce, FlyOut
from game import DIRECTION_NAMES, DIRECTION_VECTORS
from levels import LEVELS
from ui import Button

# 顶部信息栏做成一张浮起的卡片，而不是通栏色块
TOP_BAR_CARD = pygame.Rect(20, 12, S.WINDOW_WIDTH - 40, 72)

# 选关界面的卡片网格
SELECT_CARD_WIDTH = 196
SELECT_CARD_HEIGHT = 130
SELECT_COLUMNS = 4
SELECT_GAP = 20
SELECT_TOP = 172

# 开始界面顶端那排装饰箭头
DECOR_DIRECTIONS = ("up", "down", "left", "right")

# 玩法说明每行前面那个小箭头的方向（行数比方向数多，循环取用即可）
RULE_DIRECTIONS = ("up", "down", "left", "right", "up")

RULE_LINES = (
    "点击棋盘上的箭头，它会沿着自己的方向前进。",
    "前方到棋盘边界没有其他箭头 → 箭头飞出棋盘并消失。",
    "前方有其他箭头阻挡 → 无法消除，并消耗一次失误机会。",
    "清空全部箭头即可通关；失误次数耗尽则本关失败。",
    "卡住了可以点「提示」看该消哪个，点「撤销」退回上一步。",
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


def select_card_rects(count):
    """算出选关界面每一张关卡卡片的位置（按行排列、整体居中）。"""
    rows = (count + SELECT_COLUMNS - 1) // SELECT_COLUMNS
    total_w = SELECT_COLUMNS * SELECT_CARD_WIDTH + (SELECT_COLUMNS - 1) * SELECT_GAP
    left = (S.WINDOW_WIDTH - total_w) // 2
    rects = []
    for index in range(count):
        row, col = divmod(index, SELECT_COLUMNS)
        rects.append(pygame.Rect(
            left + col * (SELECT_CARD_WIDTH + SELECT_GAP),
            SELECT_TOP + row * (SELECT_CARD_HEIGHT + SELECT_GAP),
            SELECT_CARD_WIDTH, SELECT_CARD_HEIGHT))
    return rects


def draw_lock(surface, center, size, color):
    """画一个简单的挂锁图标：圆环当锁梁，矩形当锁体，锁体盖住圆环下半。"""
    cx, cy = center
    thickness = max(2, int(size * 0.15))
    pygame.draw.circle(surface, color, (int(cx), int(cy - size * 0.12)),
                       int(size * 0.26), thickness)
    body = pygame.Rect(0, 0, int(size * 0.72), int(size * 0.54))
    body.center = (int(cx), int(cy + size * 0.16))
    pygame.draw.rect(surface, color, body, border_radius=max(2, int(size * 0.12)))


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
        session = app.session
        if session.exists:
            primary = (f"继续第 {session.level_index + 1} 关", app.continue_game)
            secondary = [("新游戏", app.start_new_game),
                         ("选择关卡", app.goto_select),
                         ("退出游戏", app.quit)]
            second_w, second_gap = 168, 14
        else:
            primary = ("开 始 游 戏", app.start_new_game)
            secondary = [("选择关卡", app.goto_select),
                         ("退出游戏", app.quit)]
            second_w, second_gap = 185, 14

        self.buttons = [Button((cx - 150, 532, 300, 64), primary[0], primary[1],
                               style="primary", font_size=27)]
        total = len(secondary) * second_w + (len(secondary) - 1) * second_gap
        x = cx - total // 2
        for label, callback in secondary:
            self.buttons.append(Button((x, 608, second_w, 48), label, callback,
                                       font_size=20))
            x += second_w + second_gap

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
        for index, direction in enumerate(DECOR_DIRECTIONS):
            x = cx + (index - 1.5) * 110
            bob = math.sin(self.time * 1.8 + index * 0.8) * 7
            ui.draw_arrow(surface, (x, 120 + bob), 48, direction, S.ARROW_COLORS[direction])

        ui.draw_text_gradient(surface, "一箭又一箭", 84,
                              S.COLOR_TITLE_TOP, S.COLOR_TITLE_BOTTOM,
                              (cx, 208), bold=True)
        ui.draw_text(surface, "Arrow Escape", 21, S.COLOR_TEXT_DIM, (cx, 268))
        pygame.draw.line(surface, ui.mix(S.COLOR_ACCENT, S.COLOR_BG_BOTTOM, 0.62),
                         (cx - 150, 280), (cx + 150, 280), 2)

        # 玩法说明面板
        panel = pygame.Rect(0, 0, 740, 236)
        panel.center = (cx, 400)
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

        progress = self.app.progress
        ui.draw_text(surface,
                     f"已通关 {progress.cleared_count} / {len(LEVELS)} 关 · "
                     f"总分 {score.format_score(progress.total_score)}",
                     16, S.COLOR_TEXT_DIM, (cx, 690))
        ui.draw_text(surface, "按 Esc 退出游戏", 16, S.COLOR_TEXT_FAINT, (cx, 722))


# ==================================================================== 游戏界面
class GameScene:
    def __init__(self, app):
        self.app = app
        self.time = 0.0

        self.overlay = None              # None | "win" | "lose"
        self.overlay_buttons = []

        self.animations = []             # 正在播放的箭头动画（飞出 / 碰撞）
        self.hover_cell = None
        self.hit_cell = None             # 刚被挡住的格子，画一圈红色扩散环
        self.hit_timer = 0.0

        self.toast_text = ""
        self.toast_color = S.COLOR_TEXT
        self.toast_timer = 0.0

        self.result = None               # 本关结算数据（得分明细等）

        self.hints_left = S.HINTS_PER_LEVEL
        self.hint_cell = None            # 被提示标出的格子
        self.hint_timer = 0.0

        self.undos_left = S.UNDOS_PER_LEVEL
        self.history = []                # 本关的操作记录，供撤销回退

        right = TOP_BAR_CARD.right - 20
        self.buttons = [
            Button((right - 260, TOP_BAR_CARD.y + 14, 124, 44), "重新开始",
                   self.restart_level, font_size=19),
            Button((right - 124, TOP_BAR_CARD.y + 14, 124, 44), "选择关卡",
                   self.goto_select, font_size=19),
        ]
        bar_y = S.WINDOW_HEIGHT - S.BOTTOM_BAR_HEIGHT + 14
        self.undo_button = Button((644, bar_y, 112, 44), "撤销",
                                  self.undo, font_size=19)
        self.hint_button = Button((768, bar_y, 112, 44), "提示",
                                  self.use_hint, font_size=19)
        self.refresh_action_buttons()

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
        self.save_progress()

    def goto_next_level(self):
        if self.state.has_next_level:
            self.state.load_level(self.state.level_index + 1)
            self.clear_feedback()
            self.close_overlay()
            self.show_toast(f"进入第 {self.state.level_index + 1} 关", S.COLOR_ACCENT)
            self.save_progress()

    def replay_all(self):
        self.app.start_new_game()

    def goto_select(self):
        self.app.goto_select()

    # ---------------------------------------------------------- 单局存档
    def save_progress(self):
        """把本关当前状态写进单局存档，随时退出都能接着玩。

        已经结算完的关卡不用存——通关或失败都表示这一关已经结束了。
        """
        if self.overlay:
            return
        state = self.state
        self.app.session.save(
            level=state.level_index,
            arrows=state.arrows,
            mistakes=state.mistakes,
            elapsed=state.elapsed,
            hints_left=self.hints_left,
            undos_left=self.undos_left,
            history=self.history,
        )

    def restore(self, payload):
        """从单局存档恢复本关进度。"""
        state = self.state
        state.arrows = dict(payload["arrows"])
        state.mistakes = payload["mistakes"]
        state.elapsed = payload["elapsed"]
        state.final_time = None
        self.hints_left = min(payload["hints_left"], S.HINTS_PER_LEVEL)
        self.undos_left = min(payload["undos_left"], S.UNDOS_PER_LEVEL)
        self.history = list(payload["history"])
        self.refresh_action_buttons()

    # ---------------------------------------------------------- 界面反馈
    def show_toast(self, text, color=S.COLOR_TEXT, duration=1.8):
        self.toast_text = text
        self.toast_color = color
        self.toast_timer = duration

    def clear_feedback(self):
        self.animations.clear()
        self.hit_cell = None
        self.hit_timer = 0.0
        self.hover_cell = None
        self.toast_timer = 0.0
        self.result = None
        self.hints_left = S.HINTS_PER_LEVEL
        self.hint_cell = None
        self.hint_timer = 0.0
        self.undos_left = S.UNDOS_PER_LEVEL
        self.history.clear()
        self.refresh_action_buttons()

    def refresh_action_buttons(self):
        self.hint_button.label = f"提示 ×{self.hints_left}"
        self.hint_button.enabled = self.hints_left > 0
        self.undo_button.label = f"撤销 ×{self.undos_left}"
        self.undo_button.enabled = self.undos_left > 0 and bool(self.history)

    def use_hint(self):
        """标出一个当前能直接消掉的箭头，供玩家参考。"""
        if self.overlay or self.hints_left <= 0:
            return
        cell = self.state.hint()
        if cell is None:
            return
        self.hints_left -= 1
        self.hint_cell = cell
        self.hint_timer = S.HINT_SECONDS
        self.refresh_action_buttons()
        self.save_progress()
        left = self.hints_left
        tail = f"（还剩 {left} 次）" if left else "（提示已用完）"
        self.show_toast(f"试试金框标出的箭头 {tail}", S.COLOR_HINT, 2.2)

    def undo(self):
        """撤销上一步：把飞出去的箭头放回原位，或者退回一次误点扣掉的失误。"""
        if self.overlay or self.undos_left <= 0 or not self.history:
            return
        action = self.history.pop()
        state = self.state

        if action["kind"] == "launch":
            state.restore(action["cell"], action["direction"])
            # 顺手把这段飞出动画撤掉，否则箭头会一边往回放一边还在往外飞
            self.animations = [anim for anim in self.animations
                               if not (anim.kind == "fly" and anim.cell == action["cell"])]
            label = "已把飞出的箭头放回原位"
        else:
            state.refund_mistake()
            self.animations = [anim for anim in self.animations
                               if not (anim.kind == "bounce"
                                       and anim.cell == action["cell"])]
            if self.hit_cell == action["cell"]:
                self.hit_cell = None
                self.hit_timer = 0.0
            label = "已退回一次失误"

        self.undos_left -= 1
        self.refresh_action_buttons()
        self.save_progress()
        tail = f"（还剩 {self.undos_left} 次）" if self.undos_left else "（撤销已用完）"
        self.show_toast(f"{label} {tail}", S.COLOR_UNDO, 1.9)

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
        self.goto_select()

    def handle_event(self, event):
        if self.overlay:
            for button in self.overlay_buttons:
                button.handle_event(event)
            return

        for button in self.buttons:
            button.handle_event(event)
        self.undo_button.handle_event(event)
        self.hint_button.handle_event(event)

        if event.type == pygame.MOUSEMOTION:
            self.update_hover(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.on_board_click(event.pos)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_z \
                and event.mod & pygame.KMOD_CTRL:
            self.undo()

    def update_hover(self, pos):
        _, grid, cell = self.layout()
        hover = cell_at(pos, grid, cell, self.state.rows, self.state.cols)
        if hover is not None and self.state.arrow_at(*hover) is None:
            hover = None
        self.hover_cell = hover

    def on_board_click(self, pos):
        _, grid, cell = self.layout()
        target = cell_at(pos, grid, cell, self.state.rows, self.state.cols)
        if target is not None:
            self.resolve_click(target)

    # ---------------------------------------------------------- 核心判定
    def resolve_click(self, cell):
        """点一个格子的完整判定：飞得出去就飞出消除，飞不出去就记一次失误。"""
        direction = self.state.arrow_at(*cell)
        if direction is None:
            return
        if self.is_animating(cell):
            return                       # 该格动画还没播完，忽略连点
        if self.state.can_leave(*cell):
            self.launch(cell, direction)
        else:
            self.block(cell, direction)
        self.refresh_action_buttons()
        self.save_progress()

    def is_animating(self, cell):
        return any(anim.cell == cell for anim in self.animations)

    def launch(self, cell, direction):
        """前方无阻挡：箭头立刻从棋盘上移除，同时播一段飞出动画。"""
        state = self.state
        distance = state.steps_to_edge(*cell) + 1.5      # 多飞一点，确保完全出屏
        color = S.ARROW_COLORS[direction]
        state.remove(*cell)
        self.animations.append(FlyOut(cell, direction, distance, color))
        self.history.append({"kind": "launch", "cell": cell, "direction": direction})
        self.hit_cell = None
        self.hit_timer = 0.0

    def block(self, cell, direction):
        """前方有阻挡：消耗一次失误，箭头前冲回弹 + 闪白 + 文字提示。"""
        state = self.state
        gap = state.steps_to_blocker(*cell)
        state.add_mistake()
        self.animations.append(Bounce(cell, direction, gap, S.ARROW_COLORS[direction]))
        self.history.append({"kind": "block", "cell": cell})
        self.hit_cell = cell
        self.hit_timer = 0.55
        self.show_toast(
            f"「{DIRECTION_NAMES[direction]}」向被挡住 · "
            f"失误 {state.mistakes} / {state.max_mistakes}",
            S.COLOR_DANGER, 1.6)

    def update(self, dt):
        self.time += dt
        self.state.tick(dt)
        for anim in list(self.animations):
            if anim.update(dt):
                self.animations.remove(anim)
        if self.hit_timer > 0:
            self.hit_timer = max(0.0, self.hit_timer - dt)
        if self.hint_timer > 0:
            self.hint_timer = max(0.0, self.hint_timer - dt)
        if self.toast_timer > 0:
            self.toast_timer = max(0.0, self.toast_timer - dt)
        self.settle_if_finished()

    @property
    def visible_hint(self):
        """当前真正该高亮的格子。

        提示目标会一直记着，但只有箭头还在棋盘上时才画出来：消掉就不画，
        撤销把箭头放回来又自然重新出现，不用额外处理。
        """
        if self.hint_cell is None or self.hint_timer <= 0:
            return None
        return self.hint_cell if self.hint_cell in self.state.arrows else None

    def settle_if_finished(self):
        """等动画播完再结算，避免箭头还在飞就弹出结算面板。"""
        if self.overlay or self.animations:
            return
        if not self.state.arrows:
            self.finish_level(win=True)
        elif self.state.lost:
            self.finish_level(win=False)

    def finish_level(self, win):
        """停表、算分、写成绩，然后弹出结算面板。"""
        state = self.state
        seconds = state.stop_clock()
        hints_used = S.HINTS_PER_LEVEL - self.hints_left
        undos_used = S.UNDOS_PER_LEVEL - self.undos_left
        self.app.session.clear()          # 这一关结束了，单局存档没用了
        if win:
            total, parts = score.breakdown(state.level, seconds, state.mistakes_left,
                                           hints_used, undos_used)
            better_score, better_time = self.app.progress.record(
                state.level_index, total, seconds)
            self.result = {"score": total, "parts": parts, "seconds": seconds,
                           "hints_used": hints_used, "undos_used": undos_used,
                           "better_score": better_score, "better_time": better_time}
            self.open_overlay("win")
        else:
            self.result = {"score": 0, "parts": [], "seconds": seconds,
                           "hints_used": hints_used, "undos_used": undos_used,
                           "better_score": False, "better_time": False}
            self.open_overlay("lose")

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
        # 超过目标用时就没有速度奖励了，胶囊换成橙色提示一下
        target = score.target_seconds(state.level)
        time_color = S.COLOR_WARN if state.seconds > target else S.COLOR_TIME
        chips = (
            ("剩余箭头", str(state.arrows_left), S.COLOR_ACCENT),
            ("剩余失误", f"{left} / {state.max_mistakes}", mistake_color),
            ("用时", score.format_clock(state.seconds), time_color),
        )
        for offset, (label, value, color) in enumerate(chips):
            self.draw_stat_chip(surface, (212 + offset * 136, card.y + 8, 124, 56),
                                label, value, color)

        for button in self.buttons:
            button.draw(surface)

    @staticmethod
    def draw_stat_chip(surface, rect, label, value, value_color):
        rect = pygame.Rect(rect)
        surface.blit(ui.round_rect_surface(rect.size, 14, S.COLOR_CHIP_TOP,
                                           S.COLOR_CHIP_BOTTOM, S.COLOR_CHIP_BORDER, 1,
                                           highlight=True), rect.topleft)
        ui.draw_round_rect(surface, pygame.Rect(rect.x + 12, rect.centery - 15, 4, 30),
                           value_color, 2)
        ui.draw_text(surface, label, 13, S.COLOR_TEXT_FAINT,
                     (rect.x + 24, rect.y + 18), anchor="midleft")
        ui.draw_text(surface, value, 23, value_color,
                     (rect.x + 24, rect.y + 39), anchor="midleft", bold=True)

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

        busy = {anim.cell for anim in self.animations}
        for row in range(state.rows):
            for col in range(state.cols):
                center = cell_rect(grid, cell, row, col).center
                hovered = self.hover_cell == (row, col) and (row, col) not in busy
                if hovered:
                    ui.draw_glow(surface, center, int(tile_px * 0.95), S.COLOR_ACCENT,
                                 alpha=40, layers=22)
                surface.blit(tile_hover if hovered else tile, tile.get_rect(center=center))

        # 留在棋盘上的箭头（正在碰撞回弹的会带偏移和闪白）
        for (row, col), direction in state.arrows.items():
            offset, color, scale = self.arrow_pose(row, col, direction, busy)
            center = cell_rect(grid, cell, row, col).center
            center = (center[0] + offset[1] * cell, center[1] + offset[0] * cell)
            ui.draw_arrow(surface, center, cell * S.ARROW_SCALE, direction,
                          color, scale=scale)

        # 正在飞出棋盘的箭头
        for anim in self.animations:
            if anim.kind == "fly":
                self.draw_flight(surface, grid, cell, anim)

        self.draw_hit_ring(surface, grid, cell, tile_px, tile_radius)
        self.draw_hint(surface, grid, cell, tile_px, tile_radius)

    def draw_hint(self, surface, grid, cell, tile_px, tile_radius):
        """提示：金色脉冲光环，呼吸式明暗，比选中环更醒目。"""
        target = self.visible_hint
        if target is None:
            return
        center = cell_rect(grid, cell, *target).center
        pulse = 0.5 + 0.5 * math.sin(self.time * 6.0)
        ui.draw_glow(surface, center, int(tile_px * 1.15), S.COLOR_HINT,
                     alpha=int(46 + 46 * pulse), layers=22)
        grow = int(3 + 6 * pulse)
        ring = pygame.Surface((tile_px + grow * 2, tile_px + grow * 2), pygame.SRCALPHA)
        pygame.draw.rect(ring, (*S.COLOR_HINT, 235), ring.get_rect(),
                         width=4, border_radius=tile_radius + grow)
        surface.blit(ring, ring.get_rect(center=center))

    def arrow_pose(self, row, col, direction, busy):
        """算出某个箭头的 (位移格数, 颜色, 缩放)：碰撞时前冲、闪白、略微放大。"""
        base = S.ARROW_COLORS[direction]
        bounce = next((a for a in self.animations
                       if a.kind == "bounce" and a.cell == (row, col)), None)
        if bounce is None:
            hovered = self.hover_cell == (row, col) and (row, col) not in busy
            return (0.0, 0.0), base, 1.06 if hovered else 1.0
        color = ui.mix(base, (255, 246, 246), 0.62 * bounce.flash)
        return bounce.offset(), color, 1.0 + 0.05 * bounce.flash

    def draw_flight(self, surface, grid, cell, anim):
        """画出正在飞出的箭头，身后带三段渐隐拖尾。"""
        dr, dc = DIRECTION_VECTORS[anim.direction]
        base = cell_rect(grid, cell, *anim.cell).center
        arrow_size = cell * S.ARROW_SCALE
        alpha_ratio = anim.alpha / 255.0

        def at(traveled):
            return (base[0] + dc * traveled * cell, base[1] + dr * traveled * cell)

        for back, ghost_alpha in ((0.62, 34), (0.42, 58), (0.22, 96)):
            ghost = int(ghost_alpha * alpha_ratio)
            if ghost > 0:
                ui.draw_arrow(surface, at(max(0.0, anim.traveled - back)),
                              arrow_size, anim.direction, anim.color, alpha=ghost)
        if anim.alpha > 0:
            ui.draw_arrow(surface, at(anim.traveled), arrow_size,
                          anim.direction, anim.color, alpha=anim.alpha)

    def draw_hit_ring(self, surface, grid, cell, tile_px, tile_radius):
        """被挡住时在格子上扩散一圈红色光环。"""
        if self.hit_cell is None or self.hit_timer <= 0:
            return
        center = cell_rect(grid, cell, *self.hit_cell).center
        t = 1.0 - self.hit_timer / 0.55           # 0 → 1
        grow = int(4 + t * 18)
        ring = pygame.Surface((tile_px + grow * 2, tile_px + grow * 2), pygame.SRCALPHA)
        pygame.draw.rect(ring, (*S.COLOR_DANGER, int(215 * (1 - t))), ring.get_rect(),
                         width=3, border_radius=tile_radius + grow)
        surface.blit(ring, ring.get_rect(center=center))

    # -------------------------------------------------- 底部提示栏
    def draw_bottom_bar(self, surface):
        line_y = S.WINDOW_HEIGHT - S.BOTTOM_BAR_HEIGHT
        pygame.draw.line(surface, S.COLOR_TOP_BAR_LINE,
                         (60, line_y), (S.WINDOW_WIDTH - 60, line_y), 1)

        # toast 和提示文字占同一格，两者同时画会互相压字，所以 toast 显示时让位
        if self.toast_timer <= 0:
            text = "点击箭头：前方无阻挡 → 飞出棋盘；有阻挡 → 消耗 1 次失误"
            width = ui.text_width(text, 18) + 46
            pill = pygame.Rect(40, 0, width, 38)
            pill.centery = line_y + S.BOTTOM_BAR_HEIGHT // 2
            surface.blit(ui.round_rect_surface(pill.size, 19, S.COLOR_CHIP_TOP,
                                               S.COLOR_CHIP_BOTTOM, S.COLOR_CHIP_BORDER, 1),
                         pill.topleft)
            ui.draw_text(surface, text, 18, S.COLOR_TEXT_DIM,
                         (pill.x + 23, pill.centery), anchor="midleft")

        self.undo_button.draw(surface)
        self.hint_button.draw(surface)

    def draw_toast(self, surface):
        if self.toast_timer <= 0 or not self.toast_text:
            return
        alpha = int(255 * min(1.0, self.toast_timer / 0.4))
        image = ui.font(19, bold=True).render(self.toast_text, True, self.toast_color)
        pill = image.get_rect().inflate(48, 22)
        # 左对齐，给右下角的撤销 / 提示按钮让位
        pill.midleft = (40, S.WINDOW_HEIGHT - S.BOTTOM_BAR_HEIGHT
                        + S.BOTTOM_BAR_HEIGHT // 2)

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
        panel = pygame.Rect(0, 0, 560, 424)
        panel.center = (S.WINDOW_WIDTH // 2, S.WINDOW_HEIGHT // 2 - 10)
        return panel

    def build_overlay_buttons(self, kind):
        panel = self.overlay_panel_rect()
        if kind == "win":
            if self.state.has_next_level:
                entries = [("下一关", self.goto_next_level, "primary"),
                           ("重玩本关", self.restart_level, "normal"),
                           ("选择关卡", self.goto_select, "normal")]
            else:
                entries = [("再玩一遍", self.replay_all, "primary"),
                           ("重玩本关", self.restart_level, "normal"),
                           ("选择关卡", self.goto_select, "normal")]
            width, gap = 150, 16
        else:
            entries = [("再试一次", self.restart_level, "primary"),
                       ("选择关卡", self.goto_select, "normal")]
            width, gap = 172, 18

        total = len(entries) * width + (len(entries) - 1) * gap
        x = panel.centerx - total // 2
        y = panel.bottom - 74
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

    def record_note(self, result):
        """结算面板最下面那行：破纪录就报喜，否则显示历史最好成绩。"""
        progress = self.app.progress
        index = self.state.level_index
        if result["better_score"] and result["better_time"]:
            return "新纪录！最高分和最快用时都刷新了", S.COLOR_SUCCESS
        if result["better_score"]:
            return "刷新最高分纪录！", S.COLOR_SUCCESS
        if result["better_time"]:
            return "刷新最快用时纪录！", S.COLOR_SUCCESS
        best = progress.best_seconds(index)
        best_score = score.format_score(progress.best_score(index))
        best_time = score.format_clock(best) if best is not None else "--:--"
        return f"最高分 {best_score} · 最快 {best_time}", S.COLOR_TEXT_FAINT

    def draw_overlay(self, surface):
        win = self.overlay == "win"
        state = self.state
        result = self.result or {"score": 0, "parts": [], "seconds": state.seconds,
                                 "better_score": False, "better_time": False}
        accent = S.COLOR_SUCCESS if win else S.COLOR_DANGER

        dim = pygame.Surface((S.WINDOW_WIDTH, S.WINDOW_HEIGHT))
        dim.set_alpha(S.COLOR_OVERLAY[3])
        dim.fill(S.COLOR_OVERLAY[:3])
        surface.blit(dim, (0, 0))

        panel = self.overlay_panel_rect()
        ui.draw_glow(surface, panel.center, 350, accent, alpha=42, layers=32)
        draw_panel(surface, panel, radius=24, border_color=accent, border_width=2,
                   shadow_alpha=130, shadow_offset=(0, 12))

        self.draw_result_badge(surface, (panel.centerx, panel.y + 70), 32, accent,
                               "win" if win else "lose")

        ui.draw_text_gradient(surface, "通 关 ！" if win else "闯 关 失 败", 44,
                              S.COLOR_TITLE_TOP, accent,
                              (panel.centerx, panel.y + 134), bold=True)

        if win:
            detail = f"第 {state.level_index + 1} 关「{state.name}」已完成"
        else:
            detail = f"失误次数已耗尽（共 {state.max_mistakes} 次）"
        ui.draw_text(surface, detail, 18, S.COLOR_TEXT_DIM, (panel.centerx, panel.y + 180))

        stats = (f"用时 {score.format_clock(result['seconds'])} · "
                 f"剩余失误 {state.mistakes_left} / {state.max_mistakes}")
        ui.draw_text(surface, stats, 18, S.COLOR_TEXT_DIM, (panel.centerx, panel.y + 210))

        if win:
            ui.draw_text_gradient(surface, f"{score.format_score(result['score'])} 分", 40,
                                  S.COLOR_TITLE_TOP, accent,
                                  (panel.centerx, panel.y + 256), bold=True)
            parts = result["parts"]
            if parts:
                ui.draw_text(surface, score.format_parts(parts),
                             14, S.COLOR_TEXT_FAINT, (panel.centerx, panel.y + 292))
            note, note_color = self.record_note(result)
            ui.draw_text(surface, note, 15, note_color, (panel.centerx, panel.y + 320))
        else:
            ui.draw_text(surface, "再试一次，先想清楚哪个箭头能直接飞出去",
                         17, S.COLOR_TEXT_FAINT, (panel.centerx, panel.y + 258))

        for button in self.overlay_buttons:
            button.draw(surface)


def darken_soft(color, amount):
    """ui.darken 的薄封装，让徽章底色不至于全黑。"""
    return ui.mix(color, (10, 12, 20), amount)


# ==================================================================== 选关界面
class SelectScene:
    """按难度分档展示全部关卡，点卡片直接开始；未解锁的关卡显示为灰色。"""

    def __init__(self, app):
        self.app = app
        self.time = 0.0
        self.hover_index = None
        self.cards = select_card_rects(len(LEVELS))
        self.notice_text = ""
        self.notice_timer = 0.0
        cx = S.WINDOW_WIDTH // 2
        self.buttons = [
            Button((cx - 95, 610, 190, 46), "返回主菜单", self.app.goto_start,
                   font_size=19),
        ]

    # ---------------------------------------------------------- 状态
    def is_unlocked(self, index):
        return self.app.progress.is_unlocked(index, S.UNLOCK_ALL_LEVELS)

    def card_index_at(self, pos):
        for index, rect in enumerate(self.cards):
            if rect.collidepoint(pos):
                return index
        return None

    def show_notice(self, text, duration=1.8):
        self.notice_text = text
        self.notice_timer = duration

    # ---------------------------------------------------------- 事件
    def on_escape(self):
        self.app.goto_start()

    def handle_event(self, event):
        for button in self.buttons:
            button.handle_event(event)
        if event.type == pygame.MOUSEMOTION:
            index = self.card_index_at(event.pos)
            self.hover_index = (index if index is not None and self.is_unlocked(index)
                                else None)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            index = self.card_index_at(event.pos)
            if index is not None:
                self.pick(index)

    def pick(self, index):
        if not self.is_unlocked(index):
            self.show_notice("先通关前一关，才能解锁这一关")
            return
        self.app.start_level(index)

    def update(self, dt):
        self.time += dt
        if self.notice_timer > 0:
            self.notice_timer = max(0.0, self.notice_timer - dt)

    # ---------------------------------------------------------- 绘制
    def draw(self, surface):
        cx = S.WINDOW_WIDTH // 2
        ui.draw_text_gradient(surface, "选 择 关 卡", 44, S.COLOR_TITLE_TOP,
                              S.COLOR_TITLE_BOTTOM, (cx, 82), bold=True)
        ui.draw_text(surface, f"共 {len(LEVELS)} 关 · 已通关 "
                              f"{self.app.progress.cleared_count} 关 · "
                              f"总分 {score.format_score(self.app.progress.total_score)}",
                     17, S.COLOR_TEXT_DIM, (cx, 130))
        for index, rect in enumerate(self.cards):
            self.draw_card(surface, index, rect)
        for button in self.buttons:
            button.draw(surface)
        ui.draw_text(surface, "按 Esc 返回主菜单", 16, S.COLOR_TEXT_FAINT, (cx, 730))
        self.draw_notice(surface)

    def draw_card(self, surface, index, rect):
        level = LEVELS[index]
        tier_color = S.TIER_COLORS.get(level.tier, S.COLOR_ACCENT)
        cleared = self.app.progress.is_cleared(index)
        unlocked = self.is_unlocked(index)
        hovered = self.hover_index == index
        accent = S.COLOR_SUCCESS if cleared else tier_color

        if unlocked:
            top, bottom = S.COLOR_PANEL_TOP, S.COLOR_PANEL_BOTTOM
            border = ui.lighten(accent, 0.10)
        else:
            top = ui.mix(S.COLOR_PANEL_TOP, S.COLOR_BG_BOTTOM, 0.55)
            bottom = ui.mix(S.COLOR_PANEL_BOTTOM, S.COLOR_BG_BOTTOM, 0.55)
            border = S.COLOR_PANEL_BORDER
            accent = S.COLOR_TEXT_FAINT

        if hovered:
            ui.draw_glow(surface, rect.center, int(rect.width * 0.60), accent,
                         alpha=40, layers=20)
        ui.draw_shadow(surface, rect, radius=18, spread=12, alpha=90, offset=(0, 6))
        surface.blit(ui.round_rect_surface(rect.size, 18, top, bottom, border, 2,
                                           highlight=True), rect.topleft)

        # 左上角关卡编号
        badge = pygame.Rect(rect.x + 16, rect.y + 14, 34, 34)
        ui.draw_round_rect(surface, badge, accent, 10)
        ui.draw_text(surface, f"{index + 1:02d}", 16,
                     S.COLOR_BG_BOTTOM if unlocked else S.COLOR_PANEL_BOTTOM,
                     badge.center, bold=True)

        # 右上角难度档
        pill_w = ui.text_width(level.tier, 13) + 18
        pill = pygame.Rect(rect.right - 14 - pill_w, rect.y + 21, pill_w, 21)
        ui.draw_round_rect(surface, pill, ui.mix(accent, S.COLOR_BG_BOTTOM, 0.6), 10,
                           accent, 1)
        ui.draw_text(surface, level.tier, 13, accent, pill.center)

        ui.draw_text(surface, level.name, 21,
                     S.COLOR_TEXT if unlocked else S.COLOR_TEXT_FAINT,
                     (rect.centerx, rect.y + 72), bold=True)
        ui.draw_text(surface, f"{level.rows} × {level.cols} · "
                              f"{len(level.arrows)} 个箭头",
                     13, S.COLOR_TEXT_DIM if unlocked else S.COLOR_TEXT_FAINT,
                     (rect.centerx, rect.y + 97))

        if cleared:
            best_time = self.app.progress.best_seconds(index)
            text = f"{score.format_score(self.app.progress.best_score(index))} 分"
            if best_time is not None:
                text += f" · {score.format_clock(best_time)}"
            self.draw_status(surface, rect, text, S.COLOR_SUCCESS, icon="check")
        elif unlocked:
            self.draw_status(surface, rect, "可挑战", S.COLOR_TEXT_DIM)
        else:
            self.draw_status(surface, rect, "未解锁", S.COLOR_TEXT_FAINT, icon="lock")

    @staticmethod
    def draw_status(surface, rect, text, color, icon=None):
        text_w = ui.text_width(text, 13)
        icon_w = 17 if icon else 0
        left = rect.centerx - (text_w + icon_w) / 2
        y = rect.y + 116
        if icon == "check":
            pygame.draw.lines(surface, color, False,
                              [(left, y), (left + 4, y + 5), (left + 12, y - 5)], 2)
        elif icon == "lock":
            draw_lock(surface, (left + 6, y), 16, color)
        ui.draw_text(surface, text, 13, color, (left + icon_w, y), anchor="midleft")

    def draw_notice(self, surface):
        if self.notice_timer <= 0 or not self.notice_text:
            return
        alpha = int(255 * min(1.0, self.notice_timer / 0.4))
        image = ui.font(18, bold=True).render(self.notice_text, True, S.COLOR_WARN)
        pill = image.get_rect().inflate(44, 20)
        pill.center = (S.WINDOW_WIDTH // 2, 686)
        layer = pygame.Surface(pill.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*S.COLOR_BOARD_BOTTOM, min(240, alpha)),
                         layer.get_rect(), border_radius=pill.height // 2)
        pygame.draw.rect(layer, (*S.COLOR_WARN, int(alpha * 0.75)), layer.get_rect(),
                         width=2, border_radius=pill.height // 2)
        image.set_alpha(alpha)
        layer.blit(image, image.get_rect(center=(pill.width // 2, pill.height // 2)))
        surface.blit(layer, pill)
