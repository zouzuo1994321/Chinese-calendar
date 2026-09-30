# -*- coding: utf-8 -*-
"""v1.9.12 真机/离屏实测探针。

用户反馈「调整虚线位置，放在 分数 和 八字推演 居中位置」。本探针渲染整页，实测：
  ① 分隔虚线（绿色虚线）落在 y=541；
  ② 它位于「分数区」底部（左侧 吉/平/凶 方框底线 536）与「八字推演」文字墨迹顶（≈547）
     之间的空白带（537..546）正中 —— 上下留白之差 ≤2px。

用法：base python 直接运行（QT_QPA_PLATFORM=offscreen 由脚本内设）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                       # noqa: E402
from PySide6.QtGui import QImage                                 # noqa: E402

app = QApplication.instance() or QApplication([])
from ui.page import CalendarPage                                 # noqa: E402
from calendar_app.engine import (compute_eightchar, bazi_day_report,    # noqa: E402
                                 analyze_zodiac_day)

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


page = CalendarPage()
page.resize(page.PAGE_W, page.PAGE_H)
_br = bazi_day_report(compute_eightchar(1994, 3, 21, 13), page.info)
_rep = analyze_zodiac_day(page.info, _br["shengxiao"])
_rep["name"] = _br["shengxiao"]
_rep["bazi_text"] = _br["text"]
page.set_zodiac_report(_rep)
page.repaint()
img = page.grab().toImage().convertToFormat(QImage.Format_RGB32)


def rgb(x, y):
    c = img.pixel(x, y)
    return (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF


def green(x, y):
    r, g, b = rgb(x, y)
    return g > 90 and g - r > 40 and g - b > 40


def dark(x, y):
    r, g, b = rgb(x, y)
    return (r + g + b) / 3 < 150 and not green(x, y)


# ① 虚线行：x 34..486 上绿色像素最多的一行（虚线满宽 460px，约一半为段）
line_rows = [y for y in range(528, 552)
             if sum(1 for x in range(34, 486) if green(x, y)) > 150]
line_top = line_rows[0] if line_rows else -1
line_bot = line_rows[-1] if line_rows else -1
ck("虚线绘制行 = 541..542（原 536..537，下移 5 行）",
   line_rows == [541, 542], "实测虚线行 = %s" % (line_rows or "无"))

# ② 分数区最低点 = 左侧 吉/平/凶 方框底线（drawRect(30,484,52,52) + 2px 笔）
box_rows = [y for y in range(528, 540) if green(55, y)]
box_bottom = box_rows[-1] if box_rows else -1
ck("吉/平/凶 方框底线 = 行 536", box_bottom == 536, "实测方框底行 = %s" % box_rows)

# ③ 八字推演文字墨迹顶（深色像素首个 y）
bazi_top = None
for y in range(542, 575):
    if sum(1 for x in range(30, 490) if dark(x, y)) > 3:
        bazi_top = y
        break
ck("八字推演墨迹顶 = 行 548（在 543..560 内）",
   bazi_top is not None and 543 <= bazi_top <= 560, "实测 = %s" % bazi_top)

# ④ 上下留白（空行数）是否对称
gap_up = line_top - box_bottom - 1          # 分数区底 → 虚线上沿
gap_dn = (bazi_top or 0) - line_bot - 1     # 虚线下沿 → 八字推演顶
ck("虚线在「分数区底」与「八字推演顶」之间居中（上下空行差 ≤1）",
   abs(gap_up - gap_dn) <= 1,
   "上空 %d 行 / 下空 %d 行" % (gap_up, gap_dn))

print("==== v1.9.12 实测探针 ====")
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
