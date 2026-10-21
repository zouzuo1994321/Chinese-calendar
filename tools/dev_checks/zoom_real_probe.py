# -*- coding: utf-8 -*-
"""真机探针：整窗等比缩放（v1.9.27）—— 真实鼠标悬停与拖拽。

离屏探针（zoom_probe.py）只能验几何与数学；offscreen 平台**收不到无按键悬停**
（QTest.mouseMove 不产生 hover 事件），也拖不动真实鼠标。所以这几条必须真机：

  ① 页面悬停仍工作：光标移到「今日卦象」框 → page._hover_gua 为 True；
     移到建议卡 → page._hover_advice_key 命中（证明场景代理没有掐断 hover）；
  ② 手柄悬停淡入 / 离开淡出（alpha 0 → 1 → 0）；
  ③ **按住右下三角真实拖动** → 窗口等比放大、宽高比 = 逻辑比、左上角不动；
  ④ **按住左下三角真实拖动** → 窗口等比放大、右缘不动；
  ⑤ 标题行拖窗仍可用（缩放宿主没有抢掉页面自己的拖动分支）；
  ⑥ 拖拽后 settings.json 写入 ui_scale（沙盒路径，不污染工程根）。

⚠ 必须真机（脚本内 pop 掉 QT_QPA_PLATFORM）；会显示窗口并移动鼠标约 12 秒。
⚠ 注入要点（见 SKILL「真实鼠标拖动验收」）：位移必须在**独立线程**里逐步注入，
   主线程负责泵消息，且左键要一直按住 —— 否则窗口一动不动。
"""
import ctypes
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.pop("QT_QPA_PLATFORM", None)              # 必须真实平台

from PySide6.QtWidgets import QApplication                           # noqa: E402

from _box import make_box                                            # noqa: E402

BOX = make_box("_zoom_real")
SETTINGS = os.path.join(BOX, "settings.json")

app = QApplication.instance() or QApplication([])
if app.platformName() in ("offscreen", "minimal", "vnc"):
    print("平台插件 = %s（需要真实平台，跳过）" % app.platformName())
    sys.exit(2)

from calendar_app import fonts as _fonts                             # noqa: E402
_fonts.install_fonts()

import ui.theme as _uit                                              # noqa: E402
import ui_main as _uim                                               # noqa: E402

_uim.SETTINGS_PATH = SETTINGS
_uit.SETTINGS_PATH = SETTINGS

from ui_main import MainWindow                                       # noqa: E402

user32 = ctypes.windll.user32
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


def pump(sec):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.008)


win = MainWindow()
win._scale = 0.85                     # 先缩小，保证整窗落在 1080p 屏幕内可拖
win._apply_geometry()
win.move(260, 40)
win.show()
pump(1.0)
hwnd = int(win.winId())
user32.SetForegroundWindow(hwnd)
pump(0.4)


def page_global(lx, ly):
    """页面逻辑坐标 → 屏幕坐标。"""
    s = win._scale
    tl = win.mapToGlobal(win._page_rect_in_window().topLeft())
    return (tl.x() + int(round(lx * s)), tl.y() + int(round(ly * s)))


def hover(lx, ly):
    """真实移动光标（连挪两次：首个移动只用于进入窗口，Qt 不会当 hover 派发）。"""
    x, y = page_global(lx, ly)
    user32.SetCursorPos(x, y)
    pump(0.25)
    user32.SetCursorPos(x + 1, y + 1)
    pump(0.30)


# ---------- ① 页面悬停 ----------
g = win.page.GUA_RECT
hover(g.center().x(), g.center().y())
ck("① 页面「今日卦象」框悬停命中", bool(win.page._hover_gua),
   "hover_gua=%s scale=%.2f" % (win.page._hover_gua, win._scale))

advs = win.page._advice_rects()
if advs:
    a = advs[0][1]
    hover(a.center().x(), a.center().y())
    ck("① 建议卡悬停命中（场景代理未掐断 hover）",
       win.page._hover_advice_key == advs[0][0],
       "hover=%r" % (win.page._hover_advice_key,))

# ---------- ② 手柄悬停淡入 / 淡出 ----------
br = win._grip_br
bl = win._grip_bl
c0 = win.mapToGlobal(br.geometry().center())
user32.SetCursorPos(c0.x(), c0.y())
pump(0.55)
ck("② 右下三角悬停淡入", br._alpha > 0.9 and br.underMouse(),
   "alpha=%.2f" % br._alpha)
