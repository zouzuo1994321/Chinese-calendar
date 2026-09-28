# -*- coding: utf-8 -*-
"""双实例端到端：验证「新实例只清理旧实例的应用本体，不碰其引导父进程」。

泄漏机理：onefile 的引导父进程与应用本体**映像名相同**。旧版清理逻辑会把旧实例的
引导父进程一起杀掉，而删除 %TEMP%\\_MEIxxxxxx 正是引导父进程的职责 → 每次开第二个
实例就永久残留一份完整解包（实测累积 52 GB）。本测试即为该修复的端到端证据。
"""
import ctypes, os, subprocess, sys, time

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
EXE = os.path.abspath(os.path.join("dist", "农历日历.exe"))
TARGET = os.path.basename(EXE).lower()
ROOT = os.getcwd()
BOX_A = os.path.join(ROOT, "build", "_dual_A_%d" % time.time())
BOX_B = os.path.join(ROOT, "build", "_dual_B_%d" % time.time())
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
            out.append((e.th32ProcessID, e.th32ParentProcessID))
        ok = k32.Process32NextW(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return out


def pids():
    return {p for p, _ in procs()}


def mei_in(box):
    try:
        return [d for d in os.listdir(box) if d.startswith("_MEI")]
    except OSError:
        return []


def launch(box, autoquit=None):
    os.makedirs(box, exist_ok=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    if autoquit:
        env["SYY_AUTOQUIT_MS"] = str(autoquit)
    env["TEMP"] = env["TMP"] = box
    return subprocess.Popen([EXE], env=env, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for(cond, timeout, step=0.5):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return time.time() - t0
        time.sleep(step)
    return None


R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""), flush=True)


print("EXE =", EXE, flush=True)

# ---------- 实例 A ----------
pa = launch(BOX_A)
t = wait_for(lambda: len(procs()) >= 2, 60)
ck("A：引导父进程 + 应用本体 均出现（onefile 双进程）", t is not None,
   "procs=%s" % procs())
a_all = procs()
a_parent = pa.pid
a_body = [p for p, pp in a_all if pp == a_parent]
ck("A：应用本体为引导父进程的子进程", len(a_body) == 1, "parent=%s body=%s" % (a_parent, a_body))
a_body = a_body[0] if a_body else None
print("A: parent_pid=%s body_pid=%s  _MEI=%s" % (a_parent, a_body, mei_in(BOX_A)), flush=True)

# ---------- 实例 B：启动时应清理 A 的应用本体 ----------
pb = launch(BOX_B, autoquit=8000)
ck("B：进程启动", pb.poll() is None)
t = wait_for(lambda: len(procs()) >= 4, 60)
print("A+B 并处 procs =", procs(), flush=True)
ck("B：与 A 并存（共 4 个同名进程）", t is not None, "procs=%s" % procs())

b_all = procs()
b_parent = pb.pid
b_body = [p for p, pp in b_all if pp == b_parent]
ck("B：自身双进程结构完整", len(b_body) == 1, "parent=%s body=%s" % (b_parent, b_body))

# 等 A 的应用本体被杀
t = wait_for(lambda: a_body is not None and a_body not in pids(), 60)
ck("B 启动后：A 的应用本体已被清理", t is not None, "t=%s a_body=%s" % (t, a_body))

# 关键断言：此刻 A 的引导父进程必须仍然存活（它要负责删除 A 的解包目录）
left = pids()
ck("**A 的引导父进程未被误杀**", a_parent in left,
   "a_parent=%s 存活=%s" % (a_parent, a_parent in left))

# A 的解包目录应在其引导父进程收尾后消失（本沙箱删除异步，给足时间）
t = wait_for(lambda: not mei_in(BOX_A), 300, 1.0)
ck("A 的解包目录最终被回收（无泄漏）", t is not None,
   "耗时=%s 剩余=%s" % (None if t is None else "%.0fs" % t, mei_in(BOX_A)))

# B 自行干净退出
t = wait_for(lambda: pb.poll() is not None, 90, 0.5)
ck("B 正常退出 rc=0", pb.poll() == 0, "rc=%s" % pb.poll())
t2 = wait_for(lambda: not mei_in(BOX_B), 300, 1.0)
ck("B 的解包目录最终被回收", t2 is not None,
   "耗时=%s 剩余=%s" % (None if t2 is None else "%.0fs" % t2, mei_in(BOX_B)))

for p in pids():
    os.system('taskkill /F /PID %d >nul 2>&1' % p)
failed = [n for n, c, _ in R if not c]
print("\n==== 双实例端到端 ==== total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, c, _ in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
