# -*- coding: utf-8 -*-
"""就地修复已构建内置字体的 name 表：补齐唯一 PostScript 名 / 唯一标识。

背景（v1.8.2 真实运行环境暴露）：
`tools/build_fonts.py` 原 `set_names()` 只改写 nameID 1/2/4/16/17，**漏了 6**。
而 `instantiateVariableFont(..., updateFontNames=False)` 会把可变字体的原始
PostScript 名原样保留，于是：

    NotoSerifSC-Regular.ttf / -Bold.ttf / -Black.ttf  →  6 = NotoSerifSC-ExtraLight（全同）
    NotoSansSC-Regular.ttf  / -Bold.ttf               →  6 = NotoSansSC-Thin      （全同）
    nameID 3（唯一标识）同样完全相同

Windows / Qt 以 PostScript 名作字体注册键，重名导致三个字重相互覆盖：
**请求 Bold / Black 全部落到同一个面**，页头英文因而「只是变大、不会加粗」。
离屏（offscreen）渲染恰好不读这条路径，所以此前 61/61 全绿却没发现。

本脚本不需要源可变字体，直接对 fonts/*.ttf 原地补 name 表即可。
`build_fonts.py::set_names()` 已同步修好，重跑构建也会得到正确结果。

用法： python tools/fix_font_names.py [--check]
"""
import os
import sys

from fontTools.ttLib import TTFont

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_ROOT, "fonts")


def _style_of(fname):
    """从文件名取字重名（NotoSerifSC-Bold.ttf → Bold）。"""
    return os.path.splitext(fname)[0].rsplit("-", 1)[-1]


def _family_of(font):
    return font["name"].getDebugName(1)


def patch(path, check_only=False):
    """补齐 nameID 3 / 6；返回 (文件名, 旧PS名, 新PS名, 是否有改动)。"""
    fname = os.path.basename(path)
    font = TTFont(path)
    family = _family_of(font)
    style = _style_of(fname)
    ps_name = "%s-%s" % (family.replace(" ", ""), style)
    old_ps = font["name"].getDebugName(6)
    old_uid = font["name"].getDebugName(3)
    new_uid = "%s %s;%s" % (family, style, ps_name)
    changed = (old_ps != ps_name) or (old_uid != new_uid)
    if changed and not check_only:
        # 覆盖所有平台/编码记录（fontTools 的 setName 会按需新增）
        font["name"].setName(ps_name, 6, 3, 1, 0x409)
        font["name"].setName(ps_name, 6, 1, 0, 0)
        font["name"].setName(new_uid, 3, 3, 1, 0x409)
        font["name"].setName(new_uid, 3, 1, 0, 0)
        font.save(path)
    font.close()
    return fname, old_ps, ps_name, changed


def main():
    check_only = "--check" in sys.argv
    files = sorted(f for f in os.listdir(OUT) if f.lower().endswith(".ttf"))
    if not files:
        print("fonts/ 下没有 TTF，无需处理")
        return 0
    print("模式：%s" % ("仅检查" if check_only else "就地修复"))
    print("%-26s %-28s %-28s %s" % ("文件", "旧 PostScript 名", "新 PostScript 名", "结果"))
    dup_before, dup_after = {}, {}
    for f in files:
        fname, old, new, changed = patch(os.path.join(OUT, f), check_only)
        dup_before.setdefault(old, []).append(fname)
        dup_after.setdefault(new, []).append(fname)
        print("%-26s %-28s %-28s %s" % (fname, old, new, "需修复" if changed else "已正确"))
    bad_before = {k: v for k, v in dup_before.items() if len(v) > 1}
    bad_after = {k: v for k, v in dup_after.items() if len(v) > 1}
    print()
    print("修复前重名：%s" % (bad_before or "无"))
    print("修复后重名：%s" % (bad_after or "无"))
    if bad_after:
        print("!! 仍有重名，请检查文件名与族名")
        return 1
    if check_only and bad_before:
        print("→ 存在重名，去掉 --check 执行修复")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
