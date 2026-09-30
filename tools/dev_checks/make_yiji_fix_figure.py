# -*- coding: utf-8 -*-
"""生成「宜/忌 跨行居中错位」修复前/后对照图。

用真实页面渲染：同一日期，分别用「修复前（保留行尾顿号）」与「修复后（抹除行尾顿号）」
的断行逻辑各画一次，裁出宜框区域并排对照，叠一条居中虚线以显错位。

用法：base python 直接运行（脚本内设 offscreen）。
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                       # noqa: E402
from PySide6.QtGui import (QImage, QPainter, QColor, QPen,        # noqa: E402
                           QFont, QFontMetricsF)
from PySide6.QtCore import Qt, QRect, QRectF                      # noqa: E402

app = QApplication.instance() or QApplication([])
import ui.page as P                                              # noqa: E402
from ui.page import CalendarPage                                 # noqa: E402
from ui.theme import _font, ZH_FONT, palette_for                 # noqa: E402
from calendar_app.engine import get_day_info                     # noqa: E402

REAL = CalendarPage._wrap_px                                     # 修复后（真身）


def old_wrap_px(fm, text, width):
    """修复前逻辑：断行后**不**抹除行尾顿号。"""
    parts = text.split("、")
    units = [p + ("、" if i < len(parts) - 1 else "") for i, p in enumerate(parts)]
    lines, cur = [], ""
    for unit in units:
        if cur and fm.horizontalAdvance(cur + unit) > width:
            lines.append(cur)
            cur = ""
        if not cur and fm.horizontalAdvance(unit) > width:
            for ch in unit:
                if cur and fm.horizontalAdvance(cur + ch) > width:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            continue
        cur += unit
    if cur:
        lines.append(cur)
    return lines


page = CalendarPage()
page.resize(page.PAGE_W, page.PAGE_H)


def render(d):
    page.set_date(d)
    page.repaint()
    return page.grab().toImage().convertToFormat(QImage.Format_RGB32)


# 找一个宜/忌文本会折成 ≥2 行、且首行以顿号收尾的日期（最能体现错位）
CAND = None
d = date(2026, 1, 1)
while d <= date(2026, 12, 31):
    info = get_day_info(d)
    fm = QFontMetricsF(_font(14, ZH_FONT, QFont.DemiBold))
    for tag, key in (("宜", "yi"), ("忌", "ji")):
        txt = "、".join(info[key][:6]) or "—"
        lines = REAL(fm, txt, 140)
        raw = old_wrap_px(fm, txt, 140)
        if len(lines) >= 2 and any(ln.endswith("、") for ln in raw):
            CAND = (d, tag, key)
            break
    if CAND:
        break
    d += timedelta(days=1)

assert CAND, "未找到合适的多行示例日期"
_DAY, _TAG, _KEY = CAND

# 两次渲染：旧 / 新
Page = P.CalendarPage
Page._wrap_px = staticmethod(old_wrap_px)
_old = render(_DAY)
Page._wrap_px = REAL
_new = render(_DAY)

# 裁区域：宜框（x 25..185, y 380..482）；若示例是「忌」则裁忌框
if _TAG == "宜":
    RC = QRect(28, 380, 155, 100)
else:
    RC = QRect(338, 380, 155, 100)
crop_old = _old.copy(RC)
crop_new = _new.copy(RC)

SCALE = 2
W, H = RC.width() * SCALE, RC.height() * SCALE
crop_old = crop_old.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
crop_new = crop_new.scaled(W, H, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

LABEL_H, PAD, GUT, CAP_H = 40, 24, 36, 46
canvas = QImage(PAD * 2 + W * 2 + GUT, LABEL_H + H + CAP_H + PAD, QImage.Format_RGB32)
canvas.fill(QColor("#faf8f3"))

pp = QPainter(canvas)
pp.setRenderHint(QPainter.Antialiasing, True)
pp.setRenderHint(QPainter.TextAntialiasing, True)

x1, x2 = PAD, PAD + W + GUT
y_top = LABEL_H

# 标题
pp.setPen(QColor("#1a1a1a"))
pp.setFont(_font(13, ZH_FONT, QFont.Bold))
pp.drawText(QRect(0, 4, canvas.width(), LABEL_H - 6), Qt.AlignHCenter | Qt.AlignVCenter,
            "宜 / 忌 跨行居中 —— 修复前 / 修复后对照（%s %s）"
            % (_DAY.strftime("%Y-%m-%d"), _TAG))

# 两张裁图
pp.drawImage(x1, y_top, crop_old)
pp.drawImage(x2, y_top, crop_new)

# 居中虚线（红色）标出各框中线，凸显著墨迹是否对齐
for x0, tag, col in ((x1, "修复前", QColor("#c62828")), (x2, "修复后", QColor("#1f9c3d"))):
    cx = x0 + W // 2
    pen = QPen(col, 1, Qt.DashLine)
    pp.setPen(pen)
    pp.drawLine(cx, y_top, cx, y_top + H)
    # 标签条
    pp.fillRect(QRect(x0, y_top + H, W, 22), QColor(col))
    pp.setPen(QColor("#ffffff"))
    pp.setFont(_font(12, ZH_FONT, QFont.Bold))
    pp.drawText(QRect(x0, y_top + H, W, 22), Qt.AlignCenter, tag)

# 底部说明
pp.setPen(QColor("#333333"))
pp.setFont(_font(11, ZH_FONT))
pp.drawText(QRect(PAD, y_top + H + 30, canvas.width() - PAD * 2, CAP_H - 30),
            Qt.AlignHCenter | Qt.AlignTop,
            "修复前：行尾顿号被计入居中宽度，可见文字整体左偏（虚线在墨迹右侧）\n"
            "修复后：抹除行尾顿号，各行墨迹精确对齐于中线")
pp.end()

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "docs", "screenshots", "yiji-fix-compare.png")
canvas.save(OUT)

# 量证：修复后两张先后裁块的墨迹中点极差
def ink_centers(img, x0):
    xs = [x for x in range(img.width()) for y in range(img.height())
          if (img.pixelColor(x, y).red() + img.pixelColor(x, y).green()
              + img.pixelColor(x, y).blue()) / 3 < 150]
    return (min(xs), max(xs)) if xs else (0, 0)


print("示例日期 =", _DAY, _TAG)
print("修复前断行 =", old_wrap_px(QFontMetricsF(_font(14, ZH_FONT, QFont.DemiBold)),
                                  "、".join(get_day_info(_DAY)[_KEY][:6]), 140))
print("修复后断行 =", REAL(QFontMetricsF(_font(14, ZH_FONT, QFont.DemiBold)),
                           "、".join(get_day_info(_DAY)[_KEY][:6]), 140))
print("对照图已保存:", OUT)
sys.exit(0)
