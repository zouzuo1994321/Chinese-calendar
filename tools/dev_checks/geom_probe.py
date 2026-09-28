# -*- coding: utf-8 -*-
"""几何精确量测：单独渲染龙凤/云纹，量测墨迹包围盒，验证对齐（不受缺字环境干扰）。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from datetime import date
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from calendar_app.engine import get_day_info
from ui_main import CalendarPage, MainWindow, palette_for

app = QApplication(sys.argv)
win = MainWindow()
page = win.page

print("可用字体族数量 =", len(QFontDatabase.families()))
for f in ("Arial", "Georgia", "Rockwell", "SimSun", "Microsoft YaHei"):
    print("  字体 %-18s 存在=%s" % (f, f in QFontDatabase.families()))

RED = date(2026, 9, 27)
page.info = get_day_info(RED)
page.P = palette_for(page.info)


def ink_bbox(pm, x0, y0, x1, y1, bg=(250, 248, 240), tol=6):
    """返回区域内非背景墨迹的包围盒。"""
    img = pm.toImage()
    minx, miny, maxx, maxy, n = 10 ** 9, 10 ** 9, -1, -1, 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            c = img.pixelColor(x, y)
            if (abs(c.red() - bg[0]) > tol or abs(c.green() - bg[1]) > tol
                    or abs(c.blue() - bg[2]) > tol):
                n += 1
                minx = min(minx, x); maxx = max(maxx, x)
                miny = min(miny, y); maxy = max(maxy, y)
    return (minx, miny, maxx, maxy, n)


def blank():
    pm = QPixmap(520, 848)
    pm.fill(QColor(250, 248, 240))
    return pm


# ---- 只画龙凤 ----
pm = blank()
q = QPainter(pm)
q.setRenderHint(QPainter.SmoothPixmapTransform)
page._paint_dragon_phoenix(q)
q.end()

LR = ink_bbox(pm, 0, 0, 262, 848)      # 左（龙）
RR = ink_bbox(pm, 262, 0, 520, 848)    # 右（凤）
NUM = CalendarPage.NUM_RECT
cy = NUM.y() + NUM.height() // 2
print("\nNUM_RECT =", NUM, " 数字中心 y =", cy)
print("龙 墨迹包围盒 (x0,y0,x1,y1,n) =", LR, " 竖向中心 = %.1f" % ((LR[1] + LR[3]) / 2.0))
print("凤 墨迹包围盒 (x0,y0,x1,y1,n) =", RR, " 竖向中心 = %.1f" % ((RR[1] + RR[3]) / 2.0))
print("龙 高度 =", LR[3] - LR[1] + 1, " 凤 高度 =", RR[3] - RR[1] + 1)
print("龙 右缘 =", LR[2], "（锚点 198）    凤 左缘 =", RR[0], "（锚点 322）")

# ---- 只画云纹 ----
pm2 = blank()
q2 = QPainter(pm2)
page._paint_cloud(q2)
q2.end()
CL = ink_bbox(pm2, 0, 280, 260, 330)
CR = ink_bbox(pm2, 260, 280, 520, 330)
print("\n云纹 左 墨迹 =", CL, "  右 墨迹 =", CR)
print("页面宽 =", page.PAGE_W)

# ---- 数字是否能渲染（判断是否缺字） ----
pm3 = blank()
q3 = QPainter(pm3)
q3.setPen(QColor(198, 40, 40))
from PySide6.QtGui import QFont
q3.setFont(QFont("Arial", 120))
q3.drawText(60, 300, "27")
q3.end()
print("\n[Arial 120px 画 '27'] 墨迹 =", ink_bbox(pm3, 0, 0, 520, 400))

ok = True
for tag, bb, exp_h in (("龙", LR, 168), ("凤", RR, 168)):
    c = (bb[1] + bb[3]) / 2.0
    good = abs(c - cy) <= 2 and abs((bb[3] - bb[1] + 1) - exp_h) <= 6
    ok &= good
    print("%s 竖直居中对齐数字中心: %s (中心 %.1f vs %d，高 %d)"
          % (tag, "OK" if good else "偏差", c, cy, bb[3] - bb[1] + 1))
print("云纹左锚 x=%d(应≈22) 右缘 x=%d(应≈%d)" % (CL[0], CR[2], page.PAGE_W - 22))
print("\n几何判定:", "通过" if ok else "不通过")
app.quit()
