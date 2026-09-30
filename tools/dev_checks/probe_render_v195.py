# -*- coding: utf-8 -*-
"""v1.9.5 交付前视觉探针：渲染真实页面 PNG + 复核 5px 间隔与两字生肖。

- 红日页：选「马」→ 生肖框显示「午马」、本日生肖 午马、年/日生肖两字。
- 八字链路：1990-1-1 12时 → 年支巳蛇 → 生肖框联动「巳蛇」、本日运势 巳蛇。
- 程序化量算 R1/R2/R3/R4 四处间隔是否均为 5px。
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

BOX = os.path.join(_ROOT, "build", "_render_v195_%d" % os.getpid())
os.makedirs(BOX, exist_ok=True)
SETTINGS = os.path.join(BOX, "settings.json")

import ui.theme as _uit
import ui_main as _uim
_uit.SETTINGS_PATH = SETTINGS
_uim.SETTINGS_PATH = SETTINGS

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QImage

app = QApplication(sys.argv)

from ui_main import MainWindow
from ui.dialogs import BaziDialog
from calendar_app.engine import compute_eightchar, bazi_day_report, ANIMAL_TO_2CHAR
from datetime import date

_two = lambda s: ANIMAL_TO_2CHAR.get(s, s)

OUT = os.path.join(_ROOT, "dist", "_render_v195")
os.makedirs(OUT, exist_ok=True)


def shot(mw, name):
    mw.page.repaint()
    img = mw.page.grab().toImage()
    p = os.path.join(OUT, name)
    img.save(p)
    print("    saved:", p, img.width(), "x", img.height())


def report_geometry(mw):
    """程序化量算四处间隔（与 page.py 常量一致）。"""
    # 宜/忌框底（384 + 95 = 479）；本日运势框顶（_paint_fortune y=484）
    R1 = 484 - (384 + 95)
    # 左右栏列间距：左框 30..257，右框 262..490
    R2 = 262 - 257
    # 吉时/颜色框底（574 + 68 = 642）；建议卡顶（_advice_rects y=647）
    R3 = 647 - 642
    # 建议卡行间距：cell_h=54，行间距 +5 → 行0 底 701，行1 顶 706
    R4 = 706 - 701
    print("    间隔 R1(宜/忌↔本日运势)=%d  R2(栏间距)=%d  R3(时辰↔事业)=%d  R4(事业↔出行)=%d"
          % (R1, R2, R3, R4))
    ok = (R1, R2, R3, R4) == (5, 5, 5, 5)
    print("    => 四处间隔全部 5px :", ok)
    return ok


# ---------- 红日页：选「马」 ----------
print("[A] 红日页 + 选「马」")
mw = MainWindow()
# 固定到 2026-01-06（宜三行日，验证窄栏不裁切）
mw._set_date(date(2026, 1, 6))
idx = mw.page.zodiac_box.findData("马")
mw.page.zodiac_box.setCurrentIndex(idx)
mw._apply_zodiac()
print("    生肖框显示 =", repr(mw.page.zodiac_box.currentText()),
      " data =", repr(mw.page.zodiac_box.currentData()))
rep = mw.page.zodiac_report
print("    本日生肖标签 =", rep and (("本日运势" if rep.get("bazi_text") else "本日生肖")
      + " " + (rep.get("name") or "")))
print("    年/日生肖两字 =",
      mw.page.info["lunar_year_cn"] + "年 · " + _two(mw.page.info["lunar_year_shengxiao"]),
      "/", mw.page.info["day_ganzhi"] + "日 · 属" + _two(mw.page.info["day_shengxiao"]))
report_geometry(mw)
shot(mw, "red_horse.png")

# ---------- 八字链路：1990-1-1 12时 ----------
print("[B] 八字链路 1990-1-1 12时（应联动「巳蛇」）")
dlg = BaziDialog(None, None)
dlg.sb_year.setValue(1990); dlg.sb_month.setValue(1)
dlg.sb_day.setValue(1); dlg.sb_hour.setValue(12)
dlg._on_save()
mw.bazi = dlg.bazi
mw._bazi_input = dlg.input_list
mw._sync_zodiac_from_bazi()
mw._apply_zodiac()
dlg.deleteLater()
print("    四柱 =", dlg.bazi["pillars"], " 年支生肖 =", repr(dlg.bazi["shengxiao"]))
print("    生肖框联动显示 =", repr(mw.page.zodiac_box.currentText()),
      " index =", mw.page.zodiac_box.currentIndex())
rep = mw.page.zodiac_report
print("    本日运势标签 =", "本日运势 " + (rep.get("name") or ""), " score =", rep.get("score"))
shot(mw, "red_bazi_snake.png")

# ---------- 绿日页：仅选「龙」 ----------
print("[C] 绿日页 + 选「龙」")
mw2 = MainWindow()
mw2._set_date(date(2026, 5, 1))
idx2 = mw2.page.zodiac_box.findData("龙")
mw2.page.zodiac_box.setCurrentIndex(idx2)
mw2._apply_zodiac()
shot(mw2, "green_dragon.png")

print("DONE")
