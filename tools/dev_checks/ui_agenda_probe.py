# -*- coding: utf-8 -*-
"""v1.7.0 新增交互的离屏探针：行事历面板 编辑/保存、导入崩溃回归、区间导出对话框。

不触碰用户的 agenda_cache.json / agenda_edit.json（重定向到独立沙盒）。
"""
import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QFileDialog

import ui_main
from ui_main import AgendaExportDialog, AgendaImportDialog, AgendaPanel
from calendar_app import agenda_pdf as AG

from _box import make_box

BOX = make_box("_ui_agenda")        # 退出时自动回收，不再累积在 build/
AG.CACHE_PATH = os.path.join(BOX, "agenda_cache.json")
AG.EDIT_PATH = os.path.join(BOX, "agenda_edit.json")

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""))


app = QApplication(sys.argv)

# 造一份行事历（2026 丙午年，九月 10.11-11.9 / 十月 11.10-12.9）
AG.save_cache([
    {"year": "2026", "year_ganzhi": "丙午", "months": ["九"], "ganzhi": "丙戌",
     "range": "10.11-11.9", "content": "九月导入要点：本命伏吟。"},
    {"year": "2026", "year_ganzhi": "丙午", "months": ["十"], "ganzhi": "丁亥",
     "range": "11.10-12.9", "content": "十月导入要点：宜静不宜动。"},
])

# ---------------- 1. 本月行事历面板：编辑 / 保存 ----------------
pm = AgendaPanel(mode="month")
pm.theme_info = {"date": date(2026, 10, 20)}
pm.records = AG.load_cache()
pm._match_current()
pm.show()          # 离屏下需显式 show，isVisible() 才有意义
ck("面板：控件齐备（editor + 编辑 + 保存）",
   hasattr(pm, "editor") and hasattr(pm, "btn_edit") and hasattr(pm, "btn_save"))
ck("面板：编辑/保存位于右下角",
   pm.btn_save.geometry().right() >= pm.PANEL_W - 6 - 1
   and pm.btn_edit.geometry().right() < pm.btn_save.geometry().left()
   and pm.btn_save.geometry().bottom() >= pm.PANEL_H - 34,
   "edit=%s save=%s" % (pm.btn_edit.geometry().getRect(), pm.btn_save.geometry().getRect()))
ck("面板：初始只读态（常驻正文框，保存置灰）",
   pm.editor.isVisible() and pm.editor.isReadOnly() and not pm.btn_save.isEnabled()
   and pm.btn_edit.text() == "编辑",
   "vis=%s ro=%s save=%s" % (pm.editor.isVisible(), pm.editor.isReadOnly(),
                             pm.btn_save.isEnabled()))
ck("面板：正文框为常驻 QPlainTextEdit（可滚动承载长文）",
   pm.editor.geometry() == pm.EDIT_RECT and pm.editor.verticalScrollBar() is not None,
   str(pm.editor.geometry().getRect()))

MKEY = pm._override_key()
ck("面板：覆写键 = 干支年|农历月", MKEY == "丙午|九", MKEY)
ck("面板：默认显示导入内容", "九月导入要点" in pm._body_text(), pm._body_text()[:20])
ck("面板：正文已刷入常驻编辑器", "九月导入要点" in pm.editor.toPlainText(),
   pm.editor.toPlainText()[:20])
ck("面板：只读态样式透明融入纸面", "background:transparent" in pm.editor.styleSheet())
ck("面板：滚动条滑块用当日主题色", pm._last_main.name() in pm.editor.styleSheet(),
   "%s in style" % pm._last_main.name())
