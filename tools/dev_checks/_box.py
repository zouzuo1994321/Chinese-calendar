# -*- coding: utf-8 -*-
"""校验脚本的临时沙盒：统一在 build/ 下创建，进程退出时自动回收。

历史问题：`agenda_checks.py` / `ui_agenda_probe.py` / `test_process.py`
各自 `os.makedirs(BOX)` 却从不删除，**每跑一次就在 build/ 里留下一个目录**，
数月累积把 `build/` 撑到 ~11 GB（2026-09-28 清理时发现并修）。

此处用 `atexit` 兜底：即使断言失败、抛异常或 `sys.exit()`，退出时都会清掉；
删除失败（沙盒被占用等）静默忽略——`build/` 已在 .gitignore 中，不影响发布。
"""
import atexit
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def make_box(tag):
    """在 build/ 下建一个 `<tag>_<pid>` 沙盒并返回其绝对路径；退出时自动删除。"""
    box = os.path.join(ROOT, "build", "%s_%d" % (tag, os.getpid()))
    shutil.rmtree(box, ignore_errors=True)      # 清掉同 pid 的历史残留
    os.makedirs(box, exist_ok=True)
    atexit.register(shutil.rmtree, box, ignore_errors=True)
    return box
