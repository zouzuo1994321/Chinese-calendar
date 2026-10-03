# -*- coding: utf-8 -*-
"""真机诊断（v1.9.13）：无边框主窗口的原生样式位随「最小化」如何变化。

只观测、不修改源码。输出 GWL_STYLE / GWL_EXSTYLE / owner / IsIconic，
用于定位「最小化后任务栏按钮消失」的真正根因。
"""
import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.pop("QT_QPA_PLATFORM", None)

from PySide6.QtWidgets import QApplication           # noqa: E402

app = QApplication.instance() or QApplication([])
if app.platformName() in ("offscreen", "minimal", "vnc"):
    print("平台插件 = %s（需要真实平台）" % app.platformName())
    sys.exit(2)

from calendar_app import fonts as _fonts             # noqa: E402
_fonts.install_fonts()
from ui_main import MainWindow                       # noqa: E402

u = ctypes.windll.user32
u.IsIconic.argtypes = [ctypes.c_void_p]
u.IsIconic.restype = ctypes.c_bool
u.IsWindowVisible.argtypes = [ctypes.c_void_p]
u.IsWindowVisible.restype = ctypes.c_bool
u.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
u.GetWindow.restype = ctypes.c_void_p
GWL_STYLE, GWL_EXSTYLE = -16, -20
GW_OWNER = 4
_get = getattr(u, "GetWindowLongPtrW", u.GetWindowLongW)
_get.restype = ctypes.c_ssize_t
_get.argtypes = [ctypes.c_void_p, ctypes.c_int]

FLAGS = [
    ("WS_CAPTION", 0x00C00000, "style"),
    ("WS_SYSMENU", 0x00080000, "style"),
    ("WS_MINIMIZEBOX", 0x00020000, "style"),
    ("WS_MAXIMIZEBOX", 0x00010000, "style"),
    ("WS_THICKFRAME", 0x00040000, "style"),
    ("WS_POPUP", 0x80000000, "style"),
    ("WS_VISIBLE", 0x10000000, "style"),
    ("WS_EX_TOOLWINDOW", 0x00000080, "ex"),
    ("WS_EX_APPWINDOW", 0x00040000, "ex"),
    ("WS_EX_WINDOWEDGE", 0x00000100, "ex"),
    ("WS_EX_CLIENTEDGE", 0x00000200, "ex"),
]


def dump(tag, hwnd):
    style = _get(hwnd, GWL_STYLE)
    ex = _get(hwnd, GWL_EXSTYLE)
    owner = u.GetWindow(hwnd, GW_OWNER)
    print("[%s] hwnd=%s style=%s exstyle=%s owner=%s visible=%s iconic=%s"
          % (tag, hwnd, hex(style), hex(ex), owner,
             bool(u.IsWindowVisible(hwnd)), bool(u.IsIconic(hwnd))))
    on = []
    for nm, bit, kind in FLAGS:
        val = style if kind == "style" else ex
        if val & bit:
            on.append(nm)
    print("        置位: %s" % (", ".join(on) if on else "(无)"))


def pump(sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        app.processEvents()
        time.sleep(0.02)


win = MainWindow()
win._pos_save_timer.stop()
win.show()
pump(1.2)
hwnd = int(win.winId())
dump("show 后", hwnd)

win.showMinimized()
pump(1.2)
dump("最小化后", hwnd)

win.showNormal()
pump(0.8)
dump("还原后", hwnd)

# 尝试手动补 WS_EX_APPWINDOW，观察位变化（真机验证修法是否落到窗口上）
WS_EX_APPWINDOW = 0x00040000
_set = getattr(u, "SetWindowLongPtrW", u.SetWindowLongW)
_set.restype = ctypes.c_ssize_t
_set.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]
_set(hwnd, GWL_EXSTYLE, _get(hwnd, GWL_EXSTYLE) | WS_EX_APPWINDOW)
dump("补 WS_EX_APPWINDOW 后", hwnd)

if getattr(win, "tray", None) is not None:
    win.tray.hide()
win.hide()
pump(0.3)
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)