# 长文 → 出现可滚动量（v1.7.1 反馈：文字过多显示不全）
pm.editor.setPlainText("内容行。\n" * 80)
app.processEvents()
_mx = pm.editor.verticalScrollBar().maximum()
ck("面板：长文出现可滚动量（滚动条生效）", _mx > 40, "scrollMax=%d" % _mx)
pm._sync_body()
pm.btn_edit.click()
ck("面板：点『编辑』→ 解除只读、按钮变『取消』、保存可用",
   pm.editor.isVisible() and not pm.editor.isReadOnly()
   and pm.btn_edit.text() == "取消" and pm.btn_save.isEnabled(),
   "ro=%s txt=%s save=%s" % (pm.editor.isReadOnly(), pm.btn_edit.text(),
                             pm.btn_save.isEnabled()))
ck("面板：编辑态样式带主题色边框", "border:1px solid" in pm.editor.styleSheet())
pm.editor.setPlainText("九月手写要点：诸事宜缓。")
pm.btn_save.click()
ck("面板：点『保存』→ 写盘并回到只读",
   pm.editor.isReadOnly() and pm.btn_save.isEnabled() is False
   and pm.btn_edit.text() == "编辑")
ck("面板：覆写已落盘", AG.get_override("month", MKEY) == "九月手写要点：诸事宜缓。",
   AG.get_override("month", MKEY))
ck("面板：显示优先取手写内容", pm._body_text() == "九月手写要点：诸事宜缓。", pm._body_text())
PM_SHOT = os.path.join(BOX, "panel_month.png")
pm.grab().save(PM_SHOT)
ck("面板：可渲染出图", os.path.exists(PM_SHOT) and os.path.getsize(PM_SHOT) > 200,
   "%.1f KB" % (os.path.getsize(PM_SHOT) / 1024))

# 「✎ 已手工修改」标记应绘制在「编辑」按钮左侧同行（v1.7.1 反馈项）
from PySide6.QtGui import QImage
MARK_RECT = (int(pm.btn_edit.geometry().left()) - 160,
             pm.PANEL_H - 32, 152, pm.BTN_H)
img_no = QImage(PM_SHOT)


def mark_ink(img):
    n = 0
    for yy in range(MARK_RECT[1], MARK_RECT[1] + MARK_RECT[3]):
        for xx in range(MARK_RECT[0], MARK_RECT[0] + MARK_RECT[2]):
            c = img.pixelColor(xx, yy)
            if c.red() < 200 and c.green() < 200:
                n += 1
    return n


ink_with = mark_ink(img_no)
pm2_key_ok = bool(AG.get_override("month", MKEY))
ck("面板：标记区域前提成立（存在覆写）", pm2_key_ok)
# 再造一份无覆写的对照图
AG.save_override("month", MKEY, "")
pm.grab().save(PM_SHOT)
img_blank = QImage(PM_SHOT)
ink_without = mark_ink(img_blank)
ck("面板：『✎ 已手工修改』绘制于编辑按钮左侧",
   ink_with > 40 and ink_without < 10, "有覆写=%d px / 无覆写=%d px" % (ink_with, ink_without))
AG.save_override("month", MKEY, "九月手写要点：诸事宜缓。")   # 还原

# 取消：改了不保存不应落盘
pm.btn_edit.click()
pm.editor.setPlainText("临时乱写")
pm.btn_edit.click()          # 取消
ck("面板：『取消』后不落盘并还原正文",
   AG.get_override("month", MKEY) == "九月手写要点：诸事宜缓。"
   and "九月手写要点" in pm.editor.toPlainText())

# ---------------- 2. 本日行事历面板：按日期存键 ----------------
pd = AgendaPanel(mode="day")
pd.theme_info = {"date": date(2026, 10, 20)}
pd.records = []              # 未导入任何行事历
ck("面板(day)：无导入时给出可手写提示", "编辑" in pd._body_text(), pd._body_text()[:24])
pd.show()
pd.btn_edit.click()
pd.editor.setPlainText("10-20 手写：宜祭祀。")
pd.btn_save.click()
ck("面板(day)：按 YYYY-MM-DD 存键",
   AG.get_override("day", "2026-10-20") == "10-20 手写：宜祭祀。",
   AG.get_override("day", "2026-10-20"))
