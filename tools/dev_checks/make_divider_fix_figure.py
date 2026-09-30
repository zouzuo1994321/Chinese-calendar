# -*- coding: utf-8 -*-
"""生成「分数区 ↔ 八字推演 分隔虚线」修复前/后对照图（v1.9.12）。

渲染真实页面两次：旧位置（drawLine y-3 → 行 536..537）与新位置（y+2 → 行 541..542），
裁出「分数区 + 八字推演」区域并排，叠灰色辅助线标出上下留白是否对称。

用法：base python 直接运行（脚本内设 offscreen）。
"""
import os
import sys
import inspect
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                       # noqa: E402
from PySide6.QtGui import (QImage, QPainter, QColor, QPen,        # noqa: E402
                           QFont)
from PySide6.QtCore import Qt, QRect                              # noqa: E402

app = QApplication.instance() or QApplication([])
from ui.page import CalendarPage                                 # noqa: E402
from ui.theme import _font, ZH_FONT                              # noqa: E402
from calendar_app.engine import (compute_eightchar, bazi_day_report,   # noqa: E402
                                 analyze_zodiac_day)

page = CalendarPage()
page.resize(page.PAGE_W, page.PAGE_H)
_br = bazi_day_report(compute_eightchar(1994, 3, 21, 13), page.info)
_rep = analyze_zodiac_day(page.info, _br["shengxiao"])
_rep["name"] = _br["shengxiao"]
_rep["bazi_text"] = _br["text"]
page.set_zodiac_report(_rep)

ORIG = CalendarPage._paint_zodiac


def variant(dy):
    src = textwrap.dedent(inspect.getsource(ORIG)).replace(
        "line_y = y + 2", "line_y = y + %d" % dy)
    ns = {}
    exec(compile(src, "<variant>", "exec"), dict(ORIG.__globals__), ns)
    return ns[ORIG.__name__]


def render():
    page.repaint()
    return page.grab().toImage().convertToFormat(QImage.Format_RGB32)


CalendarPage._paint_zodiac = variant(-3)      # 旧：行 536..537
_old = render()
CalendarPage._paint_zodiac = variant(2)       # 新：行 541..542
_new = render()
CalendarPage._paint_zodiac = ORIG

RC = QRect(26, 480, 196, 90)
S = 3


def crop(img):
    return img.copy(RC).scaled(RC.width() * S, RC.height() * S,
                               Qt.IgnoreAspectRatio, Qt.SmoothTransformation)


co, cn = crop(_old), crop(_new)
W, H = co.width(), co.height()
PAD, GUT, LBL, CAP = 22, 34, 40, 30
cv = QImage(PAD * 2 + W * 2 + GUT, LBL + H + 26 + CAP + 16, QImage.Format_RGB32)
cv.fill(QColor("#faf8f3"))
pp = QPainter(cv)
pp.setRenderHint(QPainter.Antialiasing, True)
pp.setRenderHint(QPainter.TextAntialiasing, True)

pp.setPen(QColor("#1a1a1a"))
pp.setFont(_font(12, ZH_FONT, QFont.Bold))
pp.drawText(QRect(0, 2, cv.width(), LBL - 4), Qt.AlignCenter,
            "分隔虚线：分数区 ↔ 八字推演 的居中调整（2026-09-30）")

x1, x2 = PAD, PAD + W + GUT
y_top = LBL
pp.drawImage(x1, y_top, co)
pp.drawImage(x2, y_top, cn)

# 在每张图上标出「分数区底线」与「八字推演顶」的灰虚线，直观看出上下留白
def mark(x0, tag, col):
    # page y 536(方框底) / 548(八字推演顶) → 裁图局部坐标
    def ty(py):
        return y_top + int((py - RC.top()) * S)
    for py, lb in ((536, "分数区底"), (548, "八字推演顶")):
        pp.setPen(QPen(QColor("#9a9a9a"), 1, Qt.DotLine))
        pp.drawLine(x0, ty(py), x0 + W, ty(py))
    pp.fillRect(QRect(x0, y_top + H, W, 26), col)
    pp.setPen(QColor("#ffffff"))
    pp.setFont(_font(11, ZH_FONT, QFont.Bold))
    pp.drawText(QRect(x0, y_top + H, W, 26), Qt.AlignCenter, tag)


mark(x1, "修复前  行 536..537（贴住分数区底）", QColor("#c62828"))
mark(x2, "修复后  行 541..542（上下留白对称）", QColor("#1f9c3d"))

pp.setPen(QColor("#333333"))
pp.setFont(_font(10, ZH_FONT))
pp.drawText(QRect(PAD, y_top + H + 30, cv.width() - PAD * 2, CAP),
            Qt.AlignHCenter | Qt.AlignTop,
            "灰点线 = 分数区底线(536) 与 八字推演墨迹顶(548)　虚线落于二者之间：修复前贴住上方、修复后上下留白 4 : 5")
pp.end()

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "docs", "screenshots",
    "divider-fix-compare.png")
cv.save(OUT)
print("对照图已保存:", OUT)
sys.exit(0)
