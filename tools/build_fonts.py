# -*- coding: utf-8 -*-
"""构建内置字体：OFL 可变字体 → 静态字重 → 子集化（GB2312 + 源码用字 + 符号）。

输出 fonts/*.ttf 随 exe 打包，运行时由 calendar_app.fonts 注册，
使软件在任何 Windows 设备上的字形完全一致（不再依赖系统字体）。

源字体（SIL Open Font License 1.1，可自由再分发）：
  Noto Serif SC / Noto Sans SC  ← google/fonts 仓库 ofl/ 目录

用法： python tools/build_fonts.py
"""
import glob
import io
import os
import sys

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(_ROOT, "tools", "_font_src")
OUT = os.path.join(_ROOT, "fonts")

# (源文件名, 输出族名, 需要的字重)
PLAN = [
    ("notoserifsc.ttf", "Noto Serif SC", (400, 700, 900)),
    ("notosanssc.ttf", "Noto Sans SC", (400, 700)),
]
WEIGHT_NAME = {400: "Regular", 500: "Medium", 700: "Bold", 900: "Black"}

_EXTRA = ("✎✔✘✕✓✗✚→←↑↓·、。「」『』（）《》〈〉…—–～〇℃"
          "①②③④⑤⑥⑦⑧⑨⑩⑪⑫")


def build_charset():
    """ASCII 全集 + GB2312 全集 + 源码出现过的所有非 ASCII 字 + 常用符号。

    注意：ASCII 必须显式加入 —— 巨大日期数字、英文月份、时间「12:34」、
    分隔线「-」等全部依赖它，只按「非 ASCII」收集会让数字变成缺字方框。
    """
    chars = set(_EXTRA)
    chars.update(chr(c) for c in range(0x20, 0x7F))        # 可打印 ASCII
    chars.update("　")                                       # 全角空格
    # GB2312 全部有效编码
    for hi in range(0xA1, 0xFE + 1):
        for lo in range(0xA1, 0xFE + 1):
            try:
                chars.add(bytes([hi, lo]).decode("gb2312"))
            except (UnicodeDecodeError, ValueError):
                continue
    # 源码 / 数据里的所有非 ASCII 字符
    for path in glob.glob(os.path.join(_ROOT, "*.py")) + \
            glob.glob(os.path.join(_ROOT, "calendar_app", "*.py")) + \
            glob.glob(os.path.join(_ROOT, "tools", "dev_checks", "*.py")):
        try:
            txt = io.open(path, encoding="utf-8").read()
        except OSError:
            continue
        chars.update(c for c in txt if ord(c) > 127)
    return "".join(sorted(chars))


def set_names(font, family, weight):
    """把实例化后的字体命名固定为『族名 + 字重』，保证 Qt 能按字重匹配。

    ⚠ 必须同时改写 **nameID 6（PostScript 名）与 nameID 3（唯一标识）**：
    `instantiateVariableFont(..., updateFontNames=False)` 会把可变字体的原始
    PS 名原样带过来，于是 Regular / Bold / Black 三份的 PS 名**完全相同**
    （实测都是 `NotoSerifSC-ExtraLight`，Sans 三份都是 `NotoSansSC-Thin`）。
    Windows / Qt 以 PS 名作为字体的注册键，重名会让三个字重相互覆盖 ——
    表现为「请求 Bold / Black 全部落到同一个面」，页头英文怎么调都不变粗
    （v1.8.2 真实运行环境的根因，离屏渲染恰好不受影响，所以此前没暴露）。
    """
    style = WEIGHT_NAME.get(weight, "Regular")
    ps_name = "%s-%s" % (family.replace(" ", ""), style)
    for rec in font["name"].names:
        if rec.nameID == 1:
            rec.string = family
        elif rec.nameID == 2:
            rec.string = style
        elif rec.nameID == 3:                      # 唯一标识（必须逐字重不同）
            rec.string = "%s %s;%s" % (family, style, ps_name)
        elif rec.nameID == 4:
            rec.string = "%s %s" % (family, style)
        elif rec.nameID == 6:                      # PostScript 名（重名元凶）
            rec.string = ps_name
        elif rec.nameID == 16:
            rec.string = family
        elif rec.nameID == 17:
            rec.string = style
    if "OS/2" in font:
        font["OS/2"].usWeightClass = weight
    if "head" in font:                             # 微调字体版本，避开系统缓存
        font["head"].fontRevision = 1.0


def build_one(src_name, family, weights, charset):
    path = os.path.join(SRC, src_name)
    if not os.path.exists(path):
        print("  跳过（缺源文件）:", src_name)
        return []
    out_files = []
    for w in weights:
        font = TTFont(path)
        static = instancer.instantiateVariableFont(
            font, {"wght": w}, inplace=False, updateFontNames=False)
        set_names(static, family, w)
        ss = subset.Subsetter(options=subset.Options(
            layout_features=[], notdef_outline=True, recalc_bounds=True,
            drop_tables=["DSIG"], recommended_glyphs=False))
        ss.populate(text=charset)
        ss.subset(static)
        style = WEIGHT_NAME.get(w, "Regular")
        name = "%s-%s.ttf" % (family.replace(" ", ""), style)
        dst = os.path.join(OUT, name)
        static.save(dst)
        out_files.append((dst, family, style))
        print("  %-28s %6.2f MB" % (name, os.path.getsize(dst) / 1048576.0))
        font.close()
        static.close()
    return out_files


def main():
    os.makedirs(OUT, exist_ok=True)
    charset = build_charset()
    print("字符集：%d 个字形（GB2312 全集 + 源码用字 + 符号）" % len(charset))
    total = 0
    for src_name, family, weights in PLAN:
        print("构建 %s ..." % family)
        for dst, _f, _s in build_one(src_name, family, weights, charset):
            total += os.path.getsize(dst)
    print("合计 %.2f MB → %s" % (total / 1048576.0, OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
