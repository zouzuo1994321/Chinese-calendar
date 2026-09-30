# -*- coding: utf-8 -*-
"""内置字体注册（防止不同设备字形不一致）。

软件所用中文字体随程序发布（SIL Open Font License 1.1，允许再分发）：
  · Noto Serif SC  Regular / Bold / Black   —— 正文与标题（印刷宋体观感）
  · Noto Sans SC   Regular / Bold           —— 界面控件与对话框
字体由 tools/build_fonts.py 从 OFL 可变字体实例化并子集化（GB2312 全集 + 源码用字），
共约 12.9 MB，随 exe 打包到 fonts/ 目录。

必须在 QApplication 之后、任何控件创建之前调用 install_fonts()（main.py 已接线）。
"""
import os
import sys

from PySide6.QtGui import QFontDatabase

# 内置族名（install_fonts 成功注册后即为可用族名）
SERIF_FAMILY = "Noto Serif SC"
SANS_FAMILY = "Noto Sans SC"

# 系统兜底族名（内置字体异常时仍可用，只是字形可能不同）
_FALLBACK_SERIF = ["STZhongsong", "华文中宋", "SimSun", "NSimSun", "宋体"]
_FALLBACK_SANS = ["Microsoft YaHei", "SimHei", "微软雅黑"]

_font_dir = None
_installed = None


def font_dir():
    """字体目录：冻结 exe 为解包目录/fonts，源码运行为工程根/fonts。"""
    global _font_dir
    if _font_dir:
        return _font_dir
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS",
                       os.path.dirname(os.path.abspath(sys.executable)))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _font_dir = os.path.join(base, "fonts")
    return _font_dir


def font_files():
    d = font_dir()
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.lower().endswith((".ttf", ".otf"))]


def install_fonts():
    """注册 fonts/ 下全部内置字体，返回成功加载的族名列表。

    必须在 QApplication 之后调用 —— 实测在没有任何 QGuiApplication 实例时
    调用 addApplicationFont 会直接段错误（Qt 字体库未初始化），故此处做守卫：
    无实例时返回空列表并等待后续调用。可重复调用（第二次起返回缓存）。
    """
    global _installed
    if _installed is not None:
        return _installed
    try:
        from PySide6.QtGui import QGuiApplication
        if QGuiApplication.instance() is None:
            return []          # 尚未创建 QApplication → 推迟注册，不缓存
    except Exception:
        return []
    ok = []
    for path in font_files():
        try:
            fid = QFontDatabase.addApplicationFont(path)
            if fid < 0:
                continue
            ok.extend(QFontDatabase.applicationFontFamilies(fid))
        except Exception:
            continue
    _installed = sorted(set(ok))
    return _installed


def serif_families():
    """正文/标题族名列表：内置宋体优先，系统字体兜底。"""
    return ([SERIF_FAMILY] if SERIF_FAMILY in (install_fonts()) else []) + _FALLBACK_SERIF


def sans_families():
    """界面控件族名列表：内置黑体优先，系统字体兜底。"""
    return ([SANS_FAMILY] if SANS_FAMILY in (install_fonts()) else []) + _FALLBACK_SANS


def sans_css():
    """给 QSS 用的 font-family 串（内置黑体优先）。"""
    return ", ".join("'%s'" % f for f in sans_families())


def serif_css():
    """给 QSS 用的 font-family 串（内置宋体优先）。

    v1.9.6：生肖下拉框 / 下拉列表改用本串 —— 内置黑体（Noto Sans SC）
    子集只覆盖顶栏小控件的拉丁与常用字形，生肖两字（子鼠…亥猪）在
    下拉列表里渲染成「--」；宋体（Noto Serif SC）随整页自绘文字使用，
    CJK 字形齐备，且与页面印刷风格一致。
    """
    return ", ".join("'%s'" % f for f in serif_families())


def report():
    """返回一行自检信息，供「关于本软件」显示字体状态。"""
    fams = install_fonts()
    if not fams:
        return "内置字体：未加载（回退系统字体）"
    return "内置字体：%s（%d 个族 / %.1f MB）" % (
        "、".join(fams), len(fams),
        sum(os.path.getsize(p) for p in font_files()) / 1048576.0)
