# -*- coding: utf-8 -*-
"""印刷主题层：素材路径 / 调色板 / 字体族 / 位图缓存（ui 包公共底座）。"""
import os
import sys

from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter,
                           QPen, QPixmap)

from calendar_app import fonts as calendar_app_fonts


if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(os.path.abspath(sys.executable))
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ui/ 的上一级 = 工程根

SETTINGS_PATH = os.path.join(_BASE, "settings.json")

# 祭拜三清素材（frozen：随包附带于 _MEIPASS/祖师爷；源码：项目根/祖师爷）
if getattr(sys, "frozen", False):
    _ASSET_DIR = os.path.join(
        getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable))),
        "祖师爷")
else:
    _ASSET_DIR = os.path.join(_BASE, "祖师爷")

# 生肖剪影素材（frozen：_MEIPASS/生肖；源码：项目根/生肖）
if getattr(sys, "frozen", False):
    _ZODIAC_DIR = os.path.join(
        getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable))),
        "生肖")
else:
    _ZODIAC_DIR = os.path.join(_BASE, "生肖")
IMG_ZUSHIYE = os.path.join(_ASSET_DIR, "祖师爷.png")
IMG_XIANGLU = os.path.join(_ASSET_DIR, "香炉.png")

# 八卦图素材（frozen：_MEIPASS/八卦.png；源码：项目根/八卦.png）
if getattr(sys, "frozen", False):
    _ROOT_DIR = getattr(sys, "_MEIPASS",
                        os.path.dirname(os.path.abspath(sys.executable)))
else:
    _ROOT_DIR = _BASE
IMG_BAGUA = os.path.join(_ROOT_DIR, "八卦.png")
# 应用图标（logo.png：用于窗口 / 托盘 / exe 图标）
IMG_LOGO = os.path.join(_ROOT_DIR, "logo.png")
# 龙 / 凤 / 云纹剪纸素材（随主题红绿切换）
_LF_DIR = os.path.join(_ROOT_DIR, "龙凤")
# 联系作者图标（白底透明，运行时着色为墨色）
_ICON_DIR = os.path.join(_ROOT_DIR, "图标")
IMG_ICON_GITHUB = os.path.join(_ICON_DIR, "github.png")
IMG_ICON_BILIBILI = os.path.join(_ICON_DIR, "bilibili.png")
IMG_ICON_WEIBO = os.path.join(_ICON_DIR, "weibo.png")


def _tone_of(main) -> str:
    """按当日主题主色取「红 / 绿」：法定假日为红，平日为绿。"""
    return "红" if main.red() >= main.green() else "绿"


def _lf_asset(name: str, tone: str) -> str:
    """龙凤 / 云纹素材路径：<龙凤>/<name>（红|绿）.png"""
    return os.path.join(_LF_DIR, "%s（%s）.png" % (name, tone))

# ---- 纸色（节日主题只切换印刷色） ----
PAPER = QColor("#faf8f0")
PAPER_EDGE = QColor("#e6e2d4")
INK = QColor("#5a5a50")

# 颜色示意（取各色系代表色做小圆点）
COLOR_CHIPS = {"黑": "#2b2b2b", "蓝": "#3a5fa0", "灰": "#9a9a9a", "青": "#2e9d8b",
               "绿": "#2e8b57", "红": "#c0392b", "紫": "#7d3c98", "黄": "#c9a227",
               "棕": "#8d6e63", "白": "#f5f5f0", "金": "#d4af37", "银": "#b8c0c8"}


def _font(size, families, weight=QFont.Normal, italic=False):
    f = QFont()
    f.setFamilies(families)
    f.setPixelSize(size)
    f.setWeight(weight)
    f.setItalic(italic)
    return f


def _tinted_pixmap(path, color, size):
    """把白色透明图标重新着色（保留原有 alpha），用于浅色「关于」对话框。"""
    pm = QPixmap(path)
    if pm.isNull():
        return QPixmap()
    pm = pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    for y in range(img.height()):
        for x in range(img.width()):
            a = img.pixelColor(x, y).alpha()
            if a:
                c = QColor(color)
                c.setAlpha(a)
                img.setPixelColor(x, y, c)
    return QPixmap.fromImage(img)


