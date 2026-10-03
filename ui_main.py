# -*- coding: utf-8 -*-
"""肆月日历 - 主窗口（MainWindow）与模块门面。

2026-09-28 结构整理：原 2100+ 行单文件拆分为 ui/ 包 ——
  ui/theme.py    素材路径 / 调色板 / 字体族 / 位图缓存（公共底座）
  ui/page.py     CalendarPage 撕页日历主页自绘
  ui/agenda.py   AgendaPanel + 行事历导入 / 导出对话框
  ui/dialogs.py  祭拜三清 / 八字录入对话框
  ui_main.py     MainWindow + 对外再导出（兼容旧 import 路径与校验脚本）
"""
import ctypes
import json
import os
import sys
from datetime import date, datetime, timedelta

from PySide6.QtCore import (QDate, QEasingCurve, QPoint, QRect, QRectF, Qt,
                            QTimer, QVariantAnimation)
from PySide6.QtGui import (QColor, QFont, QIcon, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog,
                               QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QMainWindow, QMenu, QMessageBox, QPushButton,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

try:
    import winreg
except Exception:   # 非 Windows 平台（开发用）降级
    winreg = None

from calendar_app import fonts as calendar_app_fonts
from calendar_app import version as VER
from calendar_app.agenda_pdf import load_cache, import_agenda
from calendar_app.bridge import BRIDGE
from calendar_app.engine import analyze_zodiac_day, bazi_day_report, get_day_info

# 兼容再导出：v1.8.0 把 ui_main 拆成 ui/ 包后，此块把原先在 ui_main 命名空间里的
# 素材路径 / 调色板 / 图片缓存函数继续暴露出来，供 tools/dev_checks/* 与外部引用，
# 故其中若干名字在本文件内并不直接使用 —— 属有意为之，勿删。
from ui.theme import (  # noqa: F401
    COLOR_CHIPS, EN_FONT, IMG_BAGUA, IMG_ICON_BILIBILI,
    IMG_ICON_GITHUB, IMG_ICON_WEIBO, IMG_LOGO, IMG_XIANGLU,
    IMG_ZUSHIYE, INK, NUM_FONT, PAPER, PAPER_EDGE,
    SETTINGS_PATH, ZH_FONT, ZH_SONG, ZH_WISDOM, _LF_DIR,
    _PIX_CACHE, _PIX_SCALED_CACHE, _PAPER_CACHE, _ZODIAC_DIR,
    _font, _lf_asset, _mail_pixmap, _paper_pixmap,
    _pix_cached, _pix_scaled, _tinted_pixmap, _tone_of,
    palette_for, settings_path, use_builtin_fonts)
from ui.page import CalendarPage  # noqa: F401  兼容再导出
from ui.agenda import AgendaPanel, AgendaExportDialog, AgendaImportDialog  # noqa: F401
from ui.dialogs import BaziDialog, SanqingDialog  # noqa: F401  兼容再导出


_AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


# ---------- 任务栏按钮的即时增删（ITaskbarList，v1.9.14） ----------
# 无边框窗口是 WS_POPUP，任务栏按钮由扩展样式位（WS_EX_APPWINDOW / WS_EX_TOOLWINDOW）决定。
# 但窗口**当前可见**时仅改样式位，shell 不会立刻跟着增删按钮 —— ITaskbarList::AddTab /
# DeleteTab 是文档指定的即时增删接口（4=AddTab、5=DeleteTab），可免去 hide→show 的闪烁。
_CLSID_TASKBARLIST = "56FDF344-FD6D-11d0-958A-006097C9A090"
_IID_ITASKBARLIST = "56FDF342-FD6D-11d0-958A-006097C9A090"


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort), ("Data4", ctypes.c_ubyte * 8)]


def _guid(text):
    import uuid
    u = uuid.UUID(text)
    return _GUID(u.time_low, u.time_mid, u.time_hi_version,
                 (ctypes.c_ubyte * 8)(*u.bytes[8:]))


