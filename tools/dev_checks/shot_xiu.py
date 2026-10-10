# -*- coding: utf-8 -*-
"""二十八宿星图**交付截图**（页面实时渲染，非手绘示意）。

产物（写到 `docs/screenshots/`，随后由 `verify_ui.py::_embed_xiu_shots()`
base64 内嵌进 README 的「## 🌌 当日二十八宿星图」小节）：
  xiu-panel.png      —— 「颜色」卡 + 右侧星图 全景（3×），对应用户红框处
  xiu-28-sheet.png   —— 28 天逐日渲染的星图区拼图（7×4，3×），一屏看全 28 宿

用法： python tools/dev_checks/shot_xiu.py          # 真机渲染（正常用这个）
       python tools/dev_checks/shot_xiu.py --offscreen   # 仅调试用，图不可交付

⚠ **默认必须真机渲染**：离屏（offscreen）插件**不做字体回退**，而「壁水**獝**」的
  獝 (U+735D) 是宿名用字 62 个里唯一不在内置字体子集内的字 —— 离屏会画成**豆腐块**，
  真机则能回退出真实字形（SimSun 等）。故 offscreen 出的图**不可交付**。
"""
import os
import sys
from datetime import date, timedelta

if "--offscreen" in sys.argv:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
else:
    os.environ.pop("QT_QPA_PLATFORM", None)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from PySide6.QtWidgets import QApplication                      # noqa: E402
from PySide6.QtGui import QImage, QPainter, QColor, QFont       # noqa: E402
from PySide6.QtCore import Qt, QRect                            # noqa: E402

import ui_main                                                   # noqa: E402
from ui_main import CalendarPage                                 # noqa: E402
from calendar_app.engine import get_day_info                     # noqa: E402
from calendar_app.xiu28 import xiu_full_name                     # noqa: E402

app = QApplication(sys.argv)
ui_main.use_builtin_fonts()
win = ui_main.MainWindow()
page = win.page


def render(d):
    page.set_date(d)
    page.zodiac_report = None
    page._sheen_t = 0.0
    page.repaint()
    return page.grab().toImage()


OUT = os.path.join(_ROOT, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)

# ---- ① 全景：颜色卡 + 星图（3×） ----
src = render(date(2026, 10, 10))
CARD = QRect(262, 574, 230, 70)
crop = src.copy(CARD).scaled(CARD.width() * 3, CARD.height() * 3,
                             Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
crop.save(os.path.join(OUT, "xiu-panel.png"))
print("已写 xiu-panel.png", crop.size())

# ---- ② 28 天星图区拼图（7×4，3×） ----
# v1.9.24 星图改为素材贴图（图形区 = 格宽 77 × 49 行，落在栏顶下方），切片按
# 「卡片内区」取：上自卡片上框线下方（575）、下到卡片下框线之前（639），左右避开
# 卡片自身的框线（x 489..490）—— 这样拼图里只剩星图与宿名，也不含卡框线。
R = CalendarPage.XIU_RECT
CROP = QRect(R.left() - 6, R.top() - 9, 84, 65)
SC = 3
COLS, ROWS = 7, 4
GAP, LBL_H = 6, 16
CW, CH = CROP.width() * SC, CROP.height() * SC
ROW_H = CH + LBL_H
W, H = COLS * CW + (COLS + 1) * GAP, ROWS * ROW_H + (ROWS + 1) * GAP
sheet = QImage(W, H, QImage.Format_ARGB32)
sheet.fill(QColor("#f2efe6"))
p = QPainter(sheet)
p.setRenderHint(QPainter.Antialiasing, True)

start = date(2026, 10, 10)
for k in range(28):
    d = start + timedelta(days=k)
    pageimg = render(d)
    cell = pageimg.copy(CROP).scaled(CW, CH, Qt.IgnoreAspectRatio,
                                     Qt.SmoothTransformation)
    cy, cx = k // COLS, k % COLS
    x = GAP + cx * (CW + GAP)
    y = GAP + cy * (ROW_H + GAP)
    p.drawImage(x, y, cell)
    p.setPen(QColor("#9a9a9a"))
    p.setFont(QFont(ui_main.ZH_FONT[0], 10))
    p.drawText(QRect(x, y + CH, CW, LBL_H), Qt.AlignCenter,
               "%d/%d" % (d.month, d.day))
p.end()
sheet.save(os.path.join(OUT, "xiu-28-sheet.png"))
print("已写 xiu-28-sheet.png", sheet.size())

# ---- 控制台核对：28 天宿名 ----
print("\n2026-10-10 起 28 天宿名：")
names = []
for k in range(28):
    d = start + timedelta(days=k)
    i = get_day_info(d)
    names.append(xiu_full_name(i["xiu"], i["xiu_zheng"], i["xiu_animal"]))
print("  " + " ".join(names))
print("  唯一 %d / 28" % len(set(names)))
