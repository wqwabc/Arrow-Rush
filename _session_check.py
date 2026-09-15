# -*- coding: utf-8 -*-
"""临时工具：校验单局存档（保存 / 续关 / 失效处理）+ 全功能回归。用完即删。"""
import json
import os
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

import scenes  # noqa: E402
import settings as S  # noqa: E402
from levels import LEVELS  # noqa: E402
from main import App  # noqa: E402
from progress import Progress  # noqa: E402
from session import Session, decode_arrows, encode_arrows  # noqa: E402

failures = []


def check(label, condition):
    print(("  OK   " if condition else "  FAIL ") + label)
    if not condition:
        failures.append(label)


tmp_dir = tempfile.gettempdir()
save_tmp = os.path.join(tmp_dir, "arrow_session.json")
prog_tmp = os.path.join(tmp_dir, "arrow_session_progress.json")
for path in (save_tmp, prog_tmp):
    if os.path.exists(path):
        os.remove(path)

# ============================================================ 1. 编解码
print("存档编解码")
arrows = {(0, 2): "up", (3, 1): "left", (5, 4): "down"}
back = decode_arrows(encode_arrows(arrows))
check("箭头编解码可逆", back == arrows)
check("键是字符串（JSON 要求）", all(isinstance(k, str) for k in encode_arrows(arrows)))
check("非法方向被丢弃", decode_arrows({"1,1": "斜着"}) == {})
check("非法键被丢弃", decode_arrows({"垃圾": "up", "1": "up", "a,b": "up"}) == {})
check("负数坐标被丢弃", decode_arrows({"-1,2": "up"}) == {})
check("非字典输入返回空", decode_arrows("nope") == {})

# ============================================================ 2. 存取
print("存档读写")
sess = Session(save_tmp)
check("初始没有存档", sess.exists is False)
sess.save(level=3, arrows=arrows, mistakes=1, elapsed=42.5,
          hints_left=2, undos_left=3,
          history=[{"kind": "launch", "cell": (0, 2), "direction": "up"},
                   {"kind": "block", "cell": (3, 1)}])
check("保存后有存档", sess.exists is True)
check("内存里的箭头保持元组坐标", sess.data["arrows"] == arrows)

reload = Session(save_tmp).load()
check("能读回关卡序号", reload.data["level"] == 3)
check("能读回箭头布局", reload.data["arrows"] == arrows)
check("能读回失误数", reload.data["mistakes"] == 1)
check("能读回用时", abs(reload.data["elapsed"] - 42.5) < 1e-6)
check("能读回提示/撤销次数",
      reload.data["hints_left"] == 2 and reload.data["undos_left"] == 3)
check("能读回操作历史", reload.data["history"] == [
    {"kind": "launch", "cell": (0, 2), "direction": "up"},
    {"kind": "block", "cell": (3, 1)}])

sess.clear()
check("清除后没有存档", sess.exists is False)
check("清除后文件也没了", not os.path.exists(save_tmp))

# ============================================================ 3. 坏存档
print("坏存档容错")
for label, content in (
        ("不是合法 JSON", "{ 坏掉了"),
        ("不是对象", "[1, 2, 3]"),
        ("缺字段", '{"level": 3}'),
        ("箭头为空", '{"level": 3, "arrows": {}}'),
        ("关卡号为负", '{"level": -5, "arrows": {"1,1": "up"}}'),
        ("箭头字段是垃圾", '{"level": 3, "arrows": "nope"}'),
        ("数字字段是垃圾",
         '{"level": 3, "arrows": {"1,1": "up"}, "mistakes": "很多"}'),
):
    with open(save_tmp, "w", encoding="utf-8") as fh:
        fh.write(content)
    broken = Session(save_tmp).load()
    check(f"{label} → 视为没有存档", broken.exists is False)

with open(save_tmp, "w", encoding="utf-8") as fh:
    fh.write('{"level": 3, "arrows": {"1,1": "up", "坏": "x"},'
             ' "mistakes": -2, "elapsed": -5, "hints_left": 99, "undos_left": 99}')
salvaged = Session(save_tmp).load()
check("部分损坏时能救回可信的部分",
      salvaged.exists and salvaged.data["arrows"] == {(1, 1): "up"})
check("负数被夹到 0",
      salvaged.data["mistakes"] == 0 and salvaged.data["elapsed"] == 0.0)

# ============================================================ 4. 续关流程
print("续关流程")
os.remove(save_tmp)
app = App()
app.progress = Progress(prog_tmp)
app.session = Session(save_tmp)
app.session.load()
app.backdrop.update(6.0)

check("新开局没有存档", app.session.exists is False)
check("主菜单按钮：开始游戏 / 选择关卡 / 退出游戏",
      [b.label for b in app.scene.buttons]
      == ["开 始 游 戏", "选择关卡", "退出游戏"])

app.start_level(6)
scene = app.scene
check("开始关卡后立刻写了一次存档", app.session.exists is True)
check("存档里记的是这一关", app.session.data["level"] == 6)
check("存档里的箭头数与本关一致",
      len(app.session.data["arrows"]) == len(LEVELS[6].arrows))

# 打几步再改状态
order = sorted(app.state.arrows)
plays = app.state.free_arrows()[:3]
for cell in plays:
    scene.resolve_click(cell)
    scene.update(1 / 60)
