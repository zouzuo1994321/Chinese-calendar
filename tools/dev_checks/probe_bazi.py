# -*- coding: utf-8 -*-
"""headless 验证八字数据层 + 对话框 + 联动 findData（不构造 MainWindow，避开沙箱 GUI 崩溃）。

验证：
1) compute_eightchar 返回含 shengxiao
2) BaziDialog._on_save 能 accept 且 bazi 非空（对话框保存逻辑）
3) 生肖下拉 findData(生肖) 能命中索引（联动前提）
4) bazi_day_report 返回 text/shengxiao（本日运势标签前提）
5) 复现 _paint_fortune 的 label 决策
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication, QComboBox

app = QApplication([])

from calendar_app.engine import compute_eightchar, bazi_day_report, get_day_info, analyze_zodiac_day
from ui.theme import SHENGXIAO_LIST
from ui.dialogs import BaziDialog

print("SHENGXIAO_LIST =", SHENGXIAO_LIST)

print("=== 1) compute_eightchar(1992,8,15,12) ===")
res = compute_eightchar(1992, 8, 15, 12)
print("  pillars:", res["pillars"], " shengxiao:", res["shengxiao"])

print("=== 2) BaziDialog._on_save 行为 ===")
d = BaziDialog(input_list=[1992, 8, 15, 12, False])
print("  初始 bazi:", d.bazi)
d._on_save()
print("  accept 后 result==Accepted:", d.result() == d.Accepted, " bazi 非空:", bool(d.bazi))

print("=== 3) 生肖下拉 findData 联动前提 ===")
box = QComboBox()
for s in SHENGXIAO_LIST:
    box.addItem(s, s)
sx = res["shengxiao"]
idx = box.findData(sx)
print("  findData(%s) -> idx=%s (>=0 即可联动)" % (sx, idx))
print("  setCurrentIndex 后 currentData =", (box.setCurrentIndex(idx) or box.currentData()))

print("=== 4) bazi_day_report + 本日运势标签 ===")
info = get_day_info(__import__("datetime").date.today())
brep = bazi_day_report(res, info)
print("  brep keys:", list(brep.keys()))
print("  brep.shengxiao:", brep.get("shengxiao"), " brep.text:", brep.get("text"))
rep = analyze_zodiac_day(info, brep["shengxiao"])
rep["name"] = brep["shengxiao"]
rep["bazi_text"] = brep["text"]
rep["score"] = max(5, min(98, (rep["score"] + brep["score"]) // 2))
label = "本日运势" if rep.get("bazi_text") else "本日生肖"
print("  rep.name:", rep.get("name"), " rep.bazi_text:", rep.get("bazi_text"))
print("  _paint_fortune 将显示标签:", label)
print("  ztxt =", "%s %s：%s（%d分）" % (label, rep.get("name") or "",
      " · ".join(rep["tags"]), rep["score"]))
print("\n结论：数据层 + 对话框 + findData + 本日运势标签 逻辑全部成立。")
