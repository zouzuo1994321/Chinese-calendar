# -*- coding: utf-8 -*-
"""肆月日历 - 进程管理。

要求：
  · exe 打开时，清理之前未关闭的本软件残留进程；
  · 关闭窗口后，自身进程正常退出。
"""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import time

TH32CS_SNAPPROCESS = 0x00000002


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong),
                ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", ctypes.c_ulong),
                ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_wchar * 260)]


def _exe_name() -> str:
    return os.path.basename(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])


def _snapshot_ppid_map() -> dict:
    """快照「PID -> 父 PID」映射。"""
    return {pid: ppid for pid, ppid, _ in iter_processes()}


def iter_processes() -> list:
    """枚举当前全部进程，返回 ``[(pid, ppid, 映像名小写), ...]``。

    单独抽出，便于单测注入假进程表（本机进程表无法构造场景）。
    """
    k32 = ctypes.windll.kernel32
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = []
    if snap == -1 or snap == 0:
        return out
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            out.append((entry.th32ProcessID, entry.th32ParentProcessID,
                        entry.szExeFile.lower()))
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        k32.CloseHandle(snap)
    return out


def _ancestor_pids_from(procs, start=None) -> set:
    """沿父链上溯的全部祖先 PID（基于已取好的进程表快照）。"""
    ppid = {pid: pp for pid, pp, _ in procs}
    ancestors, cur, guard = set(), os.getpid() if start is None else start, 0
    while guard < 32:
        cur = ppid.get(cur, 0)
        if not cur or cur in ancestors:
            break
        ancestors.add(cur)
        guard += 1
    return ancestors


def _ancestor_pids() -> set:
    """当前进程的全部祖先 PID（沿父链上溯）。

    ⚠ 关键：PyInstaller 单文件（onefile）打包后，引导进程会**以同名 exe** 再启动一个
    子进程来承载真正的 Python 代码 —— 二者的映像名完全相同。若把祖先也当成「残留
    进程」杀掉，引导进程会被自己的子进程终止，而**删除 %TEMP%\\_MEIxxxxxx 解包目录
    正是引导进程的职责**，于是每次启动都会永久残留一份完整解包（实测曾累积 52 GB）。
    因此必须把祖先 PID 排除在清理范围之外。
    """
    return _ancestor_pids_from(iter_processes())


def find_sibling_pids(skip=None, procs=None) -> list:
    """找到需要清理的「旧实例应用本体」PID。

    难点：onefile 的**引导父进程**与**应用本体（子进程）**映像名相同，肉眼不可区分。
    但二者的父子关系不同，据此可安全判别：

      · 应用本体：其父进程**同名**（父 = 引导进程）；若父进程已消失（孤儿）也算。
      · 引导父进程：其父进程是 explorer / cmd / 启动器等**不同名**的存活进程。

    引导父进程负责删除 %TEMP%\\_MEIxxxxxx，**杀掉它 = 永久残留一份完整解包**；
    而杀掉应用本体后，引导父进程会自行完成收尾并退出。故这里只返回应用本体。
    """
    name = _exe_name().lower()
    table = iter_processes() if procs is None else procs
    if skip is None:
        skip = {os.getpid()} | _ancestor_pids_from(table)
    live = {pid for pid, _, _ in table}
    same = {pid for pid, _, n in table if n == name}
    pids = []
    for pid, ppid, n in table:
        if n != name or pid in skip:
            continue
        if ppid in same or ppid not in live:     # 应用本体（含孤儿），非引导父进程
            pids.append(pid)
    return pids


