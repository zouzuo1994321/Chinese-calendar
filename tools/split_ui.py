# -*- coding: utf-8 -*-
"""把 ui_main.py 按类边界拆分为 ui/ 包（theme / page / agenda / dialogs + MainWindow）。

按 AST 行号机械切分，拆完用 AST 复核方法归属与未解析名。
"""
import ast
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "ui_main.py")

with io.open(SRC, encoding="utf-8") as f:
    lines = f.read().splitlines(keepends=True)


def block(a, b):
    return "".join(lines[a - 1:b])


tree = ast.parse("".join(lines))
spans = {}
for n in tree.body:
    spans[getattr(n, "name", None)] = (n.lineno, n.end_lineno)

paths_blk = block(44, 84)
theme_blk = block(87, 234)
autostart_blk = block(238, 270)
page_blk = block(273, 928)
agenda_panel_blk = block(931, 1182)
sanqing_blk = block(1185, 1407)
agenda_import_blk = block(1410, 1490)
agenda_export_blk = block(1493, 1566)
mainwindow_blk = block(1569, 2070)
bazi_blk = block(2074, len(lines))

# ---- ui/theme.py -----------------------------------------------------------
paths_blk = paths_blk.replace(
    "_BASE = os.path.dirname(os.path.abspath(__file__))",
    "_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))"
    "   # ui/ 的上一级 = 工程根")
theme_src = '''# -*- coding: utf-8 -*-
"""印刷主题层：素材路径 / 调色板 / 字体族 / 位图缓存（ui 包公共底座）。"""
import os
import sys

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter,
                           QPen, QPixmap)

from calendar_app import fonts as calendar_app_fonts


''' + paths_blk + "\n\n" + theme_blk

# ---- ui/page.py ------------------------------------------------------------
page_src = '''# -*- coding: utf-8 -*-
"""撕页日历主页自绘控件（CalendarPage）。"""
from datetime import date, datetime

from PySide6.QtCore import (QPoint, QRect, QRectF, Qt, QTime, QTimer,
                            QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter,
                           QPen, QPixmap, QCursor)
from PySide6.QtWidgets import QApplication, QComboBox, QWidget

from calendar_app import fonts as calendar_app_fonts
from calendar_app.engine import get_day_info, SHENGXIAO_LIST
from calendar_app import version as VER

from ui.theme import (_font, _lf_asset, _paper_pixmap, _pix_cached,
                      _pix_scaled, _tone_of, palette_for, use_builtin_fonts,
                      EN_FONT, IMG_BAGUA, INK, NUM_FONT, PAPER, PAPER_EDGE,
                      ZH_FONT, ZH_SONG, ZH_WISDOM, _ZODIAC_DIR)


''' + page_blk

# ---- ui/agenda.py ----------------------------------------------------------
agenda_src = '''# -*- coding: utf-8 -*-
"""行事历面板与导入 / 导出对话框（AgendaPanel · AgendaImport/ExportDialog）。"""
import os

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QFileDialog,
                               QHBoxLayout, QLabel, QPushButton,
                               QPlainTextEdit, QVBoxLayout, QWidget)

from calendar_app import fonts as calendar_app_fonts
from calendar_app.agenda_pdf import (export_agenda, get_import_date,
                                     get_override, import_agenda, load_cache,
                                     make_agenda_template, match_current_month,
                                     record_end_date, save_override)
from calendar_app.engine import match_current_month as _match_month  # noqa: F401

from ui.theme import (_font, palette_for, PAPER, PAPER_EDGE, use_builtin_fonts,
                      ZH_FONT, ZH_SONG)


''' + agenda_panel_blk + "\n\n" + agenda_import_blk + "\n\n" + agenda_export_blk

# ---- ui/dialogs.py ---------------------------------------------------------
dialogs_src = '''# -*- coding: utf-8 -*-
"""次级对话框：祭拜三清（SanqingDialog）· 八字录入（BaziDialog）。"""
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QGridLayout,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QSpinBox, QVBoxLayout)

from calendar_app.engine import bazi_day_report, compute_eightchar

from ui.theme import (_font, _tinted_pixmap, IMG_XIANGLU, IMG_ZUSHIYE,
                      ZH_FONT, ZH_SONG)


''' + sanqing_blk + "\n\n" + bazi_blk

