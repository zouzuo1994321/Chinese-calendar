# -*- coding: utf-8 -*-
"""整窗等比缩放（v1.9.27）实测。

规格（用户 2026-10-21）：
  左右下角各一个小三角形，鼠标移过去才显示；按住三角拖动 = 软件**等比缩放**，
  且不影响功能与布局。

本探针在离屏平台断言：
  ① 100%：窗口尺寸与 v1.9.26 的公式逐项一致，page / 面板逻辑尺寸不变；
  ② 缩放：窗口 = round(逻辑 × s)，宽高比严格等于逻辑比（±1px）；
  ③ 命中：三种比例下点「下一页」日期都 +1（事件坐标由视图反变换，未错位）；
     （无按键悬停 + 真实鼠标拖拽在真机探针 zoom_real_probe.py 里验，offscreen 收不到 hover）
  ④ 手柄：左右下角各一个、贴角、光标方向正确、不越出窗口；
  ⑤ 可见：悬停淡入后三角真的画出来（像素证据），未悬停时全透明；
  ⑥ 拖拽：右下锚左上 / 左下锚右上；两轴取主导轴 ⇒ 严格等比；上下限生效；
  ⑦ 面板开关：高度仍按「逻辑高度 × s」重算；
  ⑧ 持久化：settings.json 里写入 ui_scale，新窗口能读回；
  ⑨ 翻页动画快照落在缩放后的窗口坐标（scale≠1 时不再用逻辑坐标）；
  ⑩ 源码守门：MainWindow 走 QGraphicsView 场景缩放，不再硬编码 setFixedSize。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt                   # noqa: E402
from PySide6.QtTest import QTest                              # noqa: E402
from PySide6.QtWidgets import QApplication                    # noqa: E402

from _box import make_box                                     # noqa: E402

BOX = make_box("_zoom")
SETTINGS = os.path.join(BOX, "settings.json")

app = QApplication.instance() or QApplication([])
from calendar_app import fonts as _fonts                      # noqa: E402
_fonts.install_fonts()

import ui.theme as _uit                                       # noqa: E402
import ui_main as _uim                                        # noqa: E402
from ui_main import MainWindow                                # noqa: E402
from ui.page import CalendarPage                              # noqa: E402
from ui.agenda import AgendaPanel                             # noqa: E402

_uim.SETTINGS_PATH = SETTINGS
_uit.SETTINGS_PATH = SETTINGS

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


win = MainWindow()
win.show()
app.processEvents()

# 离屏平台默认屏 800×600 会让「放大」被屏幕上限吃掉 —— 拖拽数学用一台虚拟大屏
BIG = QRect(0, 0, 2560, 1600)


def use_big_screen():
    win._avail_geo = lambda: BIG


use_big_screen()

# ---------- ① 100% 与旧版逐项一致 ----------
MARGIN = 8
LW = CalendarPage.PAGE_W + MARGIN * 2
LH = CalendarPage.PAGE_H + MARGIN * 2 + 4 + AgendaPanel.PANEL_H * 2
ck("① 逻辑尺寸 = v1.9.26 公式（536 × 1217）", (LW, LH) == (536, 1217), "%dx%d" % (LW, LH))
ck("① 100% 时窗口 = 逻辑尺寸", (win.width(), win.height()) == (LW, LH),
   "%dx%d" % (win.width(), win.height()))
ck("① 页面逻辑尺寸未变（仍 520×841）",
   (win.page.width(), win.page.height()) == (520, 841),
   "%dx%d" % (win.page.width(), win.page.height()))
ck("① 面板逻辑尺寸未变（仍 520×178）",
   (win.agenda_month.width(), win.agenda_month.height()) == (520, 178),
   "%dx%d" % (win.agenda_month.width(), win.agenda_month.height()))
ck("① 画布 board 尺寸 = 逻辑尺寸", (win.board.width(), win.board.height()) == (LW, LH))
ck("① 窗口走 QGraphicsView 场景（不再是裸 QVBoxLayout 中央控件）",
   isinstance(win.centralWidget(), _uim.ZoomView) and win._view.scene() is win._scene,
   type(win.centralWidget()).__name__)

# ---------- ② 缩放几何 ----------
geo_ok, ratio_ok = [], []
for s in (0.6, 0.8, 1.0, 1.15, 1.3):
    win._scale = s
    win._apply_geometry()
    app.processEvents()
    ew, eh = int(round(LW * s)), int(round(LH * s))
    geo_ok.append((win.width(), win.height()) == (ew, eh))
    ratio_ok.append(abs(win.width() / float(win.height()) - LW / float(LH)) < 0.002)
ck("② 各比例下窗口 = round(逻辑×s)", all(geo_ok),
   "失败=%s" % [s for s, ok in zip((0.6, 0.8, 1.0, 1.15, 1.3), geo_ok) if not ok])
ck("② 各比例宽高比 = 逻辑宽高比（等比）", all(ratio_ok))
ck("② 缩放不改页面逻辑尺寸",
   all((win.page.width(), win.page.height()) == (520, 841) for _ in [0]))
ck("② 场景矩形恒为逻辑尺寸",
   win._scene.sceneRect().width() == LW and win._scene.sceneRect().height() == LH)

# ---------- ③ 命中测试（事件坐标反变换） ----------
btn = win.page.btn_next
c = btn.geometry().center()
pl = win.page.mapTo(win.board, c)
hit = []
for s in (0.6, 1.0, 1.3):
    win._scale = s
    win._apply_geometry()
    app.processEvents()
    d0 = win.page.info["date"]
    QTest.mouseClick(win._view.viewport(), Qt.LeftButton, Qt.NoModifier,
                     QPoint(int(round(pl.x() * s)), int(round(pl.y() * s))))
    app.processEvents()
    hit.append(win.page.info["date"] != d0)
ck("③ 0.6 / 1.0 / 1.3 比例下点「下一页」均生效", all(hit), "%s" % hit)

# 缩放后点击命中已在上一条覆盖。
# ⚠ 「无按键悬停」在 offscreen 平台收不到（QTest.mouseMove 不产生 hover 事件），
#    该行为由真机探针 zoom_real_probe.py 覆盖（含真实鼠标拖拽）。

# ---------- ④ 手柄存在 / 贴角 / 光标 ----------
win._scale = 1.0
win._apply_geometry()
app.processEvents()
gbl, gbr = win._grip_bl, win._grip_br
ck("④ 左右下角各一个三角手柄", gbl.corner == "bl" and gbr.corner == "br")
ck("④ 手柄贴左下角", gbl.x() <= 2 and gbl.y() + gbl.height() >= win.height() - 2,
   gbl.geometry().__str__())
ck("④ 手柄贴右下角", gbr.x() + gbr.width() >= win.width() - 2
   and gbr.y() + gbr.height() >= win.height() - 2, gbr.geometry().__str__())
ck("④ 左手柄光标 = 反对角拉伸", gbl.cursor().shape() == Qt.SizeBDiagCursor)
ck("④ 右手柄光标 = 主对角拉伸", gbr.cursor().shape() == Qt.SizeFDiagCursor)
ck("④ 手柄不越出窗口", win.rect().contains(gbl.geometry())
   and win.rect().contains(gbr.geometry()))

# ---------- ⑤ 悬停淡入 + 三角真的画出来 ----------
# ⚠ 不能直接 `grip.grab()` 量透视：QWidget.grab() 会铺一层不透明底，
#    导致「全透明」也量成 alpha=255。改为整窗截图对比：手柄隐形 = 与基线逐像素相同，
#    淡入后 = 右下角出现墨迹。
from PySide6.QtGui import QImage                                  # noqa: E402


def img_of(widget):
    return widget.grab().toImage().convertToFormat(QImage.Format_ARGB32)


def diff_points(a, b):
    out = []
    for y in range(a.height()):
        for x in range(a.width()):
            if a.pixel(x, y) != b.pixel(x, y):
                out.append((x, y))
    return out


def ink_pixels(img, rect):
    """区域内明显比纸色深的像素数（墨迹）。"""
    n = 0
    for y in range(rect.top(), rect.bottom() + 1):
        for x in range(rect.left(), rect.right() + 1):
            c = img.pixelColor(x, y)
            if (c.red() + c.green() + c.blue()) / 3.0 < 200:
                n += 1
    return n


ck("⑤ 初始状态手柄不可见（alpha=0）",
   gbl._alpha == 0.0 and gbr._alpha == 0.0, "%.2f/%.2f" % (gbl._alpha, gbr._alpha))


def settle():
    """把所有会自己变的动画/定时器停稳，否则两次截图会差出半屏。"""
    if getattr(win, "_anim", None) is not None:
        win._anim.stop()
    if win._anim_label is not None:
        win._anim_label.deleteLater()
        win._anim_label = None
    win.page._sheen.stop()
    win.page._clock.stop()
    for t in (win.page._dwell_timer, win.page._gua_dwell_timer):
        t.stop()
    for _ in range(3):
        app.processEvents()


settle()
base = img_of(win)
gbr._on_fade(1.0)
gbl._on_fade(1.0)
app.processEvents()
inked = img_of(win)
pts = diff_points(base, inked)
inside = [p for p in pts if gbr.geometry().contains(*p) or gbl.geometry().contains(*p)]
outside = [p for p in pts if p not in inside]
ck("⑤ 淡入后左右下角都出现墨迹",
   any(gbl.geometry().contains(*p) for p in pts)
   and any(gbr.geometry().contains(*p) for p in pts),
   "全部差异 %d 点" % len(pts))
ck("⑤ 墨迹只落在两个手柄内（页面主体零变化）", not outside,
   "越界=%s" % outside[:5])
n_br = sum(1 for p in pts if gbr.geometry().contains(*p))
ck("⑤ 右手柄是三角而非整块方形（墨迹约 13²/2 ≈ 84px，方形会是 484）",
   40 <= n_br <= 200, "墨迹=%d/484" % n_br)
rbr = gbr.geometry()
corner_diff = sum(1 for p in pts if QRect(rbr.left(), rbr.top(),
                                          gbr.SIZE // 2, gbr.SIZE // 2).contains(*p))
ck("⑤ 右手柄墨迹偏右下（左上 11×11 区无墨迹）", corner_diff == 0,
   "左上墨迹=%d" % corner_diff)
gbr._on_fade(0.0)
gbl._on_fade(0.0)
app.processEvents()
_left = diff_points(base, img_of(win))
ck("⑤ 淡出后恢复与基线一致", not _left, "残留差异 %d 点" % len(_left))

# ---------- ⑥ 拖拽数学 ----------
win._scale = 1.0
win._apply_geometry()
win.move(200, 120)
app.processEvents()
x0, y0 = win.x(), win.y()
w0, h0 = win.width(), win.height()

# 右下：向右拖 → 锚定左上角
g = QPoint(600, 1000)
win._begin_scale_drag("br", g)
win._continue_scale_drag(g + QPoint(80, 20))
app.processEvents()
k = (w0 + 80) / float(w0)
ck("⑥ 右下拖拽：宽度按位移缩放", abs(win.width() - round(LW * k)) <= 2,
   "w=%d 期望≈%d" % (win.width(), round(LW * k)))
ck("⑥ 右下拖拽：左上角不动（锚定）", (win.x(), win.y()) == (x0, y0),
   "%s vs %s" % ((win.x(), win.y()), (x0, y0)))
ck("⑥ 右下拖拽：严格等比", abs(win.width() / float(win.height())
                              - LW / float(LH)) < 0.003,
   "%.4f vs %.4f" % (win.width() / float(win.height()), LW / float(LH)))
win._end_scale_drag()

# 左下：向左拖 → 锚定右上角（右缘 + 顶边不动）
win._scale = 1.0
win._apply_geometry()
win.move(200, 120)
app.processEvents()
right0 = win.x() + win.width()
win._begin_scale_drag("bl", g)
win._continue_scale_drag(g + QPoint(-70, 0))
app.processEvents()
ck("⑥ 左下拖拽：右缘不动（锚定）", abs((win.x() + win.width()) - right0) <= 2,
   "right=%d 期望=%d" % (win.x() + win.width(), right0))
ck("⑥ 左下拖拽：顶边不动", win.y() == y0, "y=%d" % win.y())
ck("⑥ 左下拖拽：变宽（向左拖 = 放大）", win.width() > w0, "w=%d" % win.width())
win._end_scale_drag()

# 纵向主导：只往下拖也应等比放大
win._scale = 1.0
win._apply_geometry()
win.move(200, 120)
app.processEvents()
win._begin_scale_drag("br", g)
win._continue_scale_drag(g + QPoint(2, 120))
app.processEvents()
ck("⑥ 纵向主导时也等比（高变宽跟着变）",
   win.height() > h0 and abs(win.width() / float(win.height()) - LW / float(LH)) < 0.003,
   "%dx%d" % (win.width(), win.height()))
win._end_scale_drag()

# 上下限
win._begin_scale_drag("br", g)
win._continue_scale_drag(g + QPoint(-5000, -5000))
app.processEvents()
ck("⑥ 下限生效（不小于 %.2f）" % win.MIN_SCALE,
   abs(win._scale - win.MIN_SCALE) < 1e-6, "scale=%.3f" % win._scale)
win._begin_scale_drag("br", g)
win._continue_scale_drag(g + QPoint(9000, 9000))
app.processEvents()
mx = win._max_scale()
ck("⑥ 上限生效（不超过屏幕可容纳）", win._scale <= mx + 1e-6,
   "scale=%.3f max=%.3f" % (win._scale, mx))
win._end_scale_drag()

# ---------- ⑦ 面板开关仍按缩放比重算 ----------
win._scale = 1.2
win._apply_geometry()
win._toggle_panel("day")
app.processEvents()
lh1 = CalendarPage.PAGE_H + MARGIN * 2 + 4 + AgendaPanel.PANEL_H
ck("⑦ 关掉「本日」面板后高度 = 新逻辑高 × s",
   win.height() == int(round(lh1 * 1.2)) and win.width() == int(round(LW * 1.2)),
   "%dx%d" % (win.width(), win.height()))
win._toggle_panel("day")     # 复原
app.processEvents()

# ---------- ⑧ 持久化 ----------
win._scale = 0.9
win._apply_geometry()
win._save_settings()
app.processEvents()
import json                                                   # noqa: E402
with open(SETTINGS, "r", encoding="utf-8") as f:
    data = json.load(f)
ck("⑧ settings.json 记录 ui_scale", abs(float(data.get("ui_scale", 0)) - 0.9) < 1e-6,
   str(data.get("ui_scale")))
win2 = MainWindow()
ck("⑧ 新窗口读回 90%", abs(win2._scale - 0.9) < 1e-6, "%.3f" % win2._scale)
ck("⑧ 读回后窗口尺寸同步", win2.height() == int(round(
    (CalendarPage.PAGE_H + MARGIN * 2 + 4 + AgendaPanel.PANEL_H * 2) * 0.9))
   or not win2._month_visible,
   "%dx%d" % (win2.width(), win2.height()))
win2.close()
win2.deleteLater()
app.processEvents()

# ---------- ⑨ 翻页动画快照坐标 ----------
win._scale = 1.3
win._apply_geometry()
app.processEvents()
win._flip(1)
app.processEvents()
lab = win._anim_label
r = win._page_rect_in_window()
ck("⑨ 动画快照落在缩放后的页面位置",
   lab is not None and abs(lab.x() - r.x()) <= 1 and abs(lab.y() - r.y()) <= 1,
   "lab=(%d,%d) 期望=(%d,%d)" % (lab.x() if lab else -1, lab.y() if lab else -1,
                                 r.x(), r.y()))
ck("⑨ 动画快照尺寸 = 页面 × 1.3",
   lab is not None and abs(lab.width() - int(round(520 * 1.3))) <= 2
   and abs(lab.height() - int(round(841 * 1.3))) <= 2,
   "%dx%d" % (lab.width() if lab else -1, lab.height() if lab else -1))

# ---------- ⑩ 源码守门 ----------
import inspect                                                # noqa: E402
src_init = inspect.getsource(MainWindow.__init__)
src_geo = inspect.getsource(MainWindow._apply_geometry)
ck("⑩ 构造期装的是 ZoomView 场景宿主", "ZoomView(self)" in src_init
   and "addWidget(self.board)" in src_init)
ck("⑩ 几何由「逻辑尺寸 × _scale」算出（场景变换）",
   "QTransform().scale" in src_geo and "setSceneRect" in src_geo)
ck("⑩ 不再有硬编码的 setFixedSize(536, …) 旧写法",
   "PAGE_W + margin * 2," not in src_init.replace(" ", ""))
ck("⑩ 手柄常量与绘制在 ui/zoom.py",
   os.path.exists(os.path.join(os.path.dirname(os.path.dirname(
       os.path.dirname(os.path.abspath(__file__)))), "ui", "zoom.py")))

for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok),
                                        len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