def kill_stale_instances(timeout_ms: int = 3000) -> int:
    """启动时清理旧实例的**应用本体**，返回终止数量。

    不含本进程及其引导父进程，也**不包含其它实例的引导父进程**（见
    :func:`find_sibling_pids`）——那是删除解包目录的唯一责任人。
    """
    k32 = ctypes.windll.kernel32
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED = 0x1000
    killed = 0
    skip = {os.getpid()} | _ancestor_pids()
    targets = find_sibling_pids(skip=skip)
    # ⚠ 冻结 exe 冷启动陷阱（v1.8.3 实测）：本软件本体与**其它 PyInstaller 单文件
    # 应用**共用映像名以外的判定逻辑没问题，但旧实例若正处于解包自举阶段，其引导
    # 父进程会持有主 exe 的文件句柄 —— 此时 TerminateProcess 后句柄不会立刻释放，
    # 下面的「等它退干净」轮询会被拖满整个 timeout_ms。旧实现无论有没有真的杀掉，
    # 只要 killed>0 就轮询，实测在 tmp 目录被大量扫描的系统上稳定吃掉 17s+，
    # 表现为「双击 exe 半天没反应」。改为**只等真正终止过的进程**，并在轮询里
    # 用 OpenProcess 句柄确认，避免反复全表枚举。
    if not targets:
        return 0
    for pid in targets:
        h = k32.OpenProcess(PROCESS_TERMINATE, False, pid)
        if h:
            if k32.TerminateProcess(h, 1):
                killed += 1
            k32.CloseHandle(h)
    if killed:
        deadline = time.time() + timeout_ms / 1000.0
        pending = set(targets)
        while pending and time.time() < deadline:
            gone = set()
            for pid in pending:
                h = k32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
                if not h:                       # 句柄取不到 = 进程已消失
                    gone.add(pid)
                else:
                    # 句柄能取到也可能是僵尸，再看退出码是否已就绪
                    code = ctypes.c_ulong(259)  # STILL_ACTIVE
                    if k32.GetExitCodeProcess(h, ctypes.byref(code)) and code.value != 259:
                        gone.add(pid)
                    k32.CloseHandle(h)
            pending -= gone
            if pending:
                time.sleep(0.05)
    return killed


def cleanup_orphan_temp_dirs(min_age_s: int = 600, max_seconds: float = 20.0,
                             max_dirs: int = 120) -> int:
    """自愈清理历史遗留的 %TEMP%\\_MEIxxxxxx 解包目录，返回清理数量。

    单文件 exe 的解包目录由**引导父进程**负责删除。只要引导父进程没能正常收尾
    （被新实例的残留清理杀掉、被运行器强制结束、掉电……），该目录就会永久残留，
    且体积等于整包解压后的全部内容（本例约 640MB/次）。实测本机累积 332 个目录、
    约 **53GB**。为此在启动后（后台线程）做一次自愈清理，安全边界如下：

      · 只处理 %TEMP% 下**直接子项**且名字以 ``_MEI`` 开头的**目录**；
      · 跳过本进程自身正在使用的解包目录（``sys._MEIPASS`` 的父目录）；
      · 只处理 mtime 早于 ``min_age_s`` 的目录，避免误删刚刚解包的活跃目录；
      · 先 ``os.replace`` 做占用探测——目录内有打开的文件句柄或已加载的 DLL 时
        改名会失败，据此跳过所有仍被其它进程使用的解包目录（含其它 PyInstaller 应用）；
      · ``max_seconds`` / ``max_dirs`` 限定单次工作量，避免拖住解释器退出；
      · 全程吞掉异常，绝不影响主流程。
    """
    tmp = os.environ.get("TEMP") or os.environ.get("TMP")
    if not tmp or not os.path.isdir(tmp):
        return 0
    meipass = getattr(sys, "_MEIPASS", None)
    own = os.path.normcase(os.path.dirname(meipass)) if meipass else None
    now = time.time()
    deadline = now + max_seconds
    cleaned = 0
    try:
        names = os.listdir(tmp)
    except OSError:
        return 0
    for name in names:
        if cleaned >= max_dirs or time.time() > deadline:
            break
        if not name.startswith("_MEI"):
            continue
        path = os.path.join(tmp, name)
        if own and os.path.normcase(path) == own:
            continue
        try:
            if not os.path.isdir(path):
                continue
            if now - os.path.getmtime(path) < min_age_s:
                continue
        except OSError:
            continue
        probe = path + ".__orphan__"
        try:
            os.replace(path, probe)      # 占用探测：失败即说明仍在使用
        except OSError:
            continue
        try:
            shutil.rmtree(probe)
            cleaned += 1
        except OSError:
            try:                          # 删不掉就还原，别留垃圾
                os.replace(probe, path)
            except OSError:
                pass
    return cleaned