_TASKBAR_CB = None          # 成功 → callable(idx, hwnd)->bool；失败 → False
_TASKBAR_TRIED = False


def _taskbar_call(idx, hwnd):
    """调用 ITaskbarList 的 vtable 方法（4=AddTab / 5=DeleteTab）。成功且 HRESULT=0 返回 True。"""
    global _TASKBAR_CB, _TASKBAR_TRIED
    if sys.platform != "win32":
        return False
    if not _TASKBAR_TRIED:
        _TASKBAR_TRIED = True
        try:
            ole32 = ctypes.windll.ole32
            # 已初始化过会返回 S_FALSE / RPC_E_CHANGED_MODE，忽略（Qt 已为 GUI 线程初始化 OLE）
            ole32.CoInitializeEx(None, 0x2)
            clsid, iid = _guid(_CLSID_TASKBARLIST), _guid(_IID_ITASKBARLIST)
            ptr = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(ctypes.byref(clsid), None, 0x1 | 0x4,
                                        ctypes.byref(iid), ctypes.byref(ptr))
            if hr == 0 and ptr.value:
                vtbl_addr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
                vtbl = ctypes.cast(ctypes.c_void_p(vtbl_addr),
                                   ctypes.POINTER(ctypes.c_void_p))
                proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                                           ctypes.c_void_p)
                proto(vtbl[3])(ptr, None)          # HrInit

                def _call(i, h):
                    return proto(vtbl[i])(ptr, ctypes.c_void_p(int(h))) == 0
                _TASKBAR_CB = _call                # 闭包持有 ptr，保证 COM 对象存活
            else:
                _TASKBAR_CB = False
        except Exception:
            _TASKBAR_CB = False
    if not _TASKBAR_CB:
        return False
    try:
        return bool(_TASKBAR_CB(idx, hwnd))
    except Exception:
        return False


