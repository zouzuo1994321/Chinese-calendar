# -*- coding: utf-8 -*-
"""进程清理判定的注入式单测 + 孤儿解包目录自愈清理的行为验证。"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from calendar_app import process as P

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _box import make_box                                   # noqa: E402

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""))


EXE = "农历日历.exe"
SH = "bash.exe"


def table(*rows):
    """rows: (pid, ppid, name)"""
    return [(p, pp, n.lower()) for p, pp, n in rows]


# 让 _exe_name() 固定返回 农历日历.exe
P._exe_name = lambda: EXE

# --- 场景 1：单实例（自己 + 自己的引导父进程）不应清理任何东西 ---
t1 = table((5, 0, SH), (100, 5, SH), (200, 100, EXE), (201, 200, EXE))
skip1 = {201} | P._ancestor_pids_from(t1, start=201)
ck("单实例：无残留可杀", P.find_sibling_pids(skip=skip1, procs=t1) == [],
   "skip=%s" % sorted(skip1))

# --- 场景 2：双实例 —— 只杀旧实例的应用本体，保留旧实例的引导父进程 ---
t2 = table((5, 0, SH), (100, 5, SH),
           (200, 100, EXE), (201, 200, EXE),      # 旧实例：引导父 200 / 本体 201
           (300, 5, SH), (400, 300, EXE), (401, 400, EXE))   # 新实例（自己）
skip2 = {401} | P._ancestor_pids_from(t2, start=401)
got2 = P.find_sibling_pids(skip=skip2, procs=t2)
ck("双实例：杀掉旧实例应用本体", got2 == [201], "得到=%s 期望=[201]" % got2)
ck("双实例：**不杀**旧实例引导父进程（否则必泄漏解包）", 200 not in got2, "得到=%s" % got2)
ck("双实例：不误杀无关进程", all(p in (201,) for p in got2))

# --- 场景 3：旧实例本体已退出、仅剩引导父进程在收尾 ---
t3 = table((5, 0, SH), (100, 5, SH),
           (200, 100, EXE),                        # 旧引导父进程收尾中
           (300, 5, SH), (400, 300, EXE), (401, 400, EXE))
skip3 = {401} | P._ancestor_pids_from(t3, start=401)
ck("收尾中的引导父进程不被杀掉（保住解包回收）",
   P.find_sibling_pids(skip=skip3, procs=t3) == [],
   "得到=%s" % P.find_sibling_pids(skip=skip3, procs=t3))

# --- 场景 4：孤儿应用本体（引导父已消失）仍应被清理 ---
t4 = table((5, 0, SH), (100, 5, SH),
           (301, 999, EXE),                        # 999 已不存在
           (300, 5, SH), (400, 300, EXE), (401, 400, EXE))
skip4 = {401} | P._ancestor_pids_from(t4, start=401)
ck("孤儿应用本体可被清理", 301 in P.find_sibling_pids(skip=skip4, procs=t4),
   "得到=%s" % P.find_sibling_pids(skip=skip4, procs=t4))

# --- 场景 5：三实例级联 ---
t5 = table((5, 0, SH),
           (110, 5, SH), (210, 110, EXE), (211, 210, EXE),
           (120, 5, SH), (220, 120, EXE), (221, 220, EXE),
           (130, 5, SH), (230, 130, EXE), (231, 230, EXE))
skip5 = {231} | P._ancestor_pids_from(t5, start=231)
got5 = sorted(P.find_sibling_pids(skip=skip5, procs=t5))
ck("三实例：只清两个旧本体，三个引导父进程全部保留", got5 == [211, 221],
   "得到=%s 期望=[211, 221]" % got5)
ck("三实例：引导父 210/220 未被杀", 210 not in got5 and 220 not in got5)

# --- 场景 6：祖先链上溯正确性 ---
t6 = table((1, 0, SH), (2, 1, "python.exe"), (3, 2, EXE), (4, 3, EXE))
ck("祖先链上溯 {3,2,1}", P._ancestor_pids_from(t6, start=4) == {3, 2, 1},
   "得到=%s" % sorted(P._ancestor_pids_from(t6, start=4)))

# --- 场景 7：孤儿解包目录自愈清理 ---
BOX = make_box("_cleanup_case")     # 退出时自动回收，不再累积在 build/
old_mei = os.path.join(BOX, "_MEIabc111")
new_mei = os.path.join(BOX, "_MEIabc222")
other = os.path.join(BOX, "not_mei")
for d in (old_mei, new_mei, other):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "f.txt"), "w") as f:
        f.write("x")
past = time.time() - 3600
for d in (old_mei, new_mei):
    os.utime(os.path.join(d, "f.txt"), (past, past))
    os.utime(d, (past, past))
os.environ["TEMP"] = os.environ["TMP"] = BOX
sys._MEIPASS = os.path.join(new_mei, "inner")     # 假装新目录是自己正在用的
n = P.cleanup_orphan_temp_dirs(min_age_s=600, max_seconds=5.0, max_dirs=10)
# 注：本沙箱的删除是异步落地的，故轮询等待（真实机器上毫秒级）
_gone = False
for _ in range(30):
    if not os.path.isdir(old_mei):
        _gone = True
        break
    time.sleep(0.2)
ck("自愈清理：删除过期 _MEI 目录", _gone, "cleaned=%d isdir=%s" % (n, os.path.isdir(old_mei)))
ck("自愈清理：跳过本进程自身的解包目录", os.path.isdir(new_mei))
ck("自愈清理：不动非 _MEI 目录", os.path.isdir(other))
ck("自愈清理：返回计数正确", n == 1, "cleaned=%d" % n)

# 新鲜目录（未过期）不清理
fresh = os.path.join(BOX, "_MEIabc333")
os.makedirs(fresh, exist_ok=True)
del sys._MEIPASS
n2 = P.cleanup_orphan_temp_dirs(min_age_s=600, max_seconds=5.0, max_dirs=10)
ck("自愈清理：新解包目录（10 分钟内）不误删", os.path.isdir(fresh), "cleaned=%d" % n2)

failed = [n_ for n_, c, _ in R if not c]
print("\n==== 进程判定单测 ==== total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, c, _ in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
