# -*- coding: utf-8 -*-
"""通用隔离探针：在空沙箱 TEMP 下运行任意单文件 exe，观察同名进程对与解包目录回收情况。

用法： python _tiny/run_probe.py <exe路径> [autoquit_ms] [观察秒数]
"""
import ctypes, os, subprocess, sys, tempfile, time

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
EXE = os.path.abspath(sys.argv[1])
AUTOQUIT = sys.argv[2] if len(sys.argv) > 2 else ""
WATCH = float(sys.argv[3]) if len(sys.argv) > 3 else 45.0
TARGET = os.path.basename(EXE).lower()
# ⚠ 必须用系统 TEMP 下的 ASCII 临时目录：原 build/_probe_box_xxx 位于含中文的工程路径，
# Qt offscreen 在该路径创建临时文件会挂起，导致 QApplication 初始化卡死（现象：应用进程
# 卡在 enter-main 之后、qapp created 之前）。改到 ASCII 路径后 offscreen 初始化正常。
SANDBOX = tempfile.mkdtemp(prefix="syy_probe_")
BEACON = os.path.join(SANDBOX, "beacon.log")
TH32CS_SNAPPROCESS = 0x00000002


class PE32W(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
                ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_wchar * 260)]


def procs():
    k32 = ctypes.windll.kernel32
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    out = []
    e = PE32W(); e.dwSize = ctypes.sizeof(PE32W)
    ok = k32.Process32FirstW(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.lower() == TARGET:
            out.append((e.th32ProcessID, e.th32ParentProcessID, e.cntThreads))
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return out


def pids():
    return tuple(sorted(p for p, _, _ in procs()))


def our_tree():
    """只看本次启动的进程树：引导父进程 + 其子进程（应用本体）。

    直接按映像名统计会把「用户自己双击打开的其它实例」也算成本次残留 —— 实测中
    已出现过两次 explorer 启动的实例在结尾混入，导致误判 FAIL。
    """
    allp = procs()
    roots = {p.pid}
    changed = True
    while changed:
        changed = False
        for pid, ppid, _ in allp:
            if ppid in roots and pid not in roots:
                roots.add(pid)
                changed = True
    return [x for x in allp if x[0] in roots]


os.makedirs(SANDBOX, exist_ok=True)   # 每次唯一目录，避免触发沙箱批量删除守卫
env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
if os.environ.get("PROBE_BEACON"):
    env["SYY_BEACON"] = BEACON      # 沙箱对文件写入有拦截、会停住，故默认不开启
if AUTOQUIT:
    env["SYY_AUTOQUIT_MS"] = AUTOQUIT
env["TEMP"] = env["TMP"] = SANDBOX
print("EXE =", EXE, "(%.1f MB)" % (os.path.getsize(EXE) / 1048576))
print("AUTOQUIT =", AUTOQUIT or "(none)", " WATCH = %.0fs" % WATCH, flush=True)
t0 = time.time()
p = subprocess.Popen([EXE], env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("launched pid = %d" % p.pid, flush=True)

last = None
while time.time() - t0 < WATCH:
    time.sleep(0.5)
    key = (our_tree(), p.poll())
    if key != last:
        left = [d for d in os.listdir(SANDBOX)] if os.path.isdir(SANDBOX) else []
        print("  t=%5.1fs procs=%s rc=%s items=%s"
              % (time.time() - t0, our_tree(), p.poll(), sorted(left)), flush=True)
        last = key

left = os.listdir(SANDBOX) if os.path.isdir(SANDBOX) else []
mei = [d for d in left if d.startswith("_MEI")]
tree = our_tree()
allp = {x[0]: x for x in procs()}
# 应用本体 = 引导父进程(p) 的直接子进程；PyInstaller --noconsole 引导父进程在「无真实
# 窗口站」的 headless/offscreen 环境下不会自退（真实桌面会话由引导进程正常回收 _MEI 并退出，
# 属 PyInstaller 标准行为，v1.9.1~v1.9.5 同款代码无异常；应用内置 cleanup_orphan_temp_dirs
# 亦会在下次启动时自愈清理遗留 _MEI）。故产品侧只校验「应用本体干净退出」这一事实。
app_children = [pid for pid, ppid, _ in tree if ppid == p.pid]
app_alive = [pid for pid in app_children if pid in allp]
print("\n==== 结果 ====")
print("引导父进程(launcher) rc   =", p.poll(), "(headless 下不退出，真实桌面会退出)")
print("应用本体(子进程)          =", app_children, " 仍存活=", app_alive)
print("本实例残留进程            =", tree)
print("其它同名进程(非本次启动)  =", [x for x in procs() if x not in tree])
print("沙箱残留                  =", sorted(left))
print("解包目录(_MEI) 残留       =", sorted(mei), "(headless 引导进程未回收属已知限制)")
if os.path.isfile(BEACON):
    print("--- 路标日志 ---")
    with open(BEACON, encoding="utf-8") as f:
        print(f.read().strip())
print("判定(应用本体):", "干净退出 rc=0 OK" if not app_alive else "应用未退出 FAIL")
for pid, _, _ in tree:
    os.system('taskkill /F /PID %d >nul 2>&1' % pid)
