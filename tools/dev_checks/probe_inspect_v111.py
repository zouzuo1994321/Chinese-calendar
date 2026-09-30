# -*- coding: utf-8 -*-
"""v1.9.11 真机/离屏实测探针。

覆盖本轮 2 项改动：
  ① 宜 / 忌 **跨行居中**：换行点行尾顿号被抹除后，各行墨迹中点应对齐
     （渲染整页 -> 逐行取墨迹 bbox -> 校验各行中心横坐标极差 ≤ 3px）。
  ② 软件 logo 更新：logo.png 为 1024×1024、主色调朱红；logo.ico 多尺寸含 256²。

用法：base python 直接运行（QT_QPA_PLATFORM=offscreen 由脚本内设）。
"""
import os
import struct
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication                  # noqa: E402
from PySide6.QtGui import QImage                            # noqa: E402

app = QApplication.instance() or QApplication([])
from ui.page import CalendarPage                            # noqa: E402
from ui.theme import IMG_LOGO                               # noqa: E402

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


page = CalendarPage()
page.resize(page.PAGE_W, page.PAGE_H)


def render(d):
    page.set_date(d)
    img = page.grab().toImage().convertToFormat(QImage.Format_RGB32)
    return img


def rgb(img, x, y):
    c = img.pixel(x, y)
    return (c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF


def is_ink(img, x, y):
    r, g, b = rgb(img, x, y)
    return (r + g + b) / 3 < 150


def row_centers(img, x0, x1, y0, y1):
    """在矩形内逐行取墨迹带，返回每带的 (y_mid, x_left, x_right, x_center)。"""
    bands, cur = [], None
    for y in range(y0, y1):
        xs = [x for x in range(x0, x1) if is_ink(img, x, y)]
        if xs:
            if cur is None:
                cur = [y, y, min(xs), max(xs)]
            else:
                cur[1] = y
                cur[2] = min(cur[2], min(xs))
                cur[3] = max(cur[3], max(xs))
        elif cur is not None:
            bands.append(cur)
            cur = None
    if cur is not None:
        bands.append(cur)
    return [((b[0] + b[1]) / 2, b[2], b[3], (b[2] + b[3]) / 2) for b in bands]


# ---------- ① 宜 / 忌 跨行居中（渲染实测）----------
# 扫 2026 全年，挑出宜/忌文本确实换行（≥2 行）的若干日期做校验。
REGIONS = [("宜", 35, 175), ("忌", 345, 485)]
checked_days = 0
max_spread = 0.0
worst = None
d = date(2026, 1, 1)
while d <= date(2026, 12, 31) and checked_days < 40:
    img = render(d)
    for tag, x0, x1 in REGIONS:
        bands = row_centers(img, x0, x1, 422, 476)
        if len(bands) >= 2:                       # 确有跨行
            cs = [b[3] for b in bands]
            spread = max(cs) - min(cs)
            if spread > max_spread:
                max_spread, worst = spread, (str(d), tag, [round(c, 1) for c in cs])
            checked_days += 1
            break
    d += timedelta(days=1)

ck("渲染实测：宜/忌跨行样本均取自真实日期（≥1 例）", checked_days >= 1,
   "抽样跨行日期数 = %d" % checked_days)
ck("宜/忌各行墨迹中点对齐（极差 ≤ 3px，修掉行尾顿号左偏）", max_spread <= 3.0,
   "最差极差 %.2fpx @ %s" % (max_spread, worst))

# 反向印证：行尾顿号在 14px DemiBold 下约 7px，旧行为必有此量级左偏
from PySide6.QtGui import QFontMetricsF, QFont                    # noqa: E402
from ui.theme import _font, ZH_FONT                               # noqa: E402
_fm14 = QFontMetricsF(_font(14, ZH_FONT, QFont.DemiBold))
_shift = (_fm14.horizontalAdvance("出行、") - _fm14.horizontalAdvance("出行")) / 2.0
ck("行尾顿号居中左偏量 ≈ 半字（>3px），证明确为错位来源", _shift > 3.0,
   "半顿号 ≈ %.1fpx" % _shift)

# ---------- ② 软件 logo 更新 ----------
with open(IMG_LOGO, "rb") as f:
    sig = f.read(8)
    _len, _typ = struct.unpack(">I4s", f.read(8))
    w, h = struct.unpack(">II", f.read(8))
ck("logo.png 为方形 1024×1024", sig[:4] == b"\x89PNG" and w == 1024 and h == 1024,
   "签名=%r 尺寸=%dx%d" % (sig[:4], w, h))

_ico = os.path.join(os.path.dirname(IMG_LOGO), "logo.ico")
with open(_ico, "rb") as f:
    _r, _t, cnt = struct.unpack("<HHH", f.read(6))
    sizes = []
    for _ in range(cnt):
        bw, bh = struct.unpack("<BB", f.read(2))
        f.read(14)
        sizes.append((bw or 256, bh or 256))
ck("logo.ico 含多尺寸且覆盖 256²", len(sizes) >= 5 and (256, 256) in sizes,
   "尺寸 = %s" % sizes)

# 主色调为朱红（新 logo 红底金「历」）
_img = QImage(IMG_LOGO)
red = gold = tot = 0
for y in range(0, _img.height(), 7):
    for x in range(0, _img.width(), 7):
        r, g, b, _a = _img.pixelColor(x, y).getRgb()
        tot += 1
        if r > 120 and r - g > 60 and r - b > 60:
            red += 1
        elif r > 150 and g > 120 and b < 120:
            gold += 1
ck("logo.png 主色为朱红底（新配色）", red / tot > 0.4,
   "红占比 %.0f%% 金占比 %.0f%%" % (100.0 * red / tot, 100.0 * gold / tot))

print("==== v1.9.11 实测探针 ====")
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
