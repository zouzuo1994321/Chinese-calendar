# -*- coding: utf-8 -*-
"""内置字体字重实测（**必须在真实平台插件下运行**，不能用 offscreen）。

为什么单独一个脚本、且必须真实平台：
    v1.8.3 的「英文加粗失效」bug 在 `QT_QPA_PLATFORM=offscreen` 下**完全复现不出来**
    —— 离屏渲染的字重匹配走的是另一条路径，61/61 全绿却掩盖了线上问题。
    只有真实 `windows` 插件才会以 PostScript 名作字体注册键，从而暴露出
    「Regular/Bold/Black 三份 PS 名相同 → 字重互相覆盖」的问题。

本脚本直接量**渲染后的深墨像素**，断言字重梯度真实存在：
    Normal < Bold < Black（且 Black 显著厚于 Normal）

用法： python tools/dev_checks/font_weight_probe.py
"""
import os
import sys

# ⚠ 故意不设 QT_QPA_PLATFORM=offscreen：本探针的目的就是跑真实平台。
os.environ.pop("QT_QPA_PLATFORM", None)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from calendar_app import fonts as FONTS
from ui.theme import EN_FONT, ZH_FONT, _font, use_builtin_fonts

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""))


print("平台插件 =", app.platformName())
if app.platformName() == "offscreen":
    print("!! 本探针必须在真实平台下运行（不要设 QT_QPA_PLATFORM=offscreen）")
    sys.exit(2)

fams = FONTS.install_fonts()
print("内置字体族 =", fams)
use_builtin_fonts()


def ink(font, text):
    """渲染一段文字，统计「深墨」像素量（关抗锯齿，使墨迹量可比）。"""
    img = QImage(460, 90, QImage.Format_ARGB32)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.setFont(font)
    p.setPen(QColor("#000000"))
    p.drawText(0, 58, text)
    p.end()
    n = 0
    for y in range(90):
        for x in range(460):
            if img.pixelColor(x, y).red() < 160:
                n += 1
    return n


# ---- 1. 内置族的字重必须真的可分 ----
print("\n[1] 英文（EN_FONT，无斜体 —— 与页头 _painter_shear 一致）")
en = {}
for w, tag in ((QFont.Normal, "Normal"), (QFont.Bold, "Bold"), (QFont.Black, "Black")):
    en[tag] = ink(_font(26, EN_FONT, w), "OCTOBER")
    print("    %-7s ink=%d" % (tag, en[tag]))
ck("英文 Normal < Bold < Black（字重梯度真实存在）",
   en["Normal"] < en["Bold"] < en["Black"],
   "Normal=%d Bold=%d Black=%d" % (en["Normal"], en["Bold"], en["Black"]))
ck("英文 Black 至少比 Normal 厚 15%",
   en["Black"] > en["Normal"] * 1.15,
   "+%.0f%%" % ((en["Black"] - en["Normal"]) * 100.0 / en["Normal"]))

print("\n[2] 中文（ZH_FONT）")
zh = {}
for w, tag in ((QFont.Normal, "Normal"), (QFont.Bold, "Bold"), (QFont.Black, "Black")):
    zh[tag] = ink(_font(14, ZH_FONT, w), "宜会亲友出行安床")
    print("    %-7s ink=%d" % (tag, zh[tag]))
ck("中文 Normal < Bold < Black", zh["Normal"] < zh["Bold"] < zh["Black"],
   "Normal=%d Bold=%d Black=%d" % (zh["Normal"], zh["Bold"], zh["Black"]))

# ---- 3. italic 必须不吞字重（这是页头曾经的坑）----
print("\n[3] italic=True 会吞掉字重（故页头改走 _painter_shear）")
ital = {t: ink(_font(26, EN_FONT, w, italic=True), "OCTOBER")
        for w, t in ((QFont.Normal, "Normal"), (QFont.Bold, "Bold"),
                     (QFont.Black, "Black"))}
for t, v in ital.items():
    print("    italic %-7s ink=%d" % (t, v))
_flat = len(set(ital.values())) == 1
ck("内置族 italic 时字重退化（已确知，故页头不用 italic）",
   _flat, "值=%s（全等=%s）" % (ital, _flat))

# ---- 4. 页头实际路径：Black + shear 必须厚于 Normal + shear ----
print("\n[4] 页头实际路径（_painter_shear 切变，保留字重）")
from ui.theme import SHEAR


def ink_shear(font, text):
    img = QImage(460, 90, QImage.Format_ARGB32)
    img.fill(0xFFFFFFFF)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, False)
    p.translate(140.0, 0.0)
    p.shear(SHEAR, 0.0)
    p.translate(-140.0, 0.0)
    p.setFont(font)
    p.setPen(QColor("#000000"))
    p.drawText(0, 58, text)
    p.end()
    return sum(1 for y in range(90) for x in range(460)
               if img.pixelColor(x, y).red() < 160)


sh = {t: ink_shear(_font(26, EN_FONT, w), "SEPTEMBER")
      for w, t in ((QFont.Normal, "Normal"), (QFont.Black, "Black"))}
for t, v in sh.items():
    print("    shear %-7s ink=%d" % (t, v))
ck("页头切变后 Black 仍显著厚于 Normal", sh["Black"] > sh["Normal"] * 1.15,
   "Normal=%d Black=%d (+%.0f%%)"
   % (sh["Normal"], sh["Black"], (sh["Black"] - sh["Normal"]) * 100.0 / sh["Normal"]))

ok = sum(1 for _n, c, _d in R if c)
print("\n==== 内置字体字重实测 ==== total=%d passed=%d failed=%d"
      % (len(R), ok, len(R) - ok))
for n, c, d in R:
    if not c:
        print("FAILED:", n, d)
sys.exit(0 if ok == len(R) else 1)