# ---- ui_main.py（保留 MainWindow + 兼容再导出） ------------------------------
new_main = '''# -*- coding: utf-8 -*-
"""肆月日历 - 主窗口（MainWindow）与模块门面。

2026-09-28 结构整理：原 2100+ 行单文件拆分为 ui/ 包 ——
  ui/theme.py    素材路径 / 调色板 / 字体族 / 位图缓存（公共底座）
  ui/page.py     CalendarPage 撕页日历主页自绘
  ui/agenda.py   AgendaPanel + 行事历导入 / 导出对话框
  ui/dialogs.py  祭拜三清 / 八字录入对话框
  ui_main.py     MainWindow + 对外再导出（兼容旧 import 路径与校验脚本）
"""
import json
import os
import sys
from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (QApplication, QLabel, QMainWindow, QMenu,
                               QMessageBox, QSystemTrayIcon, QWidget,
                               QVBoxLayout)

try:
    import winreg
except Exception:   # 非 Windows 平台（开发用）降级
    winreg = None

from calendar_app import fonts as calendar_app_fonts
from calendar_app import version as VER
from calendar_app.agenda_pdf import load_cache, import_agenda
from calendar_app.bridge import BRIDGE
from calendar_app.engine import analyze_zodiac_day, bazi_day_report, get_day_info

from ui.theme import (COLOR_CHIPS, EN_FONT, IMG_BAGUA, IMG_ICON_BILIBILI,
                      IMG_ICON_GITHUB, IMG_ICON_WEIBO, IMG_LOGO, IMG_XIANGLU,
                      IMG_ZUSHIYE, INK, NUM_FONT, PAPER, PAPER_EDGE,
                      SETTINGS_PATH, ZH_FONT, ZH_SONG, ZH_WISDOM, _LF_DIR,
                      _ZODIAC_DIR, _font, _lf_asset, _mail_pixmap,
                      _paper_pixmap, _pix_cached, _pix_scaled, _tinted_pixmap,
                      _tone_of, palette_for, use_builtin_fonts)
from ui.page import CalendarPage
from ui.agenda import AgendaPanel, AgendaExportDialog, AgendaImportDialog
from ui.dialogs import BaziDialog, SanqingDialog


''' + autostart_blk + "\n\n" + mainwindow_blk

os.makedirs(os.path.join(ROOT, "ui"), exist_ok=True)
init = os.path.join(ROOT, "ui", "__init__.py")
if not os.path.exists(init):
    io.open(init, "w", encoding="utf-8").write(
        '"""ui 包：撕页日历界面层（theme / page / agenda / dialogs / 主窗口）。"""\n')

for name, text in (("ui/theme.py", theme_src), ("ui/page.py", page_src),
                   ("ui/agenda.py", agenda_src), ("ui/dialogs.py", dialogs_src),
                   ("ui_main.py", new_main)):
    io.open(os.path.join(ROOT, name), "w", encoding="utf-8").write(text)
    print("written", name, len(text.splitlines()), "lines")

# AST 复核：方法归属 + 每个模块未解析名
for mod in ("ui/theme.py", "ui/page.py", "ui/agenda.py", "ui/dialogs.py",
            "ui_main.py"):
    path = os.path.join(ROOT, mod)
    tree = ast.parse(io.open(path, encoding="utf-8").read())
    defined = set(dir(__builtins__)) if False else set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            defined.add(n.name)
        elif isinstance(n, ast.Assign):
            defined.update(t.id for t in n.targets if isinstance(t, ast.Name))
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                defined.add((a.asname or a.name).split(".")[0])
    used = {x.id for x in ast.walk(tree) if isinstance(x, ast.Name)
            and isinstance(x.ctx, ast.Load)}
    missing = sorted(used - defined)
    print("%-14s classes=%s 未解析名=%s" % (
        mod, [n.name for n in tree.body if isinstance(n, ast.ClassDef)],
        missing[:24]))