def set_autostart(enabled: bool, app_name: str, exe_path: str) -> bool:
    """在 HKCU\\...\\Run 下增删当前用户开机启动项。返回是否成功。"""
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY,
                             0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def get_autostart(app_name: str) -> bool:
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _AUTOSTART_KEY)
        val, _ = winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return bool(val)
    except Exception:
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("%s v%s (Build %s)" % (
            VER.APP_NAME, VER.APP_VERSION, VER.BUILD_CODE))
        if os.path.exists(IMG_LOGO):
            self.setWindowIcon(QIcon(IMG_LOGO))
        # 无边框窗口建出来是 WS_POPUP，任务栏图标的「有 / 无」完全由扩展样式位决定：
        #   WS_EX_APPWINDOW（有按钮） ⇄ WS_EX_TOOLWINDOW（无按钮） —— 见 _set_taskbar。
        # 交互规格（v1.9.14，用户逐项确认；整体参照「悬浮窗」）：
        #   启动                    → 有任务栏图标
        #   点「最小化」            → 窗口**留在桌面原地不动**，仅摘掉任务栏图标
        #   点「关闭」              → 窗口与任务栏图标都消失，软件驻留系统托盘
        #   关闭后点「托盘左键」    → 只把桌面窗口叫回来，**不带**任务栏图标
        #   关闭后「托盘右键→显示/隐藏」→ 叫回桌面窗口，**带**任务栏图标
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self._taskbar_mode = True          # 目标态：True＝任务栏有按钮
        margin = 8
        self.setFixedSize(CalendarPage.PAGE_W + margin * 2,
                          CalendarPage.PAGE_H + AgendaPanel.PANEL_H + margin * 2 + 4)

        central = QWidget()
        central.setStyleSheet("background:#f3f0e6;")   # 与叠页纸色一致（去掉深色外框）
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(margin, margin, margin, margin)
        v.setSpacing(4)

        self.page = CalendarPage()
        v.addWidget(self.page, 0, Qt.AlignHCenter)

        self.agenda_month = AgendaPanel(mode="month")
        self.agenda_month.theme_info = self.page.info   # 标题带颜色与当日主题联动
        v.addWidget(self.agenda_month, 0, Qt.AlignHCenter)
        self.agenda_day = AgendaPanel(mode="day")
        self.agenda_day.theme_info = self.page.info
        self.agenda_day._sync_body()   # theme_info 注入后刷新 day 正文（日期键依赖它）
        v.addWidget(self.agenda_day, 0, Qt.AlignHCenter)

        # ---- 状态 ----
        self.settings = self._load_settings()
        self.zodiac = self.settings.get("zodiac")
        self.bazi = self.settings.get("bazi")            # 个人八字（compute_eightchar 结果）
        self._bazi_input = self.settings.get("bazi_input")  # [年,月,日,时,农历?] 用于回填
        self._opacity = max(30, min(100, int(self.settings.get("opacity", 100))))
        self.page.opacity_slider.setValue(self._opacity)   # 先于信号连接，避免误存盘
        self.setWindowOpacity(self._opacity / 100.0)
        self._month_visible = self.settings.get("month_visible",
                                                self.settings.get("agenda_visible", True))
        self._day_visible = self.settings.get("day_visible",
                                              self.settings.get("agenda_visible", True))
        # 已录入八字：生肖框自动联动八字年支生肖（v1.9.3）
        _bx_sx = (self.bazi or {}).get("shengxiao")
        if _bx_sx:
            self.zodiac = _bx_sx
        if self.zodiac:
            idx = self.page.zodiac_box.findData(self.zodiac)
            if idx >= 0:
                self.page.zodiac_box.setCurrentIndex(idx)
        self._apply_zodiac(update_page=False)
        self.agenda_month.refresh_current()
        self.agenda_day.refresh_current()
        self._apply_panel_visibility()

        # ---- 信号 ----
        self.page.zodiac_box.currentIndexChanged.connect(self._on_zodiac_changed)
        self.page.btn_bazi.clicked.connect(self._open_bazi)
        self.page.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.page.btn_import.clicked.connect(self._on_import)
        self.page.btn_prev.clicked.connect(lambda: self._flip(-1))
        self.page.btn_next.clicked.connect(lambda: self._flip(1))
        self.page.btn_today.clicked.connect(self._go_today)
        self.page.btn_tear.clicked.connect(self._tear)
        self.page.btn_about.clicked.connect(self._about)
        self.page.btn_min.clicked.connect(self._minimize_to_float)
        self.page.btn_close.clicked.connect(self.close)
        self.page.month_toggle_requested.connect(lambda: self._toggle_panel("month"))
        self.page.day_toggle_requested.connect(lambda: self._toggle_panel("day"))
        self.page.date_pressed_ten_times.connect(self._open_sanqing)

        # ---- 每日 0:00 自动撕页（跨日检测，每 30s 轮询，兼顾休眠唤醒） ----
        self._midnight_timer = QTimer(self)
        self._midnight_timer.setInterval(30000)
        self._midnight_timer.timeout.connect(self._auto_tear)
        self._midnight_timer.start()

        # ---- 系统托盘（默认以托盘图标形式常驻；关闭窗口仅隐藏到托盘） ----
        self.tray = None
        self._setup_tray()

        self._anim_label = None
        self._drag_pos = None
        self.bridge = BRIDGE

        # 初始窗口高度：按两个行事历面板可见状态定高
        self._apply_window_height()

        # ---- 窗口位置：记忆上次关闭位置；拖近屏幕边缘自动贴边（不隐藏） ----
        self._pos_save_timer = QTimer(self)
        self._pos_save_timer.setSingleShot(True)
        self._pos_save_timer.setInterval(600)
        self._pos_save_timer.timeout.connect(self._save_settings)
        self._restore_or_center_position()

    # ---------- 行事历面板可见性（本月 / 本日 独立开关） ----------
    def _apply_panel_visibility(self):
        self.page.set_panels_visible(self._month_visible, self._day_visible)
        self.agenda_month.setVisible(self._month_visible)
        self.agenda_day.setVisible(self._day_visible)

    def _apply_window_height(self):
        margin = 8
        h = CalendarPage.PAGE_H + margin * 2 + 4
        if self._month_visible:
            h += AgendaPanel.PANEL_H
        if self._day_visible:
            h += AgendaPanel.PANEL_H
        self.setFixedSize(CalendarPage.PAGE_W + margin * 2, h)

    def _toggle_panel(self, which: str):
        if which == "month":
            self._month_visible = not self._month_visible
        else:
            self._day_visible = not self._day_visible
        self._apply_panel_visibility()
        self._apply_window_height()
        self._save_settings()

    # ---------- 设置 ----------
    def _load_settings(self):
        try:
            with open(settings_path(), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_settings(self):
        try:
            p = settings_path()
            d = os.path.dirname(p)
            if d and not os.path.isdir(d):
                os.makedirs(d, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"zodiac": self.zodiac,
                           "bazi": self.bazi,
                           "bazi_input": self._bazi_input,
                           "opacity": self._opacity,
                           "last_date": self.page.info["date"].isoformat(),
                           "month_visible": self._month_visible,
                           "day_visible": self._day_visible,
                           "win_pos": [self.x(), self.y()],
                           "autostart": self.settings.get("autostart", False)}, f,
                          ensure_ascii=False)
        except Exception:
            pass

    # ---------- 窗口透明度 ----------
    def _on_opacity_changed(self, v):
        self._opacity = int(v)
        self.setWindowOpacity(self._opacity / 100.0)
        self._save_settings()

    # ---------- 生肖 ----------
    def _on_zodiac_changed(self):
        self._apply_zodiac()

    def _apply_zodiac(self, update_page=True):
        try:
            self.zodiac = self.page.zodiac_box.currentData()
            rep = None
            # 已录入八字：以八字年支生肖为基准，并叠加八字推演
            brep = bazi_day_report(self.bazi, self.page.info) if self.bazi else None
            if brep and brep.get("shengxiao"):
                rep = analyze_zodiac_day(self.page.info, brep["shengxiao"])
                rep["name"] = brep["shengxiao"]
                rep["bazi_text"] = brep["text"]
                # v1.9.15：录入八字后**直接采用子平法专业分**（日主强弱 + 喜用神 +
                # 流日契合度）。旧版与「仅看年支生肖」的分取平均，等于把专业信号
                # 稀释掉一半，且生肖口径已被八字报告完全涵盖。
                rep["score"] = brep["score"]
            elif brep:
                rep = brep
                rep["name"] = "八字"
            elif self.zodiac:
                rep = analyze_zodiac_day(self.page.info, self.zodiac)
                rep["name"] = self.zodiac
            self.page.set_zodiac_report(rep)
        except Exception:
            # 任何推演异常都不应让页面停更：兜底清空，避免整页绘制崩溃
            try:
                self.page.set_zodiac_report(None)
            except Exception:
                pass
        self._save_settings()

    # ---------- 八字录入 ----------
    def _open_bazi(self):
        dlg = BaziDialog(self, self._bazi_input)
        # v1.9.5 根因修复：PySide6 6.11 实例上访问 dlg.Accepted 会 AttributeError
        # （枚举只在类上），异常被 Qt 槽吞掉 → 保存/联动/落盘全部没执行。
        # 必须用类级 QDialog.DialogCode.Accepted 比较。
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg.cleared:          # 用户点「清除」：撤销八字推演
                self.bazi = None
                self._bazi_input = None
            else:                     # 保存：写入四柱并持久化
                self.bazi = dlg.bazi
                self._bazi_input = dlg.input_list
                self._sync_zodiac_from_bazi()   # 八字↔生肖联动（v1.9.3）
            self._save_settings()
            self._apply_zodiac()
        dlg.deleteLater()

    def _sync_zodiac_from_bazi(self):
        """八字↔生肖联动：由八字年支自动识别生肖并选中下拉框（v1.9.3）。"""
        sx = (self.bazi or {}).get("shengxiao")
        if not sx:
            return
        idx = self.page.zodiac_box.findData(sx)
        if idx >= 0 and self.page.zodiac_box.currentData() != sx:
            self.page.zodiac_box.setCurrentIndex(idx)   # 触发 _on_zodiac_changed

    # ---------- 翻页 / 撕页 ----------
    def _flip(self, delta):
        new_date = self.page.info["date"] + timedelta(days=delta)
        self._animate_page("slide", delta)
        self._set_date(new_date)

    def _tear(self):
        new_date = self.page.info["date"] + timedelta(days=1)
        self._animate_page("tear")
        self._set_date(new_date)

    def _auto_tear(self):
        """跨日（0:00 之后）自动撕页到新的一天。"""
        today = date.today()
        if self.page.info["date"] < today:
            self._animate_page("tear")
            self._set_date(today)

    # ---------- 系统托盘 ----------
    def _make_tray_icon(self):
        """托盘图标：统一使用 logo.png（缺失时兜底为手绘红色「历」字）。"""
        if os.path.exists(IMG_LOGO):
            pm = QPixmap(IMG_LOGO)
            if not pm.isNull():
                return QIcon(pm.scaled(64, 64, Qt.KeepAspectRatio,
                                       Qt.SmoothTransformation))
        pm = QPixmap(64, 64)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#c0392b"))
        p.drawRoundedRect(QRectF(2, 2, 60, 60), 12, 12)
        p.setPen(QPen(QColor("#fdf6e3")))
        p.setFont(_font(38, ZH_FONT, QFont.Black))
        p.drawText(pm.rect(), Qt.AlignCenter, "历")
        p.end()
        return QIcon(pm)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self._make_tray_icon())
        self.tray.setToolTip("%s v%s" % (VER.APP_NAME, VER.APP_VERSION))
        menu = QMenu()
        act_toggle = menu.addAction("显示 / 隐藏")
        act_toggle.triggered.connect(lambda: self._toggle_visible())
        act_reset = menu.addAction("初始化位置")
        act_reset.triggered.connect(lambda: self._reset_position())
        act_about = menu.addAction("关于本软件")
        act_about.triggered.connect(lambda: self._about())
        menu.addSeparator()
        act_quit = menu.addAction("退出")
        act_quit.triggered.connect(lambda: self._quit_app())
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _toggle_visible(self):
        """托盘右键菜单「显示 / 隐藏」：隐藏 ↔ 显示。

        v1.9.14 规格：走这条路的**显示**是唯一会让窗口**带上任务栏图标**的入口。
        """
        if self.isVisible():
            self.hide()
        else:
            self._show_window(taskbar=True)

    def _on_tray_activated(self, reason):
        """托盘左键单击 / 双击：只把桌面窗口叫回来，**不带**任务栏图标（v1.9.14 规格）。"""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self._show_window(taskbar=False)

    def _show_window(self, taskbar: bool):
        """按指定任务栏模式把窗口显示出来（**先定样式位、再 show**，shell 才会按新位建按钮）。"""
        self._set_taskbar(taskbar)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        if self.tray is not None:
            self.tray.hide()
        self._save_settings()
        QApplication.quit()

    def _go_today(self):
        """回到当日。"""
        today = date.today()
        if self.page.info["date"] == today:
            return
        delta = 1 if today > self.page.info["date"] else -1
        self._animate_page("slide", delta)
        self._set_date(today)

    def _set_date(self, d: date):
        self.page.set_date(d)
        self.agenda_month.theme_info = self.page.info
        self.agenda_day.theme_info = self.page.info
        self._apply_zodiac(update_page=False)
        self.agenda_month.refresh_current()
        self.agenda_day.refresh_current()
        self._save_settings()

    def _animate_page(self, mode, direction=1):
        """翻页 / 撕页动画：抓取当前页快照，滑动 + 渐隐。"""
        if self._anim_label:
            self._anim_label.deleteLater()
            self._anim_label = None
        pix = self.page.grab()
        lab = QLabel(self)
        lab.setPixmap(pix)
        start = self.page.mapTo(self, QPoint(0, 0))
        lab.move(start)
        lab.resize(self.page.size())
        lab.show()
        self._anim_label = lab

        opacity = QGraphicsOpacityEffect(lab)
        opacity.setOpacity(1.0)
        lab.setGraphicsEffect(opacity)

        anim = QVariantAnimation(self)
        anim.setDuration(420 if mode == "tear" else 260)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def on_tick(t, lab=lab, opacity=opacity):
            opacity.setOpacity(1.0 - t)
            dy = t * (self.page.height() + 60) if mode == "tear" else t * 40 * direction
            dx = t * 160 * direction if mode == "slide" else t * 24
            lab.move(start + QPoint(int(dx), int(dy)))

        anim.valueChanged.connect(on_tick)
        anim.finished.connect(lambda: (lab.deleteLater(),
                                       setattr(self, "_anim_label", None)))
        anim.start()
        self._anim = anim

    # ---------- 导入行事历 ----------
    def _on_import(self):
        dlg = AgendaImportDialog(self)
        dlg.exec()
        if not dlg.imported:
            return
        records = load_cache()
        self.agenda_month.records = records
        self.agenda_month._match_current()
        self.agenda_month.update()
        self.agenda_day.records = records
        self.agenda_day._match_current()
        self.agenda_day.update()
        QMessageBox.information(self, "导入完成",
                                "行事历已更新，并自动定位到当前农历月。")

    # ---------- 关于 ----------
    def _about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("关于 %s" % VER.APP_NAME)
        dlg.setFixedWidth(430)
        root = QVBoxLayout(dlg)
        root.setContentsMargins(18, 16, 18, 14)
        info = (
            "<b>%s v%s</b>（Build %s）<br><br>"
            "纸质撕页风格农历通胜日历。<br>"
            "宜忌数据口径参考：两广·港澳通书（宋韶光 / 永经堂 / 广经堂）。<br>"
            "法定假日主题：当日整体切换红色印制。<br>"
            "已预留与《钦天监》对接接口。<br><br>"
            "%s<br>%s"
        ) % (VER.APP_NAME, VER.APP_VERSION, VER.BUILD_CODE,
             VER.COPYRIGHT, VER.LICENSE_NOTE)
        lb = QLabel(info)
        lb.setWordWrap(True)
        root.addWidget(lb)

        # 联系作者
        root.addWidget(QLabel("<hr>"))
        cap = QLabel("<b>联系作者</b>")
        root.addWidget(cap)
        ink = QColor("#5a5a50")
        contacts = [
            (IMG_ICON_GITHUB, "GitHub", "https://github.com/zouzuo1994321",
             "github.com/zouzuo1994321"),
            (IMG_ICON_BILIBILI, "哔哩哔哩", "https://space.bilibili.com/13715",
             "space.bilibili.com/13715"),
            (IMG_ICON_WEIBO, "微博", "https://weibo.com/u/5189652182",
             "weibo.com/u/5189652182"),
            (None, "邮箱", "mailto:921103025@qq.com", "921103025@qq.com"),
        ]
        for icon_path, name, url, text in contacts:
            row = QHBoxLayout()
            ic = QLabel()
            ic.setFixedSize(22, 22)
            if icon_path:
                ic.setPixmap(_tinted_pixmap(icon_path, ink, 22))
            else:
                ic.setPixmap(_mail_pixmap(ink, 22))
            row.addWidget(ic)
            nm = QLabel(name)
            nm.setFixedWidth(66)
            row.addWidget(nm)
            lk = QLabel('<a href="%s" style="color:#c0392b;text-decoration:none;">%s</a>'
                        % (url, text))
            lk.setOpenExternalLinks(True)
            lk.setTextInteractionFlags(Qt.TextBrowserInteraction)
            row.addWidget(lk)
            row.addStretch(1)
            root.addLayout(row)

        # 开机自动启动开关
        cb = QCheckBox("开机自动启动")
        cb.setChecked(bool(self.settings.get("autostart", False)))
        cb.stateChanged.connect(self._on_autostart_toggle)
        root.addWidget(cb)

        ok = QPushButton("确定")
        ok.setFixedWidth(80)
        ok.clicked.connect(dlg.accept)
        hb = QHBoxLayout()
        hb.addStretch(1)
        hb.addWidget(ok)
        root.addLayout(hb)
        dlg.exec()

    def _on_autostart_toggle(self, state):
        enabled = bool(state)
        ok = set_autostart(enabled, VER.APP_NAME,
                           os.path.abspath(sys.executable) if getattr(sys, "frozen", False)
                           else os.path.abspath("main.py"))
        self.settings["autostart"] = enabled if ok else self.settings.get("autostart", False)
        self._save_settings()
        if not ok:
            QMessageBox.warning(self, "自动启动",
                                "无法写入开机启动项（可能需要以管理员运行，"
                                "或当前为开发模式）。")

    # ---------- 祭拜三清（按住中间日期累计 10 次触发） ----------
    def _open_sanqing(self):
        dlg = SanqingDialog(self)
        dlg.exec()


    # ---------- 无边框拖动 ----------
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton and self._drag_pos:
            self.move(ev.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._drag_pos = None
        super().mouseReleaseEvent(ev)

    # ---------- 窗口位置：记忆 / 贴边吸附 / 初始化 ----------
    SNAP_PX = 14          # 距屏幕工作区边缘 ≤14px 时吸附贴边（只贴边，绝不隐藏）
    _snapping = False     # 类级缺省，保证构造期 moveEvent 也安全

    def _avail_geo(self):
        """窗口当前所在屏幕的工作区（多显示器下跟随窗口所在屏）。"""
        try:
            scr = self.screen() or QApplication.primaryScreen()
        except Exception:
            scr = QApplication.primaryScreen()
        return (scr or QApplication.primaryScreen()).availableGeometry()

    def _center_pos(self, scr):
        return QPoint(scr.left() + max(0, (scr.width() - self.width()) // 2),
                      scr.top() + max(0, (scr.height() - self.height()) // 2))

    def _restore_or_center_position(self):
        """恢复上次关闭位置；无记录 / 坐标不在任何屏幕（如拔了显示器）则回正中。"""
        pos = (self.settings or {}).get("win_pos")
        x = y = None
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            try:
                x, y = int(pos[0]), int(pos[1])
            except (TypeError, ValueError):
                x = y = None
        if x is None or not any(s.geometry().contains(x, y)
                                for s in QApplication.screens()):
            c = self._center_pos(self._avail_geo())
            x, y = c.x(), c.y()
        self.move(x, y)

    def _reset_position(self):
        """托盘「初始化位置」：回桌面正中央（异常位置的兜底出口），并立即记忆。"""
        c = self._center_pos(self._avail_geo())
        self.move(c)
        self._save_settings()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    # ---------- 任务栏图标：有 / 无 两态切换（v1.9.14） ----------
    def _minimize_to_float(self):
        """「最小化」按钮：窗口**留在桌面原地不动**，只把任务栏图标摘掉。

        v1.9.14 用户规格：「最小化后任务栏里的图标不需要存在，桌面的界面保持存在」。
        故这里**不调用** `showMinimized()`（那是真最小化），只切到悬浮窗态（无任务栏按钮）。
        """
        self._set_taskbar(False, resync=True)

    def _write_exstyle(self, taskbar: bool):
        """把「有 / 无任务栏按钮」写进原生扩展样式位 `GWL_EXSTYLE`。

        - 有按钮：置 `WS_EX_APPWINDOW`、清 `WS_EX_TOOLWINDOW`
        - 无按钮：置 `WS_EX_TOOLWINDOW`、清 `WS_EX_APPWINDOW`（同时不进 Alt+Tab，符合悬浮窗）
        不动 `WS_CAPTION` / `WS_THICKFRAME`：窗口仍是无边框、定尺寸。位已正确时直接返回。
        """
        if sys.platform != "win32":
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            get = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            setl = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            get.restype = ctypes.c_ssize_t
            get.argtypes = [ctypes.c_void_p, ctypes.c_int]
            setl.restype = ctypes.c_ssize_t
            setl.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            ex = get(hwnd, GWL_EXSTYLE)
            if taskbar:
                want = (ex | WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW
            else:
                want = (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
            if want != ex:
                setl(hwnd, GWL_EXSTYLE, want)
                SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER = 1, 2, 4
                SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x10, 0x20
                user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                    SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER
                                    | SWP_NOACTIVATE | SWP_FRAMECHANGED)
        except Exception:
            pass

    def _sync_taskbar_tab(self, fallback: bool = False):
        """显式让 shell 立刻按 `self._taskbar_mode` 增删任务栏按钮。

        ⚠ **为什么光改扩展样式位不够**（v1.9.15 用户实测）：
        窗口**由隐藏变可见**时，若它此前已被 shell 归入「无任务栏按钮」一类（`WS_EX_TOOLWINDOW`），
        仅把该位清掉、再补上 `WS_EX_APPWINDOW`，shell **不会**自动把按钮加回来 ——
        表现为「托盘右键『显示 / 隐藏』唤回窗口，但任务栏仍没有图标」。
        文档指定的即时增删接口是 `ITaskbarList::AddTab(4) / DeleteTab(5)`。
        `fallback=True` 时若 COM 不可用，退化为 hide→show 让 shell 重新枚举。
        """
        if sys.platform != "win32":
            return
        try:
            hwnd = int(self.winId())
        except Exception:
            return
        if _taskbar_call(4 if self._taskbar_mode else 5, hwnd):
            return
        if fallback and self.isVisible():
            self.hide()
            self.showNormal()

    def _set_taskbar(self, taskbar: bool, resync: bool = False):
        """切到「有 / 无任务栏按钮」两态之一，并记进 `self._taskbar_mode`。

        `resync=True`（窗口**当前可见**时切换，如点「最小化」）会立即显式增删按钮。
        """
        self._taskbar_mode = bool(taskbar)
        self._write_exstyle(self._taskbar_mode)
        if resync:
            self._sync_taskbar_tab(fallback=True)

    def showEvent(self, ev):
        super().showEvent(ev)
        # 每次显示都按当前模式自愈（幂等）：先写样式位，再**延到事件循环下一拍**显式
        # 增删任务栏按钮 —— 确保原生窗口已完成 ShowWindow，shell 才会理会 AddTab。
        self._write_exstyle(self._taskbar_mode)
        QTimer.singleShot(0, lambda: self._sync_taskbar_tab(fallback=False))

    def moveEvent(self, ev):
        if not self._snapping:
            g = self.frameGeometry()
            scr = self._avail_geo()
            x, y = self.x(), self.y()
            nx, ny = x, y
            if abs(x - scr.left()) <= self.SNAP_PX:
                nx = scr.left()
            elif abs((x + g.width()) - (scr.right() + 1)) <= self.SNAP_PX:
                nx = scr.right() + 1 - g.width()
            if abs(y - scr.top()) <= self.SNAP_PX:
                ny = scr.top()
            elif abs((y + g.height()) - (scr.bottom() + 1)) <= self.SNAP_PX:
                ny = scr.bottom() + 1 - g.height()
            if (nx, ny) != (x, y):
                self._snapping = True
                self.move(nx, ny)
                self._snapping = False
        t = getattr(self, "_pos_save_timer", None)
        if t:
            t.start()        # 防抖：停稳 0.6s 后记忆位置
        super().moveEvent(ev)

    def closeEvent(self, ev):
        self._save_settings()
        # 默认以托盘图标形式运行：点关闭仅隐藏到托盘，托盘菜单「退出」才真正退出。
        # v1.9.14 规格：关闭后「桌面窗口 + 任务栏图标」都消失 —— 切悬浮窗态再 hide，
        # 之后无论是托盘左键（不带图标）还是右键「显示/隐藏」（带图标）都按各自入口定。
        if self.tray is not None and self.tray.isVisible():
            ev.ignore()
            self._set_taskbar(False, resync=True)
            self.hide()
            return
        super().closeEvent(ev)
