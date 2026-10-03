# -*- coding: utf-8 -*-
"""真机探针：主窗口任务栏图标「有 / 无」两态切换（v1.9.14，悬浮窗交互规格）。

用户确认的规格：
  启动                     → 有任务栏图标（WS_EX_APPWINDOW）
  点「最小化」             → 窗口**留在桌面原地不动**，只摘掉任务栏图标（WS_EX_TOOLWINDOW）
  点「关闭」               → 窗口与任务栏图标都消失，驻留系统托盘
  关闭后「托盘左键」       → 只唤回桌面窗口，**不带**任务栏图标
  关闭后「托盘右键→显示/隐藏」→ 唤回桌面窗口，**带**任务栏图标

本探针在**真实平台**断言：
  ① ITaskbarList（COM）可创建 → 可见态切换能即时增删按钮；
  ② 启动 show 后 exstyle 含 WS_EX_APPWINDOW、不含 WS_EX_TOOLWINDOW；
  ③ `_minimize_to_float()` 后窗口**仍可见且未真最小化**（IsWindowVisible=True / IsIconic=False）、
     **位置与尺寸不变**，exstyle 翻到 WS_EX_TOOLWINDOW；
  ④ `close()` 后窗口不可见（隐藏到托盘），托盘对象仍在；
  ⑤ 关后 `_on_tray_activated(Trigger)`（托盘左键）→ 可见且**无**任务栏图标；
  ⑥ 再 `close()` 后 `_toggle_visible()`（托盘右键显示/隐藏）→ 可见且**有**任务栏图标。

⚠ 必须在真实平台跑（脚本内 pop 掉 QT_QPA_PLATFORM）；会短暂显示一个窗口（约 5 秒）。
"""
import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
os.environ.pop("QT_QPA_PLATFORM", None)              # 必须真实平台

from PySide6.QtWidgets import QApplication, QSystemTrayIcon  # noqa: E402

app = QApplication.instance() or QApplication([])
if app.platformName() in ("offscreen", "minimal", "vnc"):
    print("平台插件 = %s（需要真实平台，跳过）" % app.platformName())
    sys.exit(2)

from calendar_app import fonts as _fonts             # noqa: E402
_fonts.install_fonts()
import ui_main                                       # noqa: E402
from ui_main import MainWindow, _taskbar_call        # noqa: E402

# 记录 shell 增删调用：显示时应发 AddTab(4)、悬浮窗态应发 DeleteTab(5)
_CALLS = []
_orig_call = ui_main._taskbar_call


def _rec(i, h):
    ok = _orig_call(i, h)
    _CALLS.append((i, ok))
    return ok


ui_main._taskbar_call = _rec

user32 = ctypes.windll.user32
user32.IsIconic.argtypes = [ctypes.c_void_p]
user32.IsIconic.restype = ctypes.c_bool
user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
user32.IsWindowVisible.restype = ctypes.c_bool
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000
_get = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
_get.restype = ctypes.c_ssize_t
_get.argtypes = [ctypes.c_void_p, ctypes.c_int]

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


def pump(sec):
    t0 = time.time()
    while time.time() - t0 < sec:
        app.processEvents()
        time.sleep(0.02)


win = MainWindow()
win._pos_save_timer.stop()          # 别把探针的窗口位置写回用户设置
win.show()
pump(1.2)
hwnd = int(win.winId())

ex = _get(hwnd, GWL_EXSTYLE)
ck("启动态：窗口可见", bool(user32.IsWindowVisible(hwnd)))
ck("启动态：exstyle 含 WS_EX_APPWINDOW（有任务栏图标）",
   bool(ex & WS_EX_APPWINDOW) and not (ex & WS_EX_TOOLWINDOW),
   "GWL_EXSTYLE = %s" % hex(ex))

# ---- ② ITaskbarList 可用（可见态切换靠它即时增删） ----
ok_com = _taskbar_call(4, hwnd)     # AddTab：已在任务栏，返回成功即可
ck("ITaskbarList(COM) 可用（可见态可即时增删任务栏按钮）",
   ok_com, "AddTab HRESULT=0 与否 = %s" % ok_com)
ck("⭐ 显示后已向 shell 发 AddTab —— 确保「有图标」态按钮真的被加上",
   any(i == 4 and ok for i, ok in _CALLS), "_CALLS=%s" % _CALLS)

