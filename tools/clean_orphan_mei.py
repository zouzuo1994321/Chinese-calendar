# -*- coding: utf-8 -*-
"""一次性清理 PyInstaller 单文件运行遗留的 %TEMP%\\_MEIxxxxxx 解包目录。

背景
----
单文件（onefile）exe 每次运行都会把整包解压到 %TEMP%\\_MEIxxxxxx，退出时由
**引导父进程**负责删除。若引导父进程没能正常收尾（被新实例的残留清理杀掉、
被运行器强制结束、掉电……），该目录就会永久残留，体积约等于解压后的全部内容
（本软件约 640MB/次）。

v1.6.0 起程序已内置自愈清理（启动后后台线程，安全边界见
calendar_app/process.py 的 cleanup_orphan_temp_dirs）。本脚本用于**一次性**回收
历史上已经积压的残留目录。

用法
----
    python tools/clean_orphan_mei.py            # 预演：只统计，不删除
    python tools/clean_orphan_mei.py --apply    # 实际删除

安全边界
--------
· 只处理 %TEMP% 下**直接子项**且名字以 _MEI 开头的**目录**；
· 只处理 mtime 早于 10 分钟的目录（避免误删正在运行的实例的解包目录）；
· 先改名做占用探测，仍被进程占用的目录自动跳过；
· 非 _MEI 前缀的目录/文件一律不动。
"""
import os
import shutil
import sys
import time

MIN_AGE_S = 600
APPLY = "--apply" in sys.argv


def dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def main():
    tmp = os.environ.get("TEMP") or os.environ.get("TMP")
    if not tmp or not os.path.isdir(tmp):
        print("找不到有效的 %TEMP% 目录")
        return 1
    now = time.time()
    cands, skipped_age, skipped_busy = [], 0, 0
    for name in sorted(os.listdir(tmp)):
        if not name.startswith("_MEI"):
            continue
        path = os.path.join(tmp, name)
        if not os.path.isdir(path):
            continue
        try:
            if now - os.path.getmtime(path) < MIN_AGE_S:
                skipped_age += 1
                continue
        except OSError:
            continue
        cands.append(path)

    total = sum(dir_size(p) for p in cands)
    print("临时目录: %s" % tmp)
    print("候选目录: %d 个，合计 %.1f MB (%.2f GB)"
          % (len(cands), total / 1048576, total / 1073741824))
    print("跳过（太新）: %d 个" % skipped_age)

    if not APPLY:
        print("\n[预演模式] 未删除任何文件。确认无误后加 --apply 执行。")
        for p in cands[:5]:
            print("  样本:", os.path.basename(p))
        return 0

    freed = cleaned = 0
    for path in cands:
        sz = dir_size(path)
        probe = path + ".__reclaim__"
        try:
            os.replace(path, probe)
        except OSError:
            skipped_busy += 1
            continue
        try:
            shutil.rmtree(probe)
            cleaned += 1
            freed += sz
        except OSError as e:
            print("  删除失败 %s :: %s" % (os.path.basename(path), repr(e)[:90]))
            try:
                os.replace(probe, path)
            except OSError:
                pass
    print("\n已清理 %d 个目录，释放 %.2f GB；占用中跳过 %d 个。"
          % (cleaned, freed / 1073741824, skipped_busy))
    return 0


if __name__ == "__main__":
    sys.exit(main())