blocked = next(c for c in sorted(app.state.arrows) if not app.state.can_leave(*c))
scene.resolve_click(blocked)
scene.update(0.7)
scene.use_hint()
scene.update(1 / 60)
scene.resolve_click(app.state.free_arrows()[0])
scene.update(1 / 60)
scene.undo()

expect_arrows = dict(app.state.arrows)
expect_mistakes = app.state.mistakes
expect_hints = scene.hints_left
expect_undos = scene.undos_left
expect_history = list(scene.history)
expect_elapsed = app.state.elapsed

check("存档随每次操作更新", app.session.data["arrows"] == expect_arrows
      and app.session.data["mistakes"] == expect_mistakes)

# 模拟关掉游戏再打开
app2 = App()
app2.progress = Progress(prog_tmp)
app2.session = Session(save_tmp).load()
check("重开后读到存档", app2.session.exists is True)
app2.scene = scenes.StartScene(app2)
check("主菜单出现「继续第 7 关」按钮",
      app2.scene.buttons[0].label == "继续第 7 关")

app2.continue_game()
check("续关进入正确的关卡", app2.state.level_index == 6)
check("续关后盘面完全还原", app2.state.arrows == expect_arrows)
check("续关后失误数还原", app2.state.mistakes == expect_mistakes)
check("续关后提示次数还原", app2.scene.hints_left == expect_hints)
check("续关后撤销次数还原", app2.scene.undos_left == expect_undos)
check("续关后操作历史还原", app2.scene.history == expect_history)
check("续关后用时接着走", abs(app2.state.elapsed - expect_elapsed) < 0.001)
check("续关后计时没被停掉", app2.state.final_time is None)

# 续关后撤销仍然可用
if app2.scene.undos_left > 0 and app2.scene.history:
    last = app2.scene.history[-1]
    before = dict(app2.state.arrows)
    app2.scene.undo()
    if last["kind"] == "launch":
        check("续关后撤销能把箭头放回来",
              last["cell"] in app2.state.arrows and app2.state.arrows != before)
    else:
        check("续关后撤销能退回失误", app2.state.mistakes == expect_mistakes - 1)

# ============================================================ 5. 存档失效
print("存档失效场景")
app3 = App()
app3.progress = Progress(prog_tmp)
app3.session = Session(save_tmp).load()
app3.backdrop.update(6.0)
app3.start_level(2)
check("直接选关会覆盖旧存档", app3.session.data["level"] == 2)

app3.start_new_game()
check("点「新游戏」会先清档再写新档", app3.session.exists
      and app3.session.data["level"] == app3.progress.next_level_to_play(len(LEVELS)))

# 通关后存档清掉
app3.start_level(0)
scene = app3.scene
while app3.state.arrows:
    cell = app3.state.hint()
    scene.resolve_click(cell)
    scene.update(1 / 60)
for _ in range(150):
    scene.update(1 / 60)
check("通关后单局存档被清掉", app3.session.exists is False)
check("通关成绩仍然记在 progress 里", app3.progress.best_score(0) > 0)

# 失败后存档也清掉
app3.start_level(1)
scene = app3.scene
check("重新开始关卡后又有存档", app3.session.exists is True)
blocked = next(c for c in sorted(app3.state.arrows) if not app3.state.can_leave(*c))
while app3.state.mistakes < app3.state.max_mistakes:
    scene.resolve_click(blocked)
    scene.update(0.7)
check("失败后单局存档被清掉", app3.session.exists is False)

# 结算面板打开时不写档
app3.start_level(3)
scene = app3.scene
app3.session.clear()
scene.open_overlay("win")
scene.save_progress()
check("已结算的关卡不会写单局存档", app3.session.exists is False)

# 全通关后主菜单回到「开始游戏」
app3.progress.cleared = set(range(12))
app3.progress.save()
app3.session.clear()
app3.goto_start()
check("没有存档时主菜单显示「开始游戏」",
      app3.scene.buttons[0].label == "开 始 游 戏")
check("全部通关后「开始游戏」回到第 1 关",
      app3.progress.next_level_to_play(len(LEVELS)) == 0)

# ============================================================ 6. 渲染
print("渲染截图")
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_shots")
os.makedirs(out_dir, exist_ok=True)


def render(target, name):
    target.scene.update(0.016)
    target.backdrop.draw(target.screen)
    target.scene.draw(target.screen)
    pygame.image.save(target.screen, os.path.join(out_dir, name + ".png"))


app3.start_level(4)                 # 先真正产生一份存档
app3.scene.resolve_click(app3.state.free_arrows()[0])
app3.scene.update(1 / 60)
app3.goto_start()
check("有存档时主菜单显示「继续」按钮",
      app3.scene.buttons[0].label.startswith("继续第"))
render(app3, "start_with_save")

app4 = App()
app4.progress = Progress(prog_tmp)
app4.session = Session(save_tmp)
app4.session.clear()
app4.backdrop.update(6.0)
app4.goto_start()
render(app4, "start_no_save")

app3.continue_game()
app3.scene.update(0.016)
render(app3, "playing")

for path in (save_tmp, prog_tmp):
    if os.path.exists(path):
        os.remove(path)
pygame.quit()
print("\n全部通过" if not failures else f"\n失败 {len(failures)} 项: {failures}")
raise SystemExit(1 if failures else 0)