# ---- ③ 「最小化」：窗口留在桌面不动，只摘任务栏图标 ----
pos0 = (win.x(), win.y())
size0 = (win.width(), win.height())
_CALLS.clear()
win._minimize_to_float()
pump(0.9)
ck("最小化后已向 shell 发 DeleteTab（按钮即时摘除）",
   any(i == 5 and ok for i, ok in _CALLS), "_CALLS=%s" % _CALLS)
ex2 = _get(hwnd, GWL_EXSTYLE)
ck("最小化后：窗口**仍在桌面**（IsWindowVisible=True）",
   bool(user32.IsWindowVisible(hwnd)))
ck("最小化后：**没有**真最小化（IsIconic=False）", not user32.IsIconic(hwnd))
ck("最小化后：位置与尺寸不变（窗口留在原地）",
   (win.x(), win.y()) == pos0 and (win.width(), win.height()) == size0,
   "pos %s → %s" % (pos0, (win.x(), win.y())))
ck("最小化后：exstyle 翻到 WS_EX_TOOLWINDOW（任务栏图标已摘）",
   bool(ex2 & WS_EX_TOOLWINDOW) and not (ex2 & WS_EX_APPWINDOW),
   "GWL_EXSTYLE = %s" % hex(ex2))

# ---- ④ 「关闭」：桌面与任务栏都消失，驻留托盘 ----
win.close()                          # 走 closeEvent → 切无图标态 + hide
pump(0.9)
ck("关闭后：窗口不可见（已收到托盘）", not bool(user32.IsWindowVisible(hwnd)))
ck("关闭后：托盘对象仍在（软件驻留系统托盘）",
   getattr(win, "tray", None) is not None and win.tray.isVisible())

# ---- ⑤ 托盘左键：唤回窗口但不带任务栏图标 ----
_CALLS.clear()
win._on_tray_activated(QSystemTrayIcon.Trigger)
pump(0.9)
ex5 = _get(hwnd, GWL_EXSTYLE)
ck("托盘左键：窗口唤回可见", bool(user32.IsWindowVisible(hwnd)))
ck("托盘左键：**不带**任务栏图标（TOOLWINDOW 态）",
   bool(ex5 & WS_EX_TOOLWINDOW) and not (ex5 & WS_EX_APPWINDOW),
   "GWL_EXSTYLE = %s" % hex(ex5))
ck("托盘左键：显示后发 DeleteTab（确认按钮未被 shell 自动加回）",
   any(i == 5 and ok for i, ok in _CALLS), "_CALLS=%s" % _CALLS)

# ---- ⑥ 托盘右键「显示/隐藏」：唤回窗口并带上任务栏图标（v1.9.15 修复点）----
win.close()
pump(0.6)
_CALLS.clear()
win._toggle_visible()                # 隐藏→显示，且带任务栏图标
pump(0.9)
ex6 = _get(hwnd, GWL_EXSTYLE)
ck("托盘右键「显示/隐藏」：窗口唤回可见", bool(user32.IsWindowVisible(hwnd)))
ck("托盘右键「显示/隐藏」：**带**任务栏图标（APPWINDOW 态）",
   bool(ex6 & WS_EX_APPWINDOW) and not (ex6 & WS_EX_TOOLWINDOW),
   "GWL_EXSTYLE = %s" % hex(ex6))
ck("⭐ 托盘右键唤起时已向 shell 发 AddTab（用户报的「唤回仍无图标」修复点）",
   any(i == 4 and ok for i, ok in _CALLS), "_CALLS=%s" % _CALLS)

# 收尾：摘托盘 + 显式拆窗，避免 Qt DLL 卸载期崩溃（否则退出码会变 0xC0000005）
try:
    if getattr(win, "tray", None) is not None:
        win.tray.hide()
        win.tray.setContextMenu(None)
        win.tray = None
    win.hide()
    win.deleteLater()
except Exception:
    pass
pump(0.3)

print("==== 任务栏两态实测（真机，v1.9.15）====")
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name,
                       ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.stdout.flush()          # ⚠ os._exit 不会 flush 缓冲（管道下会丢输出）
sys.stderr.flush()
os._exit(1 if bad else 0)
