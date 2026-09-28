# -*- coding: utf-8 -*-
"""肆月日历 - 程序入口。

启动时先清理之前未关闭的本软件残留进程，再显示主窗口；
窗口关闭后进程自行退出。
"""

import os
import sys
import threading
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from calendar_app.process import cleanup_orphan_temp_dirs, kill_stale_instances
from calendar_app.version import APP_NAME

# ---- 自动化诊断路标：仅当设置 SYY_BEACON=<文件路径> 时记录启动/退出阶段 ----
# 用于定位「单文件 exe 版应用未能正常退出、导致引导父进程长期等待并泄漏解包目录」。
_BEACON_PATH = os.environ.get("SYY_BEACON", "")


def _beacon(tag: str) -> None:
    if not _BEACON_PATH:
        return
    try:
        with open(_BEACON_PATH, "a", encoding="utf-8") as f:
            f.write("%.3f pid=%d %s\n" % (time.time(), os.getpid(), tag))
    except OSError:
        pass


def _logo_path():
    """解析打包/源码两种运行方式下的 logo.png 绝对路径。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "logo.png")


def main():
    _beacon("enter-main frozen=%s" % getattr(sys, "frozen", False))
    # 残留进程清理放到窗口显示之后再跑：它的唯一作用是「让旧实例腾开文件句柄」，
    # 对本次启动的界面没有任何依赖。放在最前面会让冷启动被最坏情况下的进程轮询
    # 拖住（v1.8.3 实测曾吃掉 17s+，用户观感就是「双击没反应」）。
    _stale = {"killed": 0}

    def _background_kill():
        try:
            _stale["killed"] = kill_stale_instances()
        except Exception as ex:          # noqa: BLE001 —— 清理失败绝不能影响主流程
            _beacon("kill-stale EXC %r" % (ex,))
        _beacon("kill-stale done killed=%d" % _stale["killed"])

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    _beacon("qapp created")
    # 后台自愈：清理历史遗留的 %TEMP%\_MEIxxxxxx 解包目录（不阻塞启动）
    threading.Thread(target=cleanup_orphan_temp_dirs, daemon=True).start()
    # 全局图标统一为 logo.png（主窗口 / 各对话框 / 任务栏均继承）
    logo = _logo_path()
    if os.path.exists(logo):
        app.setWindowIcon(QIcon(logo))
    _beacon("icon set exists=%s" % os.path.exists(logo))
    # 注册内置字体（必须在 QApplication 之后、任何控件创建之前）：
    # 无 QGuiApplication 实例时 addApplicationFont 会段错误，故放在这里
    try:
        from calendar_app.fonts import install_fonts
        _loaded = install_fonts()
        _beacon("fonts installed %d" % len(_loaded))
    except Exception as ex:
        _loaded = []
        _beacon("fonts EXC %r" % (ex,))
    # 默认以托盘图标形式运行：关闭窗口仅隐藏到托盘，故不因最后一个窗口关闭而退出
    app.setQuitOnLastWindowClosed(False)

    from ui_main import MainWindow
    _beacon("ui_main imported")
    win = MainWindow()
    _beacon("MainWindow built")
    win.show()
    _beacon("window shown")
    # 界面已经可见，此时再去清残留进程，用户感知不到任何延迟
    threading.Thread(target=_background_kill, daemon=True).start()

    # 自动化验证用：SYY_AUTOQUIT_MS=毫秒 时到点自动正常退出（用于校验单文件 exe 的
    # 干净退出与 %TEMP%\\_MEIxxxxxx 回收；不设该变量时对正常使用无任何影响）。
    _ms = os.environ.get("SYY_AUTOQUIT_MS", "")
    if _ms.isdigit():
        def _autoquit():
            _beacon("autoquit timer fired -> app.quit()")
            app.quit()
        QTimer.singleShot(int(_ms), _autoquit)
        _beacon("autoquit armed %sms" % _ms)

    _rc = app.exec()
    _beacon("exec returned rc=%s" % _rc)
    # 用 os._exit 直接结束进程：后台自愈清理线程可能仍阻塞在长 I/O 上，走常规
    # 解释器 finalize 会一直等它，导致引导父进程迟迟收不到子进程退出信号、
    # 迟迟不回收 %TEMP%\_MEIxxxxxx（表现为残留僵尸引导进程 + 每次启动泄漏一份解包）。
    # 此处所有需要落盘的数据（settings.json 等）都已在各自 with 块内 flush，安全。
    _beacon("about to os._exit")
    os._exit(_rc)


if __name__ == "__main__":
    main()
