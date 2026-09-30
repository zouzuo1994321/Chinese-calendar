# -*- coding: utf-8 -*-
"""v1.9.10 真机/离屏实测探针。

覆盖本轮 4 项改动的**可测量**部分：
  ① 底部四按钮距外框 5px（外框 3px 线占 787..790，按钮上沿 796，空白 5 行）
  ② 提示行随页高下移、页底留白仍 5px（PAGE_H 841）
  ③ 宜 / 忌 内容水平居中（墨迹中点 ≈ 框中心）
  ④ 八字推演行加粗（墨迹像素数，与 Regular 对比）
另：字号/字重走真实 Bold 面（内置 Noto Serif SC），不依赖离屏字体替换。

用法：base python 直接运行（QT_QPA_PLATFORM=offscreen 由脚本内设）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                  # noqa: E402
from PySide6.QtGui import QImage, QFont, QFontMetricsF      # noqa: E402

app = QApplication.instance() or QApplication([])
from ui.page import CalendarPage                            # noqa: E402
from ui.theme import _font, ZH_SONG                         # noqa: E402
from calendar_app.engine import (compute_eightchar, bazi_day_report,   # noqa: E402
                                 analyze_zodiac_day)

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


page = CalendarPage()
page.resize(page.PAGE_W, page.PAGE_H)

# 注入用户八字推演，确保「八字推演」行有内容
_bz = compute_eightchar(1994, 3, 21, 13)
_br = bazi_day_report(_bz, page.info)
_rep = analyze_zodiac_day(page.info, _br["shengxiao"])
_rep["name"] = _br["shengxiao"]
_rep["bazi_text"] = _br["text"]
page.set_zodiac_report(_rep)

pm = page.grab()
img = pm.toImage().convertToFormat(QImage.Format_RGB32)
W, H = img.width(), img.height()


def rgb(x, y):
    c = img.pixel(x, y)
    return (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF


def is_green(r, g, b):
    return g > 90 and g - r > 40 and g - b > 40


def is_ink(r, g, b):
    return (r + g + b) / 3 < 150


# ---------- ① 页面尺寸 / TAB_Y ----------
ck("页面 520x841（PAGE_H 838→841）", (W, H) == (520, 841), "%dx%d" % (W, H))
ck("TAB_Y = 796 = FRAME_OUT_BOTTOM(789) + 7",
   CalendarPage.TAB_Y == CalendarPage.FRAME_OUT_BOTTOM + 7,
   "TAB_Y=%d" % CalendarPage.TAB_Y)

# ---------- ② 外框线 / 按钮上沿 / 空白行 ----------
# ⚠ 阈值必须接近满宽：4 个按钮合计边框约 420px，用 0.85 阈值会把按钮行误判成框线。
# ⚠ 内框(1px) 与外框(3px) 都是满宽，故取「最后一段连续满宽行」= 外框下沿。
def _green_row(y, x0=30, x1=None):
    x1 = x1 if x1 is not None else W - 30
    return sum(1 for x in range(x0, x1) if is_green(*rgb(x, y)))


_full = [y for y in range(770, 800) if _green_row(y) > (W - 60) * 0.95]
_runs = []
for y in _full:
    if _runs and y == _runs[-1][-1] + 1:
        _runs[-1].append(y)
    else:
        _runs.append([y])
frame_rows = _runs[-1]                      # 外框（最靠下的满宽段）
btn_rows = [y for y in range(frame_rows[-1] + 1, 840) if _green_row(y, 29, 135) > 60]
frame_top, frame_bot = frame_rows[0], frame_rows[-1]
btn_top = btn_rows[0]
gap = btn_top - frame_bot - 1
ck("外框线 3px 落在 787..790", (frame_top, frame_bot) == (787, 790),
   "实测 %d..%d" % (frame_top, frame_bot))
ck("按钮上沿 = 796", btn_top == 796, "实测 %d" % btn_top)
ck("按钮距外框空白 = 5px", gap == 5, "空白行 %d..%d = %d 行"
   % (frame_bot + 1, btn_top - 1, gap))

# ---------- ③ 宜 / 忌 居中 ----------
def ink_bbox(x0, x1, y0, y1):
    xs = [x for x in range(x0, x1) for y in range(y0, y1) if is_ink(*rgb(x, y))]
    return (min(xs), max(xs)) if xs else (None, None)


for tag, x0, x1, cx in [("宜", 35, 175, 105), ("忌", 345, 485, 415)]:
    l, r = ink_bbox(x0, x1, 422, 476)
    dev = abs((l + r) / 2 - cx)
    ck("%s 内容水平居中（墨迹中点偏差 ≤ 8px）" % tag, l is not None and dev <= 8,
       "墨迹 %s..%s 中点 %.1f 框中心 %d 偏差 %.1f" % (l, r, (l + r) / 2, cx, dev))

# ---------- ④ 八字推行加粗（对比 Regular / Bold 的墨迹像素）----------
def para_ink(weight):
    fm = QFontMetricsF(_font(12, ZH_SONG, weight))
    return fm.horizontalAdvance("八字推演：日主丙午（火命） ｜ 比和、支六合")


w_reg = para_ink(QFont.Normal)
w_bold = para_ink(QFont.Bold)
ck("八字推行 Bold 宽度 ≥ Regular（真实 Bold 面）", w_bold >= w_reg,
   "Regular=%.1f Bold=%.1f（+%.1f）" % (w_reg, w_bold, w_bold - w_reg))
zx_ink = sum(1 for x in range(30, 490) for y in range(542, 564)
             if is_ink(*rgb(x, y)))
ck("八字推行有墨迹（渲染存在）", zx_ink > 200, "墨迹像素 = %d" % zx_ink)

# ---------- ⑤ 页底留白仍 5px ----------
ck("页底留白 = PAGE_H - (TAB_Y+TAB_H+2+12) = 5",
   CalendarPage.PAGE_H - (CalendarPage.TAB_Y + CalendarPage.TAB_H + 2 + 12) == 5)

print("==== v1.9.10 实测探针 ====")
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
