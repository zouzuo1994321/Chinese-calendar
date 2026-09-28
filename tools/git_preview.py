# -*- coding: utf-8 -*-
"""模拟 .gitignore 过滤，预览 `git add .` 会提交哪些文件（发布前自检用）。"""
import fnmatch
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_ignore():
    pats = []
    with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append(line.rstrip("/"))
    return pats


def ignored(rel, pats):
    base = os.path.basename(rel)
    for p in pats:
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(base, p):
            return True
        if rel.startswith(p + "/") or rel == p:
            return True
        # 目录前缀通配（如 __pycache__/）
        if fnmatch.fnmatch(rel.split("/")[0], p):
            return True
    return False


def main():
    pats = load_ignore()
    keep, size = [], 0
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d != ".git"]
        for f in files:
            full = os.path.join(root, f)
            rel = ""
            try:
                rel = os.path.relpath(full, ROOT).replace(os.sep, "/")
            except ValueError:
                # Windows 保留设备名（如 nul）无法做 relpath，按跳过处理
                continue
            if not ignored(rel, pats):
                keep.append(rel)
                try:
                    size += os.path.getsize(full)
                except OSError:
                    pass
    keep.sort()
    print("将被提交文件数: %d，总大小 %.1f MB" % (len(keep), size / 1048576.0))
    for r in keep:
        print("  " + r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
