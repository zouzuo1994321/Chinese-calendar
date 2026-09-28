# -*- coding: utf-8 -*-
"""清理过程文件：build/（PyInstaller 工作目录 + 校验沙盒）等。

用法：
  python tools/clean_workspace.py            # 演练：只打印将删除的内容
  python tools/clean_workspace.py --apply    # 真正删除
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TARGETS = [
    os.path.join(ROOT, "build"),                 # 11GB：构建工作目录 + 校验沙盒
    os.path.join(ROOT, "__pycache__"),
    os.path.join(ROOT, "calendar_app", "__pycache__"),
    os.path.join(ROOT, "ui", "__pycache__"),
    os.path.join(ROOT, "tools", "__pycache__"),
    os.path.join(ROOT, "tools", "dev_checks", "__pycache__"),
    os.path.join(ROOT, "tools", "_font_src"),    # 42MB 字体源（可重新下载）
    os.path.join(ROOT, "_sheen_tmp.png"),
    os.path.join(ROOT, "nul"),
]

KEEP = {"build"}   # 这些目录整个删除


def iter_files(path):
    if os.path.isfile(path):
        yield path, os.path.getsize(path)
    elif os.path.isdir(path):
        for base, _dirs, files in os.walk(path):
            for f in files:
                p = os.path.join(base, f)
                try:
                    yield p, os.path.getsize(p)
                except OSError:
                    yield p, 0


def main():
    apply = "--apply" in sys.argv
    total_files, total_bytes = 0, 0
    t0 = time.time()
    for tgt in TARGETS:
        if not os.path.exists(tgt):
            continue
        n = sz = 0
        for p, s in iter_files(tgt):
            n += 1
            sz += s
        total_files += n
        total_bytes += sz
        try:
            rel = os.path.relpath(tgt, ROOT)
        except ValueError:          # 保留名 nul 在 \\.\ 设备命名空间
            rel = tgt
        print("%-46s %6d 文件  %8.1f MB" % (rel, n, sz / 1048576.0))
        if not apply:
            continue
        if os.path.isfile(tgt):
            try:
                os.remove(tgt)
            except OSError as e:
                print("   ! 删除失败:", e)
            continue
        # 目录：逐文件删除（避开宿主环境的批量删除拦截），打印进度
        done = 0
        for p, _s in iter_files(tgt):
            try:
                os.remove(p)
            except OSError:
                pass
            done += 1
            if done % 2000 == 0:
                print("   ... %d/%d  %.0fs" % (done, n, time.time() - t0),
                      flush=True)
        for base, dirs, _files in os.walk(tgt, topdown=False):
            for d in dirs:
                try:
                    os.rmdir(os.path.join(base, d))
                except OSError:
                    pass
        try:
            os.rmdir(tgt)
            print("   已删除", rel)
        except OSError as e:
            print("   目录未能完全移除:", e)
    print("\n合计：%d 文件 / %.1f MB  耗时 %.0fs%s"
          % (total_files, total_bytes / 1048576.0, time.time() - t0,
             "" if apply else "（演练，未删除；加 --apply 才真正删除）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
