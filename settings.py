# -*- coding: utf-8 -*-
"""全局配置：窗口尺寸、布局参数、配色方案、字体候选。

所有可调项集中在这里，后续想换配色或改布局不必翻业务代码。
"""

# ------------------------------------------------------------------ 窗口
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 760
WINDOW_TITLE = "一箭又一箭 · Arrow Escape"
FPS = 60

# ------------------------------------------------------------------ 布局
TOP_BAR_HEIGHT = 96          # 顶部信息栏高度
BOTTOM_BAR_HEIGHT = 66       # 底部提示栏高度
BOARD_MARGIN_X = 44          # 棋盘区域左右留白
BOARD_MARGIN_TOP = 16        # 信息栏与棋盘之间的间距
BOARD_MARGIN_BOTTOM = 18     # 棋盘与提示栏之间的间距
BOARD_PADDING = 14           # 棋盘外框与格子之间的留白
CELL_GAP = 8                 # 格子之间的视觉缝隙
ARROW_SCALE = 1.25           # 箭头图形相对格子边长的缩放

# ------------------------------------------------------------------ 配色
COLOR_BG_TOP = (24, 27, 43)
COLOR_BG_BOTTOM = (15, 17, 29)

COLOR_TOP_BAR = (33, 37, 58)
COLOR_TOP_BAR_LINE = (52, 58, 90)

COLOR_BOARD_BG = (36, 41, 66)
COLOR_BOARD_BORDER = (62, 70, 108)
COLOR_CELL_BG = (45, 51, 80)
COLOR_CELL_BG_ALT = (41, 47, 74)

COLOR_PANEL = (30, 34, 54)
COLOR_PANEL_BORDER = (54, 61, 94)

COLOR_CHIP_BG = (26, 30, 48)
COLOR_CHIP_BORDER = (54, 61, 94)

COLOR_TEXT = (235, 239, 250)
COLOR_TEXT_DIM = (150, 160, 192)
COLOR_TEXT_FAINT = (106, 115, 148)

COLOR_ACCENT = (98, 200, 245)
COLOR_ACCENT_DARK = (46, 118, 162)
COLOR_WARN = (245, 178, 84)
COLOR_DANGER = (238, 110, 120)
COLOR_DANGER_DARK = (150, 58, 70)
COLOR_SUCCESS = (104, 214, 154)

COLOR_BTN_BG = (58, 66, 104)
COLOR_BTN_BG_HOVER = (78, 88, 136)
COLOR_BTN_BG_DOWN = (44, 51, 82)
COLOR_BTN_BORDER = (88, 98, 148)
COLOR_BTN_TEXT = (232, 237, 250)

COLOR_OVERLAY = (10, 12, 22, 200)

# 箭头颜色：按方向区分，方便肉眼分辨（想统一成单色改这里即可）
ARROW_COLORS = {
    "up": (92, 190, 240),
    "down": (248, 173, 85),
    "left": (108, 212, 156),
    "right": (240, 122, 132),
}

# ------------------------------------------------------------------ 开发开关
# True：允许 F1 / F2 直接预览通关、失败界面，并在底部显示"界面阶段"提示。
# 后续接入游戏逻辑后把它改成 False 即可隐藏提示。
DEV_PREVIEW = True
