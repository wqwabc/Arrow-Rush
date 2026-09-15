# -*- coding: utf-8 -*-
"""全局配置：窗口尺寸、布局参数、配色方案、开发开关。

所有可调项集中在这里，后续想换配色或改布局不必翻业务代码。
颜色命名规律：COLOR_XXX_TOP / _BOTTOM 表示竖向渐变的上下两端。
"""

# ------------------------------------------------------------------ 窗口
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 760
WINDOW_TITLE = "一箭又一箭 · Arrow Escape"
FPS = 60

# ------------------------------------------------------------------ 布局
TOP_BAR_HEIGHT = 96          # 顶部信息栏高度
BOTTOM_BAR_HEIGHT = 72       # 底部提示栏高度
BOARD_MARGIN_X = 44          # 棋盘区域左右留白
BOARD_MARGIN_TOP = 16        # 信息栏与棋盘之间的间距
BOARD_MARGIN_BOTTOM = 14     # 棋盘与提示栏之间的间距
BOARD_PADDING = 16           # 棋盘外框与格子之间的留白
CELL_GAP = 8                 # 格子之间的视觉缝隙
ARROW_SCALE = 1.20           # 箭头图形相对格子边长的缩放

# 缓浮粒子
PARTICLE_COUNT = 46

# ------------------------------------------------------------------ 背景
COLOR_BG_TOP = (26, 30, 48)
COLOR_BG_BOTTOM = (13, 15, 26)
COLOR_BG_GLOW = (78, 150, 210)       # 背景大光晕的色调

# ------------------------------------------------------------------ 顶部信息栏
COLOR_TOP_BAR_TOP = (41, 46, 72)
COLOR_TOP_BAR_BOTTOM = (28, 32, 51)
COLOR_TOP_BAR_LINE = (66, 78, 122)

# ------------------------------------------------------------------ 棋盘
COLOR_BOARD_TOP = (44, 50, 78)
COLOR_BOARD_BOTTOM = (32, 37, 58)
COLOR_BOARD_BORDER = (74, 84, 128)
COLOR_BOARD_WELL_TOP = (21, 25, 40)
COLOR_BOARD_WELL_BOTTOM = (28, 33, 51)
COLOR_BOARD_WELL_EDGE = (58, 66, 100)
COLOR_TILE_TOP = (63, 71, 105)
COLOR_TILE_BOTTOM = (46, 52, 80)
COLOR_TILE_EDGE = (78, 88, 128)
COLOR_TILE_HOVER_TOP = (82, 94, 138)
COLOR_TILE_HOVER_BOTTOM = (60, 69, 104)

# ------------------------------------------------------------------ 面板 / 卡片
COLOR_PANEL_TOP = (37, 42, 66)
COLOR_PANEL_BOTTOM = (27, 31, 48)
COLOR_PANEL_BORDER = (62, 71, 108)

COLOR_CHIP_TOP = (34, 39, 61)
COLOR_CHIP_BOTTOM = (24, 28, 44)
COLOR_CHIP_BORDER = (60, 69, 104)

# ------------------------------------------------------------------ 文字
COLOR_TEXT = (235, 239, 250)
COLOR_TEXT_DIM = (152, 162, 194)
COLOR_TEXT_FAINT = (108, 117, 150)

COLOR_TITLE_TOP = (255, 255, 255)
COLOR_TITLE_BOTTOM = (150, 186, 226)

# ------------------------------------------------------------------ 强调色
COLOR_ACCENT = (98, 200, 245)
COLOR_ACCENT_DARK = (44, 112, 156)
COLOR_WARN = (245, 178, 84)
COLOR_DANGER = (240, 112, 122)
COLOR_DANGER_DARK = (146, 54, 66)
COLOR_SUCCESS = (104, 214, 154)
COLOR_SUCCESS_DARK = (42, 116, 82)

# ------------------------------------------------------------------ 按钮
COLOR_BTN_TOP = (66, 75, 116)
COLOR_BTN_BOTTOM = (48, 55, 88)
COLOR_BTN_BORDER = (92, 103, 155)
COLOR_BTN_TEXT = (234, 239, 251)

COLOR_BTN_PRIMARY_TOP = (62, 148, 200)
COLOR_BTN_PRIMARY_BOTTOM = (36, 96, 138)
COLOR_BTN_PRIMARY_BORDER = (118, 210, 250)

COLOR_BTN_DANGER_TOP = (186, 72, 84)
COLOR_BTN_DANGER_BOTTOM = (132, 46, 58)
COLOR_BTN_DANGER_BORDER = (240, 132, 142)

COLOR_OVERLAY = (8, 10, 18, 205)

# 箭头颜色：按方向区分，方便肉眼分辨（想统一成单色改这里即可）
ARROW_COLORS = {
    "up": (92, 190, 240),
    "down": (248, 173, 85),
    "left": (108, 212, 156),
    "right": (240, 122, 132),
}

# ------------------------------------------------------------------ 关卡选择
# True：一开局所有关卡都能选（方便跳着试玩 / 验收）。
# False：按顺序解锁，通关前一关才开放下一关。
UNLOCK_ALL_LEVELS = False

# 难度档配色，键要和 levels.TIERS 里的档位名一致
TIER_COLORS = {
    "入门": (104, 214, 154),
    "进阶": (98, 200, 245),
    "挑战": (246, 146, 96),
}

# ------------------------------------------------------------------ 计时与计分
# 本关得分 = 基础分 + 速度奖励 + 失误奖励
SCORE_BASE = 800                 # 每关基础分
SCORE_PER_DIFFICULTY = 12        # 难度分每 1 点折算的基础分
SCORE_TIME_RATE = 15             # 比目标用时每快 1 秒加多少分
SCORE_TARGET_PER_ARROW = 4.5     # 目标用时 = 箭头数 × 这个系数（秒）
SCORE_PER_SPARE_MISTAKE = 80     # 每剩余一次失误加多少分

COLOR_TIME = (170, 162, 250)     # 用时胶囊的强调色

# ------------------------------------------------------------------ 提示
HINTS_PER_LEVEL = 3              # 每关可用提示次数
SCORE_HINT_PENALTY = 150         # 每用一次提示扣多少分
HINT_SECONDS = 10.0              # 提示高亮持续多久

COLOR_HINT = (255, 212, 96)      # 提示的金色

# ------------------------------------------------------------------ 撤销
UNDOS_PER_LEVEL = 3              # 每关可用撤销次数
SCORE_UNDO_PENALTY = 100         # 每用一次撤销扣多少分

COLOR_UNDO = (146, 206, 255)     # 撤销的浅蓝