ck("面板(day)：显示手写内容", pd._body_text() == "10-20 手写：宜祭祀。")

# ---------------- 3. 导入崩溃回归（"%d" % list） ----------------
xlsx = os.path.join(BOX, "tpl.xlsx")
AG.make_agenda_template(xlsx, 2026, "丙午年")
dlg = AgendaImportDialog()
dlg.__class__._next_path = xlsx
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (xlsx, ""))
dlg._pick_file()
ck("导入：模板 xlsx 不再崩溃，且给出条数", "已解析 12 条" in dlg.lb_result.text(),
   dlg.lb_result.text())
ck("导入：imported 标记为真", dlg.imported is True)

pdf = os.path.join(BOX, "tpl.pdf")
AG.make_agenda_template(pdf, 2026, "丙午年")
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (pdf, ""))
dlg._pick_file()
ck("导入：PDF 模板不再崩溃", "已解析 12 条" in dlg.lb_result.text(), dlg.lb_result.text())

# ---------------- 4. 区间导出对话框 ----------------
ed = AgendaExportDialog()
ck("导出对话框：两个日期选择器 + 格式下拉",
   isinstance(ed.date_from.date(), QDate) and isinstance(ed.date_to.date(), QDate)
   and ed.cmb.count() == 3)
ed.date_from.setDate(QDate(2026, 10, 1))
ed.date_to.setDate(QDate(2026, 12, 31))
out = os.path.join(BOX, "out.xlsx")
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out, ""))
ed._do_export()
ck("导出：写盘成功且条数正确", os.path.exists(out) and "已导出 4 条" in ed.lb_result.text(),
   ed.lb_result.text())

out_csv = os.path.join(BOX, "out.csv")
ed.cmb.setCurrentIndex(1)
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out_csv, ""))
ed._do_export()
ck("导出：CSV 分支可用", os.path.exists(out_csv) and os.path.getsize(out_csv) > 50)

# 区间反序（从晚到早）应自动纠正而不是空结果
out_txt = os.path.join(BOX, "out.txt")
ed.cmb.setCurrentIndex(2)
ed.date_from.setDate(QDate(2026, 12, 31))
ed.date_to.setDate(QDate(2026, 10, 1))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (out_txt, ""))
ed._do_export()
ck("导出：起止反序自动纠正", "已导出 4 条" in ed.lb_result.text(), ed.lb_result.text())

# 空区间应给可读提示而非崩溃
ed.date_from.setDate(QDate(2001, 1, 1))
ed.date_to.setDate(QDate(2001, 2, 1))
ed._do_export()
ck("导出：空区间给出可读提示", "没有可导出" in ed.lb_result.text(), ed.lb_result.text()[:40])

ED_SHOT = os.path.join(BOX, "export_dlg.png")
ed.grab().save(ED_SHOT)
ck("导出对话框：可渲染出图", os.path.getsize(ED_SHOT) > 2000,
   "%.1f KB" % (os.path.getsize(ED_SHOT) / 1024))

# ---------------- 5. 正文墨色随红 / 绿主题切换（v1.7.2 反馈） ----------------
from PySide6.QtGui import QColor

pm._apply_theme(QColor("#c62828"))
ck("正文墨色：红日 → 深红 #8e1a1a", "#8e1a1a" in pm.editor.styleSheet(),
   pm.editor.styleSheet()[:60].replace("\n", " "))
pm._apply_theme(QColor("#1f9c3d"))
ck("正文墨色：绿日 → 墨绿 #136b29", "#136b29" in pm.editor.styleSheet())
ck("正文墨色：红日滚动条滑块仍为主题色", "#c62828" in pm.editor.styleSheet()
   or pm._last_main.name() in pm.editor.styleSheet())
pm._apply_theme(QColor("#1f9c3d"))          # 还原绿态