def _mail_pixmap(color, size):
    """绘制信封图标（用于「邮箱」联系行）。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), 1.6))
    p.setBrush(Qt.NoBrush)
    r = QRectF(2.0, 5.0, size - 4.0, size - 10.0)
    p.drawRoundedRect(r, 2.0, 2.0)
    p.drawLine(r.left() + 2.0, r.top() + 1.6, size / 2.0, size * 0.58)
    p.drawLine(r.right() - 2.0, r.top() + 1.6, size / 2.0, size * 0.58)
    p.end()
    return pm


# ---------- 素材 / 底纹缓存 ----------
# 卡顿主因：绘制过程中直接 QPixmap(路径) 会在**每一帧**重新读盘 + 解码 + 平滑缩放
# （实测龙凤 4.5ms/帧、八卦 1.4ms/帧，整页 57ms/帧 ≈ 17fps，拖动窗口明显发滞）。
# 素材属于静态资源，按「路径」与「路径+目标尺寸」缓存即可。
_PIX_CACHE = {}
_PIX_SCALED_CACHE = {}
_PAPER_CACHE = {}


def _pix_cached(path):
    """按路径缓存的原始 QPixmap（缺失时返回空 pixmap 并缓存该结果）。"""
    pm = _PIX_CACHE.get(path)
    if pm is None:
        pm = QPixmap(path) if os.path.exists(path) else QPixmap()
        _PIX_CACHE[path] = pm
    return pm


def _pix_scaled(path, w, h):
    """按 (路径, 宽, 高) 缓存的预缩放 QPixmap（每帧省去一次平滑缩放）。"""
    key = (path, w, h)
    pm = _PIX_SCALED_CACHE.get(key)
    if pm is None:
        src = _pix_cached(path)
        if src.isNull():
            return QPixmap()
        pm = src.scaled(w, h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        _PIX_SCALED_CACHE[key] = pm
    return pm


def _paper_pixmap(w, h):
    """缓存纸面底纹（纸色 + 顶部微光渐变），避免每帧重算全屏渐变。"""
    pm = _PAPER_CACHE.get((w, h))
    if pm is None:
        pm = QPixmap(w, h)
        pm.fill(PAPER)
        q = QPainter(pm)
        g = QLinearGradient(0, 0, 0, h)
        g.setColorAt(0, QColor(255, 255, 255, 40))
        g.setColorAt(1, QColor(120, 110, 80, 18))
        q.fillRect(QRect(0, 0, w, h), g)
        q.end()
        _PAPER_CACHE[(w, h)] = pm
    return pm


# 字体族：内置字体（随 exe 发布的 Noto Serif/Sans SC 子集）优先，系统字体仅作兜底。
# 这样在任何 Windows 设备上字形完全一致，不会出现「换台机器字就变了」。
# 内置族不能在这里直接拼进列表 —— 注册字体必须在 QApplication 之后，
# 而 ui_main 常在任何 QApplication 之前就被 import；改由 use_builtin_fonts()
# 在创建控件时把内置族插到各列表最前（幂等）。
ZH_FONT = ["STZhongsong", "华文中宋", "SimSun", "NSimSun", "Microsoft YaHei"]
ZH_SONG = ["SimSun", "NSimSun", "宋体"]        # 正文统一宋体（原楷体/仿宋观感）
# 箴谶正文：无内置楷体，统一走内置宋体（字形一致优先于书体差异）
ZH_WISDOM = ["KaiTi", "楷体", "STKaiti", "STXingkai", "华文行楷", "SimSun"]
NUM_FONT = ["Rockwell", "Georgia", "Arial Black", "Arial"]
EN_FONT = ["Georgia", "Times New Roman", "Arial"]
_SERIF_LISTS = (ZH_FONT, ZH_SONG, ZH_WISDOM, NUM_FONT, EN_FONT)
_FONT_BUILTIN_DONE = False


def use_builtin_fonts():
    """把内置字体族插到上述字体列表最前（幂等；未注册则保持系统字体兜底）。"""
    global _FONT_BUILTIN_DONE
    if _FONT_BUILTIN_DONE:
        return True
    serif = calendar_app_fonts.SERIF_FAMILY
    if serif not in calendar_app_fonts.install_fonts():
        return False
    for lst in _SERIF_LISTS:
        if serif not in lst:
            lst.insert(0, serif)
    _FONT_BUILTIN_DONE = True
    return True


def palette_for(info: dict) -> dict:
    """按是否法定假日返回印刷配色（绿色 / 红色主题）。"""
    if info.get("holiday"):
        return {"main": QColor("#c62828"), "dark": QColor("#8e1a1a"),
                "pale": QColor("#f0b9b9"), "stamp_bg": QColor("#fceaea"),
                "box_bg": QColor("#f8efeb")}
    return {"main": QColor("#1f9c3d"), "dark": QColor("#136b29"),
            "pale": QColor("#8fcf9f"), "stamp_bg": QColor("#eaf6ec"),
            "box_bg": QColor("#f2efdf")}
