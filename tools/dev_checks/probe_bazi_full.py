# -*- coding: utf-8 -*-
"""v1.9.4 真机「八字保存失败 + 生肖不同步」全链路复现探针。

复刻 _open_bazi 的完整流程（对话框保存 → 联动 → 落盘 → 重载），
并【去掉 _apply_zodiac 的 try/except 兜底】把被吞掉的真实异常暴露出来。
"""
import json
import os
import sys
import traceback

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

BOX = os.path.join(_ROOT, "build", "_bazi_repro_%d" % os.getpid())
os.makedirs(BOX, exist_ok=True)
SETTINGS = os.path.join(BOX, "settings.json")

import ui.theme as _uit
import ui_main as _uim
_uit.SETTINGS_PATH = SETTINGS
_uim.SETTINGS_PATH = SETTINGS

from PySide6.QtWidgets import QApplication, QDialog

app = QApplication(sys.argv)

from ui_main import MainWindow
from ui.dialogs import BaziDialog
from calendar_app.engine import compute_eightchar, bazi_day_report, analyze_zodiac_day

print("=" * 60)
print("[1] BaziDialog 保存流（1990-1-1 12时，与用户截图一致）")
dlg = BaziDialog(None, None)
dlg.sb_year.setValue(1990); dlg.sb_month.setValue(1)
dlg.sb_day.setValue(1); dlg.sb_hour.setValue(12)
dlg._on_save()
print("    accepted =", dlg.result() == QDialog.DialogCode.Accepted)
print("    bazi =", dlg.bazi)
print("    input_list =", dlg.input_list)
try:
    print("    json.dumps =", json.dumps(dlg.bazi, ensure_ascii=False))
except Exception as ex:
    print("    !! json.dumps FAILED:", ex)
dlg.deleteLater()

print("[2] MainWindow 全链路（复刻 _open_bazi else 分支，不吞异常）")
mw = MainWindow()
print("    page.info 日期 =", mw.page.info["date"])
mw.bazi = dlg.bazi
mw._bazi_input = dlg.input_list
# _sync_zodiac_from_bazi（不吞异常的等价复刻）
sx = (mw.bazi or {}).get("shengxiao")
print("    shengxiao =", repr(sx))
idx = mw.page.zodiac_box.findData(sx)
print("    findData(%r) =" % sx, idx)
if idx >= 0:
    mw.page.zodiac_box.setCurrentIndex(idx)
print("    combo 当前 =", repr(mw.page.zodiac_box.currentText()),
      "index =", mw.page.zodiac_box.currentIndex(),
      "data =", repr(mw.page.zodiac_box.currentData()))

print("[3] _apply_zodiac 主体（无 try/except，暴露真异常）")
try:
    zodiac = mw.page.zodiac_box.currentData()
    rep = None
    brep = bazi_day_report(mw.bazi, mw.page.info) if mw.bazi else None
    print("    bazi_day_report =", {k: brep[k] for k in brep} if brep else None)
    if brep and brep.get("shengxiao"):
        rep = analyze_zodiac_day(mw.page.info, brep["shengxiao"])
        rep["name"] = brep["shengxiao"]
        rep["bazi_text"] = brep["text"]
        rep["score"] = max(5, min(98, (rep["score"] + brep["score"]) // 2))
    elif brep:
        rep = brep
        rep["name"] = "八字"
    elif zodiac:
        rep = analyze_zodiac_day(mw.page.info, zodiac)
        rep["name"] = zodiac
    print("    rep.name =", rep and rep.get("name"), " rep.score =", rep and rep.get("score"))
    mw.page.set_zodiac_report(rep)
    print("    set_zodiac_report OK（标签应为「本日运势」）")
except Exception:
    print("    !! _apply_zodiac 主体抛出真实异常：")
    traceback.print_exc()

print("[4] _save_settings 落盘（真实调用，含异常打印）")
try:
    mw._save_settings()
except Exception:
    print("    !! _save_settings 抛出异常：")
    traceback.print_exc()
print("    settings 存在 =", os.path.exists(SETTINGS))
if os.path.exists(SETTINGS):
    data = json.load(open(SETTINGS, encoding="utf-8"))
    print("    bazi 回读 =", data.get("bazi"))
    print("    bazi_input 回读 =", data.get("bazi_input"))
    print("    win_pos 回读 =", data.get("win_pos"))

print("[5] 模拟重启：新 MainWindow 读盘回显")
mw2 = MainWindow()
print("    mw2.bazi =", mw2.bazi)
print("    mw2._bazi_input =", mw2._bazi_input)
print("    mw2 combo =", repr(mw2.page.zodiac_box.currentText()),
      "index =", mw2.page.zodiac_box.currentIndex())

print("=" * 60)
print("DONE")