# ---------------- 6. 窗口位置：贴边吸附 / 记忆 / 初始化（v1.7.2 反馈） ----------------
import ui_main as _uim
_uim.SETTINGS_PATH = os.path.join(BOX, "settings.json")   # 不碰用户真实 settings.json
from ui_main import MainWindow

mw = MainWindow()
mw.show()
scr = QApplication.primaryScreen().availableGeometry()
w, h = mw.frameGeometry().width(), mw.frameGeometry().height()


def _center_of(s):
    return (s.left() + max(0, (s.width() - w) // 2),
            s.top() + max(0, (s.height() - h) // 2))


cx, cy = _center_of(scr)
ck("窗口：首次打开（无记录）居中显示", abs(mw.x() - cx) <= 1 and abs(mw.y() - cy) <= 1,
   "pos=(%d,%d) 期望=(%d,%d)" % (mw.x(), mw.y(), cx, cy))

# 左 / 上边缘贴边
mw.move(scr.left() + 4, scr.top() + 6)
app.processEvents()
ck("窗口：拖近左/上边缘自动贴边",
   mw.x() == scr.left() and mw.y() == scr.top(),
   "pos=(%d,%d)" % (mw.x(), mw.y()))
# 右 / 下边缘贴边
mw.move(scr.right() + 1 - w + 10, scr.bottom() + 1 - h + 12)
app.processEvents()
ck("窗口：拖近右/下边缘自动贴边",
   mw.x() == scr.right() + 1 - w and mw.y() == scr.bottom() + 1 - h,
   "pos=(%d,%d) 期望=(%d,%d)" % (mw.x(), mw.y(), scr.right() + 1 - w,
                                 scr.bottom() + 1 - h))
# 屏幕中间不吸附
mx, my = scr.left() + 120, scr.top() + 90
mw.move(mx, my)
app.processEvents()
ck("窗口：屏幕中间不吸附", (mw.x(), mw.y()) == (mx, my),
   "pos=(%d,%d)" % (mw.x(), mw.y()))
# 贴边后窗口仍完整可见（不隐藏、不出屏）
ck("窗口：贴边后完整落在工作区内",
   scr.intersects(mw.frameGeometry())
   and mw.frameGeometry().left() >= scr.left() - 1
   and mw.frameGeometry().top() >= scr.top() - 1)

# 「初始化位置」→ 桌面正中央
mw._reset_position()
ck("窗口：托盘『初始化位置』回桌面正中", abs(mw.x() - cx) <= 1 and abs(mw.y() - cy) <= 1,
   "pos=(%d,%d) 期望=(%d,%d)" % (mw.x(), mw.y(), cx, cy))

# 关闭位置写入 settings.json；再次打开自动回到上次位置
mw._save_settings()
data = json.load(open(os.path.join(BOX, "settings.json"), encoding="utf-8"))
ck("窗口：位置已写入 settings.json", data.get("win_pos") == [mw.x(), mw.y()],
   str(data.get("win_pos")))
mw.move(60, 50)
app.processEvents()
mw._save_settings()
mw2 = MainWindow()
mw2.show()
ck("窗口：再次打开自动回到上次位置", (mw2.x(), mw2.y()) == (60, 50),
   "pos=(%d,%d)" % (mw2.x(), mw2.y()))
# 异常位置兜底：win_pos 不在任何屏幕 → 回正中
mw2._save_settings = lambda: None
data2 = dict(data)
data2["win_pos"] = [-9999, -9999]
json.dump(data2, open(os.path.join(BOX, "settings.json"), "w", encoding="utf-8"),
          ensure_ascii=False)
mw3 = MainWindow()
ck("窗口：坐标不在任何屏幕时回正中",
   abs(mw3.x() - cx) <= 1 and abs(mw3.y() - cy) <= 1,
   "pos=(%d,%d)" % (mw3.x(), mw3.y()))

failed = [n for n, c, _ in R if not c]
print("\n==== 行事历 UI 探针 ==== total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, c, _ in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