c1 = win.mapToGlobal(bl.geometry().center())
user32.SetCursorPos(c1.x(), c1.y())
pump(0.55)
ck("② 左下三角悬停淡入", bl._alpha > 0.9 and bl.underMouse(),
   "alpha=%.2f" % bl._alpha)
ck("② 右下三角已淡出", br._alpha < 0.3, "alpha=%.2f" % br._alpha)


# ---------- ③④ 真实拖拽手柄 = 等比缩放 ----------
def drag_from(screen_pt, dx, dy, hold=1.9):
    """在 screen_pt 按下左键，线程里分步注入 (dx,dy)，主线程泵消息。"""
    def driver():
        time.sleep(0.45)
        steps = 24
        for i in range(1, steps + 1):
            user32.SetCursorPos(screen_pt[0] + dx * i // steps,
                                screen_pt[1] + dy * i // steps)
            time.sleep(0.02)
        time.sleep(0.22)
        user32.mouse_event(0x0004, 0, 0, 0, 0)      # LEFTUP

    user32.SetCursorPos(*screen_pt)
    pump(0.35)
    th = threading.Thread(target=driver, daemon=True)
    th.start()
    user32.mouse_event(0x0002, 0, 0, 0, 0)          # LEFTDOWN
    pump(hold)
    th.join(timeout=2.0)


def geom():
    return (win.x(), win.y(), win.width(), win.height())


LWR = win._logical_size()

# ③ 右下：向右下拖 110px
win._scale = 0.85
win._apply_geometry()
win.move(260, 40)
pump(0.6)
x0, y0, w0, h0 = geom()
cbr = win.mapToGlobal(br.geometry().center())
drag_from((cbr.x(), cbr.y()), 110, 0)
pump(0.4)
x1, y1, w1, h1 = geom()
ck("③ 按住右下三角拖动 → 窗口变大", w1 > w0 + 40, "%dx%d → %dx%d" % (w0, h0, w1, h1))
ck("③ 缩放严格等比", abs(w1 / float(h1) - LWR[0] / float(LWR[1])) < 0.004,
   "%.4f vs %.4f" % (w1 / float(h1), LWR[0] / float(LWR[1])))
ck("③ 左上角不动（锚定）", (x1, y1) == (x0, y0), "%s → %s" % ((x0, y0), (x1, y1)))
ck("③ 缩放比已更新且写入设置",
   abs(win._scale - w1 / float(LWR[0])) < 0.01 and os.path.exists(SETTINGS),
   "scale=%.3f" % win._scale)

# ④ 左下：向左拖 90px → 变大且右缘不动
win._scale = 0.85
win._apply_geometry()
win.move(260, 40)
pump(0.6)
x0, y0, w0, h0 = geom()
right0 = x0 + w0
cbl = win.mapToGlobal(bl.geometry().center())
drag_from((cbl.x(), cbl.y()), -90, 0)
pump(0.4)
x1, y1, w1, h1 = geom()
ck("④ 按住左下三角拖动 → 窗口变大", w1 > w0 + 30, "%dx%d → %dx%d" % (w0, h0, w1, h1))
ck("④ 右缘不动（锚定）", abs((x1 + w1) - right0) <= 2,
   "right %d → %d" % (right0, x1 + w1))
ck("④ 顶边不动", y1 == y0, "y %d → %d" % (y0, y1))
ck("④ 左下缩放同样严格等比",
   abs(w1 / float(h1) - LWR[0] / float(LWR[1])) < 0.004,
   "%.4f" % (w1 / float(h1)))

# ---------- ⑤ 标题行拖动窗口仍可用 ----------
win._scale = 0.85
win._apply_geometry()
win.move(260, 40)
pump(0.6)
x0, y0 = win.x(), win.y()
t = win.page.TITLE_RECT.center()
tx, ty = page_global(t.x(), t.y())
drag_from((tx, ty), 0, 70)
pump(0.4)
ck("⑤ 标题行拖动窗口仍可用（未被缩放宿主抢掉）",
   abs(win.y() - y0) > 30 and abs(win.x() - x0) <= 3,
   "y %d → %d（位移 %d）" % (y0, win.y(), win.y() - y0))
ck("⑤ 拖动窗口不改变缩放比", abs(win._scale - 0.85) < 0.02, "%.3f" % win._scale)

user32.SetCursorPos(40, 40)
pump(0.3)
win.close()
pump(0.2)

for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok),
                                        len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
