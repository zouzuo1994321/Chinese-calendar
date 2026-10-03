# -*- coding: utf-8 -*-
"""源码态综合复核：覆盖本次需求 + 性能 + 回归（版本号随 version.py 迭代）。"""
import os
import sys
import textwrap
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from datetime import date
from PIL import Image
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication

import ui_main
from ui_main import (CalendarPage, MainWindow, _lf_asset, _pix_cached,
                     _pix_scaled, _paper_pixmap, _tone_of, palette_for,
                     IMG_LOGO, _ZODIAC_DIR)
from calendar_app.engine import get_day_info
from calendar_app.version import APP_VERSION, BUILD_CODE, VERSION_TITLE

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""))


app = QApplication(sys.argv)
win = MainWindow()
win.show()
page = win.page

RED = date(2026, 9, 27)
GREEN = date(2026, 10, 10)


def setup(d):
    page.info = get_day_info(d)
    page.P = palette_for(page.info)
    return page.P


pr, pg = setup(RED), setup(GREEN)
ck("[1] 主题判定 红/绿", _tone_of(pr["main"]) == "红" and _tone_of(pg["main"]) == "绿",
   "%s/%s" % (_tone_of(pr["main"]), _tone_of(pg["main"])))
ck("[1] 龙凤四图齐备",
   all(os.path.exists(_lf_asset(n, t)) for n in ("龙", "凤") for t in ("红", "绿")))
h = 168
y = CalendarPage.NUM_RECT.y() + CalendarPage.NUM_RECT.height() // 2 - h // 2
ck("[1] 龙凤竖直居中于数字框", y == 119 and y + h == 287, "y=%d..%d" % (y, y + h))


def lf_ink(d):
    setup(d)
    page._sheen_t = 0.0
    page.repaint()      # 同步重绘；不可用 update()+processEvents()：页面自带的
    #                     定时器会在处理事件时把 page.info 重置回「今天」，
    #                     导致量到的是错日期的画面（v1.8.1 排查时踩到）
    img = page.grab().toImage()
    n = 0
    for yy in range(119, 287):
        for xx in list(range(30, 200)) + list(range(322, 492)):
            c = img.pixelColor(xx, yy)
            if c.red() < 245 or c.green() < 245 or c.blue() < 245:
                n += 1
    return n


ink_r, ink_g = lf_ink(RED), lf_ink(GREEN)
ck("[1] 红/绿两态均绘制龙凤水印", ink_r > 300 and ink_g > 300, "红=%d 绿=%d px" % (ink_r, ink_g))

ck("[2] 云纹两图齐备", all(os.path.exists(_lf_asset("云纹", t)) for t in ("红", "绿")))
pc = _pix_scaled(_lf_asset("云纹", "红"), 156, 15)
ck("[2] 云纹可缩放加载", not pc.isNull(), "%dx%d" % (pc.width(), pc.height()))


def cloud_ink(d):
    setup(d)
    page._sheen_t = 0.0
    page.repaint()      # 同步重绘；不可用 update()+processEvents()：页面自带的
    #                     定时器会在处理事件时把 page.info 重置回「今天」，
    #                     导致量到的是错日期的画面（v1.8.1 排查时踩到）
    img = page.grab().toImage()
    n = 0
    for yy in range(298, 317):
        for xx in list(range(20, 180)) + list(range(340, 500)):
            c = img.pixelColor(xx, yy)
            if c.red() < 245 or c.green() < 245 or c.blue() < 245:
                n += 1
    return n


cr, cg = cloud_ink(RED), cloud_ink(GREEN)
ck("[2] 云纹绘制于「X日 属X」两侧", cr > 100 and cg > 100, "红=%d 绿=%d px" % (cr, cg))


def corner_dots(d):
    """四角装饰圆点圆心必须恰落在外框顶点上（v1.7.0 曾右缘偏 6px）。"""
    setup(d)
    page._sheen_t = 0.0
    page.repaint()      # 同步重绘；不可用 update()+processEvents()：页面自带的
    #                     定时器会在处理事件时把 page.info 重置回「今天」，
    #                     导致量到的是错日期的画面（v1.8.1 排查时踩到）
    img = page.grab().toImage()
    main = palette_for(page.info)["main"]
    pts = [(14, 14), (page.PAGE_W - 14, 14),
           (14, CalendarPage.FRAME_OUT_BOTTOM),
           (page.PAGE_W - 14, CalendarPage.FRAME_OUT_BOTTOM)]
    hit = 0
    for x, y in pts:
        c = img.pixelColor(x, y)
        if (abs(c.red() - main.red()) <= 45 and abs(c.green() - main.green()) <= 45
                and abs(c.blue() - main.blue()) <= 45):
            hit += 1
    return hit, main.name()


hitr, mr = corner_dots(RED)
ck("[2] 页角圆点·红日四顶点命中", hitr == 4, "%d/4 main=%s" % (hitr, mr))
hitg, mg = corner_dots(GREEN)
ck("[2] 页角圆点·绿日四顶点命中", hitg == 4, "%d/4 main=%s" % (hitg, mg))

ck("[3] logo.png 被用作窗口图标",
   os.path.exists(IMG_LOGO) and not win.windowIcon().isNull(), os.path.basename(IMG_LOGO))
_main = open("main.py", encoding="utf-8").read()
ck("[3] main.py 中设置了应用级图标", "app.setWindowIcon(QIcon(logo))" in _main)
ck("[3] 托盘图标来自 logo.png", not win._make_tray_icon().isNull())
spec = open("农历日历.spec", encoding="utf-8").read()
for token in ("logo.png", "logo.ico", "龙凤/*.png", "图标/*.png"):
    ck("[3] spec 打包资源含 %s" % token, token in spec)

ck("[4] 缓存容器存在", all(hasattr(ui_main, n) for n in
   ("_PIX_CACHE", "_PIX_SCALED_CACHE", "_PAPER_CACHE")))
ck("[4] _pix_cached 命中同一对象", _pix_cached(IMG_LOGO) is _pix_cached(IMG_LOGO))
ck("[4] _pix_scaled 命中同一对象",
   _pix_scaled(IMG_LOGO, 40, 40) is _pix_scaled(IMG_LOGO, 40, 40))
ck("[4] _paper_pixmap 命中同一对象",
   _paper_pixmap(520, 841) is _paper_pixmap(520, 841))

setup(RED)
page._sheen_t = 0.0
page.update()
app.processEvents()
N = 30
t0 = time.perf_counter()
for i in range(N):
    page._sheen_t = i / float(N)
    page.repaint()
    app.processEvents()
ms = (time.perf_counter() - t0) * 1000.0 / N
ck("[4] 逐帧整页绘制 < 8ms（缓存生效）", ms < 8.0, "%.2f ms/帧 ≈ %.0f fps" % (ms, 1000.0 / ms))

import inspect
import re
bad = []
for m in ("_paint_dragon_phoenix", "_paint_cloud", "_paint_zodiac_watermark",
          "_paint_paper", "_paint_yiji"):
    f = getattr(page, m, None)
    if f is None:
        continue
    body = inspect.getsource(f)
    if re.search(r"QPixmap\(\s*[a-zA-Z_]", body) and "_pix_" not in body:
        bad.append(m)
ck("[4] 绘制路径不再直接 QPixmap(路径)", not bad, "违规=%s" % bad)

ck("[5] 高光周期够长", CalendarPage.SHEEN_PERIOD_MS >= 3000, "%dms" % CalendarPage.SHEEN_PERIOD_MS)
ck("[5] 高光透明度克制", 0 < CalendarPage.SHEEN_ALPHA <= 80, "alpha=%d" % CalendarPage.SHEEN_ALPHA)
ck("[5] 刷新区域限定在数字区", CalendarPage.SHEEN_RECT.contains(CalendarPage.NUM_RECT))
src = inspect.getsource(CalendarPage._paint_sheen)
ck("[5] 使用 45° 线性渐变", "QLinearGradient(-100.0, -100.0, 500.0, 500.0)" in src)
ck("[5] 以渐变画刷重绘同字形（自带裁切）", "QPen(QBrush(g)" in src)

ticks = 0
for _ in range(20):
    old = page._sheen_t
    page._tick_sheen()
    if page._sheen_t != old:
        ticks += 1
ck("[5] 定时推进高光相位", ticks >= 19, "20 次 tick 推进 %d 次" % ticks)
page._sheen_t = 0.99
page._tick_sheen()
ck("[5] 相位循环回绕 [0,1)", 0.0 <= page._sheen_t < 1.0, "_sheen_t=%.4f" % page._sheen_t)


def bright(d, t):
    """在指定日期 + 高光相位下取样数字区亮度。

    ⚠ 走 `repaint()` 同步重绘，**不能** `update()+processEvents()` ——
    后者会驱动跨日定时器把 `page.info` 重置回「今天」（绿色），
    于是 `bright(RED, ...)` 实际取到的是绿色页面，断言失去意义。
    """
    setup(d)
    page._sheen_t = t
    page.repaint()
    img = page.grab().toImage()
    assert page.info["date"] == d, "bright(): page.info 被重置为 %s" % page.info["date"]
    v = 0
    for yy in range(110, 296, 3):
        for xx in range(66, 458, 3):
            c = img.pixelColor(xx, yy)
            v += c.red() + c.green() + c.blue()
    return v


lo, hi = bright(RED, 0.0), bright(RED, 0.5)
ck("[5] 相位不同 → 数字区亮度不同（确有流光）", lo != hi, "v(0.0)=%d v(0.5)=%d" % (lo, hi))

ck("回归 法定假日 → 红", palette_for({"holiday": "国庆节"})["main"].name() == "#c62828")
ck("回归 平日 → 绿", palette_for({})["main"].name() == "#1f9c3d")
ck("回归 版本号 v%s / %s" % (APP_VERSION, BUILD_CODE),
   APP_VERSION == "1.9.16" and BUILD_CODE == "2609300017", VERSION_TITLE)
ck("回归 生肖水印素材齐备",
   all(os.path.exists(os.path.join(_ZODIAC_DIR, "%s（%s）.png" % (s, t)))
       for s in ("龙", "马") for t in ("红", "绿")))
ck("回归 页面尺寸 520x841（v1.9.10 底部按钮距外框 5px）",
   (page.PAGE_W, page.PAGE_H) == (520, 841))
ck("回归 软件 logo 已更新为新版（logo.png 1024² / logo.ico 多尺寸）",
   os.path.getsize(IMG_LOGO) > 500000
   and os.path.getsize(os.path.join(os.path.dirname(IMG_LOGO), "logo.ico")) > 100000,
   "logo.png=%d B" % os.path.getsize(IMG_LOGO))
from calendar_app import fonts as _fonts
from ui_main import ZH_FONT as _zhf, EN_FONT as _enf
ck("回归 内置字体已注册", _fonts.SERIF_FAMILY in _fonts.install_fonts(),
   _fonts.report())
ck("回归 ZH_FONT 首位为内置宋体", _zhf and _zhf[0] == _fonts.SERIF_FAMILY,
   str(_zhf[:2]))

# ---- [6] 宜/忌框下方「神位信息行」：喜神/财神/福神/冲煞/禄 必须全部显示完整 ----
# v1.9.4：随宜/忌满宽化（224 双栏），五行信息从「中缝 160px」挪到宜/忌框下方
# 独立一行，按满宽 5 槽等分（每槽 92px），过长项 elide 兜底，绝不溢出。
MID_Y = 462
MID_X0 = 30
MID_TOT = 460
MID_SLOTS = 5
MID_STEP = MID_TOT / MID_SLOTS


def _mid_ink_row(img, x0, x1, y0, y1):
    """统计神位信息行某槽内的「深墨」像素（阈值 120 过滤浅色底）。"""
    n = 0
    for yy in range(int(y0), int(y1)):
        for xx in range(int(x0), int(x1)):
            c = img.pixelColor(xx, yy)
            if 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue() < 120:
                n += 1
    return n


def mid_rows(d):
    setup(d)
    page._sheen_t = 0.0
    page.repaint()      # 同步重绘；不可用 update()+processEvents()：页面自带的
    #                     定时器会在处理事件时把 page.info 重置回「今天」，
    #                     导致量到的是错日期的画面（v1.8.1 排查时踩到）
    img = page.grab().toImage()
    return [_mid_ink_row(img, MID_X0 + i * MID_STEP, MID_X0 + (i + 1) * MID_STEP,
                         MID_Y, MID_Y + 16)
            for i in range(MID_SLOTS)]


for d, tag in ((RED, "红日"), (GREEN, "绿日")):
    per = mid_rows(d)
    ck("[6] 神位信息行（喜神/财神/福神/冲煞/禄）全部有字 · %s" % tag,
       all(v > 8 for v in per), "各槽像素=%s" % per)

_src_mid = inspect.getsource(CalendarPage._paint_yiji)
ck("[6] 宜/忌 回退 v1.9.3 窄 150 双栏（中缝放神位，v1.9.5）",
   "drawRect(30, y, 150, h)" in _src_mid
   and "drawRect(340, y, 150, h)" in _src_mid
   and "_draw_rows" not in _src_mid)
ck("[6] 神位信息竖排中缝 5 行（喜神/财神/福神/冲煞/禄，v1.9.3 回退）",
   "seam_x, seam_w = 186, 150" in _src_mid
   and '"喜神 %s" % info["pos_xi"]' in _src_mid)

from PySide6.QtGui import QFontMetricsF
from ui.theme import _font as _tf, SHEAR as _SHEAR
# v1.9.7：中缝神位文字加大加粗（11px→13px Bold），此处按新字号复刻 elide 逻辑
_fm13 = QFontMetricsF(_tf(13, _zhf, __import__("PySide6.QtGui",
                                              fromlist=["QFont"]).QFont.Bold))
_worst = ("", 0.0)


def _scan_lu():
    from datetime import timedelta
    global _worst
    slot = 150                                 # 中缝宽（与 page.py 一致）
    for i in range(1096):                      # 2026-01-01 起三年逐日
        info = get_day_info(date(2026, 1, 1) + timedelta(days=i))
        for r in ("喜神 %s" % info["pos_xi"], "财神 %s" % info["pos_cai"],
                  "福神 %s" % info["pos_fu"], "冲煞 %s" % info["chong"],
                  info["lu"]):
            # 复刻 page.py 渲染逻辑：elide 到 seam-6 后再量宽，
            # 验证「超长项由 elide 兜底、渲染后绝不溢出中缝」（v1.9.3 回退）
            el = _fm13.elidedText(r, Qt.ElideRight, slot - 6)
            w = _fm13.horizontalAdvance(el)
            if w > _worst[1]:
                _worst = (el, w)
    return _worst


_scan_lu()
ck("[6] 神位信息最宽项（13px Bold）elide 后必可容于中缝 150px（超长由 elide 兜底，无溢出）",
   _worst[1] <= 150, "elide后 %r = %.1fpx / 可用 150px" % (_worst[0], _worst[1]))

# ---- [7] 宜 / 忌 文本块：内置字体行距 20px，三行需 60px，旧文字区仅 48px ----
# 2026-01-06 宜「会亲友」第三行被裁（v1.8.1 修复）。此处锁定「最多三行 + 三行全可见」。
YIJI_X, YIJI_Y, YIJI_W, YIJI_H, YIJI_MAX = 35, 422, 140, 54, 3
_fm_demi = QFontMetricsF(_tf(14, _zhf, __import__("PySide6.QtGui",
                                                 fromlist=["QFont"]).QFont.DemiBold))


def _yiji_lines():
    from datetime import timedelta
    mx, sample = 0, None
    for i in range(1096):
        info = get_day_info(date(2026, 1, 1) + timedelta(days=i))
        for k in ("yi", "ji"):
            n = len(CalendarPage._wrap_px(
                _fm_demi, "、".join(info[k][:6]) or "—", YIJI_W))
            if n > mx:
                mx, sample = n, (info, k)
    return mx, sample


_maxlines, _sample = _yiji_lines()
ck("[7] 宜/忌 三年内最多 3 行（文字区按 3 行设计）", _maxlines <= YIJI_MAX,
   "最多 %d 行（含 3 行的样例 %r）" % (_maxlines, _sample[1]))


def _yiji_slots(text):
    """按 `_draw_para` 的同一套模型反推每行槽位 [top, bottom) 与行距。"""
    n = max(1, len(CalendarPage._wrap_px(_fm_demi, text, YIJI_W)))
    step = min(_fm_demi.height(), YIJI_H / float(n))
    return [(int(YIJI_Y + i * step), int(YIJI_Y + (i + 1) * step))
            for i in range(n)]


def _yiji_ink(d):
    """逐行统计宜 / 忌文字区内的深墨像素，返回 [(槽位数, 各行像素, 末行墨迹底 y)]。"""
    setup(d)
    page._sheen_t = 0.0
    # 同步重绘 + 不处理事件：processEvents() 会让页面自带定时器把 page.info
    # 重置回「今天」（主窗口每 30s 的跨日轮询），量到的就不是目标日期了
    page.repaint()
    img = page.grab().toImage()
    out = []
    for x0, key in ((35, "yi"), (345, "ji")):
        text = "、".join(page.info[key][:6]) or "—"
        slots = _yiji_slots(text)
        if os.environ.get("SYY_DBG"):        # SYY_DBG=1 时打印断行与槽位明细
            print("DBG %s %s lines=%r slots=%s" % (
                key, d, CalendarPage._wrap_px(_fm_demi, text, YIJI_W), slots))
        per = []
        for yy0, yy1 in slots:
            n = 0
            for yy in range(yy0, min(yy1, YIJI_Y + YIJI_H)):
                for xx in range(x0, x0 + YIJI_W):
                    c = img.pixelColor(xx, yy)
                    if (0.299 * c.red() + 0.587 * c.green()
                            + 0.114 * c.blue()) < 120:
                        n += 1
            per.append(n)
        last_bottom = 0
        for yy in range(YIJI_Y + YIJI_H - 1, YIJI_Y - 1, -1):
            if any((0.299 * img.pixelColor(xx, yy).red()
                    + 0.587 * img.pixelColor(xx, yy).green()
                    + 0.114 * img.pixelColor(xx, yy).blue()) < 120
                   for xx in range(x0, x0 + YIJI_W)):
                last_bottom = yy
                break
        out.append((len(slots), per, last_bottom))
    return out


for _d, _tag in ((date(2026, 1, 6), "三行日"), (RED, "两行日"), (GREEN, "两行日")):
    _res = _yiji_ink(_d)
    _ok = all(all(v > 20 for v in per) for _n, per, _lb in _res)
    ck("[7] %s %s：宜/忌 每一行均有墨（无缺行）" % (_tag, _d), _ok,
       "宜=%d行%s 忌=%d行%s" % (_res[0][0], _res[0][1], _res[1][0], _res[1][1]))
    _lb = max(r[2] for r in _res)
    ck("[7] %s %s：末行墨迹未触底边（未被裁切）" % (_tag, _d),
       _lb <= YIJI_Y + YIJI_H - 2,
       "末行底 y=%d / 文字区底 y=%d" % (_lb, YIJI_Y + YIJI_H))

_src_yi = inspect.getsource(CalendarPage._paint_yiji)
ck("[7] 宜/忌 改手工断行绘制（不再用 TextWordWrap）",
   "_draw_para(" in _src_yi and "TextWordWrap" not in _src_yi)
ck("[7] 行距与字体解耦：step 由 rect/行数决定",
   "rect.height() / float(len(lines))" in inspect.getsource(
       CalendarPage._draw_para))
_wl = CalendarPage._wrap_px(_fm_demi, "会亲友、出行、安床、祭祀、祈福、安葬", 92)
ck("[7] 断行优先在「、」处、标点不落行首",
   len(_wl) >= 2 and all(not ln.startswith("、") for ln in _wl), str(_wl))

# ---- [8] 页头英文月份 / 英文星期：加粗取自内置字体 Black(900) 实例 ----
# 背景：EN_FONT 在 use_builtin_fonts() 后被插成 ['Noto Serif SC', 'Georgia', ...]，
# 而内置族只打包了 Regular/Bold/Black 三个静态实例，故 weight 参数必须真的命中
# 三者之一，否则 Qt 退回合成加粗（观感几乎无变化）。用墨迹像素量锁死「真加粗」。
from PySide6.QtGui import QFont as _QF, QImage as _QImg, QPainter as _QP, QColor as _QC
from PySide6.QtCore import Qt as _Qt
MONTHS_EN = ("JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
             "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER")


def _month_px(month):
    """按 _paint_header 的同一套模型算出实际字号（基准 EN_MONTH_PX，超宽整字收敛）。"""
    area_w = 196
    px = CalendarPage.EN_MONTH_PX
    adv = QFontMetricsF(_tf(px, _enf, _QF.Black)).horizontalAdvance(month)
    if adv > area_w:
        px = max(12, int(px * area_w / adv))
    return px


def _en_ink(text, weight, px, italic=False):
    """渲染一段英文并统计深墨像素量，用于比较字重是否真的生效。

    ⚠ `italic` 默认 **False**：内置 Noto 系无斜体面，`setItalic(True)` 会触发
    Qt 合成斜体分支并吞掉字重轴（实测 Bold/Black 与 Regular 墨迹完全相同）。
    页头月名因此改用 `_painter_shear()` 做几何切变，故此处以非斜体量字重。
    """
    img = _QImg(320, 60, _QImg.Format_ARGB32)
    img.fill(_Qt.white)
    q = _QP(img)
    q.setRenderHint(_QP.Antialiasing, False)   # 关抗锯齿，墨迹量可比
    q.setFont(_tf(px, _enf, weight, italic=italic))
    q.setPen(_QC("#000000"))
    q.drawText(0, 42, text)
    q.end()
    return sum(1 for y in range(60) for x in range(320)
               if img.pixelColor(x, y).red() < 160)


# ---- [8] 内置字体的字重必须真的可区分（v1.8.2 真实运行环境翻车点）----
# 背景：build_fonts.py 的 set_names() 漏改 nameID 3/6（PostScript 名 / 唯一标识），
# instantiateVariableFont(updateFontNames=False) 让 Regular/Bold/Black 三份的 PS 名
# 完全相同（都是 NotoSerifSC-ExtraLight），Windows 以 PS 名作注册键 → 三字重互相覆盖，
# 请求 Bold/Black 全部落回同一面，页头英文「只是变大、不会加粗」。
# **离屏渲染恰好不读这条路径**，所以旧断言全绿却掩盖了线上问题 —— 这里改为直接校验
# 字体文件的 name 表（平台无关），并用真实平台量墨迹梯度。
from fontTools.ttLib import TTFont as _TTFont
_font_dir = os.path.join(_ROOT, "fonts")
_ttfs = sorted(f for f in os.listdir(_font_dir) if f.lower().endswith(".ttf"))
_ps_names, _uids = {}, {}
for _f in _ttfs:
    _t = _TTFont(os.path.join(_font_dir, _f))
    _ps_names[_f] = _t["name"].getDebugName(6)
    _uids[_f] = _t["name"].getDebugName(3)
    _t.close()
ck("[8] 内置字体 PostScript 名（nameID 6）互不重复",
   len(set(_ps_names.values())) == len(_ps_names),
   "重名=%s" % ({k: v for k, v in _ps_names.items()} if len(set(_ps_names.values())) != len(_ps_names) else "无"))
ck("[8] 内置字体唯一标识（nameID 3）互不重复",
   len(set(_uids.values())) == len(_uids),
   "共 %d 份字体" % len(_ttfs))
_serif_ps = {f: _ps_names[f] for f in _ttfs if f.startswith("NotoSerifSC")}
ck("[8] Noto Serif SC 三个字重的 PS 名各不相同",
   len(set(_serif_ps.values())) == 3, str(_serif_ps))

# 字重梯度：Black 墨迹必须显著厚于 Regular（非斜体路径）
_norm = _en_ink("OCTOBER", _QF.Normal, 26)
_demi = _en_ink("OCTOBER", _QF.DemiBold, 26)
_blk = _en_ink("OCTOBER", _QF.Black, 26)
ck("[8] 英文 Black(900) 墨迹显著多于 Normal(400)（真加粗）",
   _blk > _norm * 1.15 and _demi > _norm * 1.10,
   "Normal=%d DemiBold=%d Black=%d (+%.0f%%)"
   % (_norm, _demi, _blk, (_blk - _norm) * 100.0 / _norm))
_hd_src = inspect.getsource(CalendarPage._paint_header)
# 注意：注释里会出现 "italic=True" 字样（解释为何不能用它），故只校验**代码行**
_hd_code = "\n".join(ln for ln in _hd_src.splitlines()
                     if not ln.strip().startswith("#"))
ck("[8] 内置字体不被 italic 吞掉字重（页头改用 _painter_shear）",
   "italic=True" not in _hd_code and "_painter_shear" in _hd_code)

_adv = {m: QFontMetricsF(_tf(CalendarPage.EN_MONTH_PX, _enf, _QF.Black)).horizontalAdvance(m)
        for m in MONTHS_EN}
_wide = max(_adv, key=lambda m: _adv[m])
# ⚠ 可用宽度必须减去**切变溢出量**（v1.8.5 教训）：页头月名走 `_painter_shear`，
# 字形底部向右伸出 |SHEAR| × descent、顶部向左伸出 |SHEAR| × ascent。旧断言只比
# advance 且硬编码 196px，于是 26px 的 SEPTEMBER（adv=178 看似合规）实际渲染
# 185.5px、左缘顶到内框线 —— 用户看到的就是「英文出框」。这里按真实几何口径断言。
_HDR_AREA = QRect(*CalendarPage.EN_MONTH_RECT)
_fm_hdr = QFontMetricsF(_tf(CalendarPage.EN_MONTH_PX, _enf, _QF.Black))
_shear_extra = abs(_SHEAR) * (_fm_hdr.ascent() + _fm_hdr.descent())
_avail_hdr = _HDR_AREA.width() - _shear_extra
ck("[8] 12 个月名含切变后均不超页头可用宽（基准 %dpx）" % CalendarPage.EN_MONTH_PX,
   all(_adv[m] + _shear_extra <= _HDR_AREA.width() for m in MONTHS_EN),
   "最宽 %s = %.1fpx + 切变 %.1fpx = %.1fpx / 可用 %dpx"
   % (_wide, _adv[_wide], _shear_extra, _adv[_wide] + _shear_extra, _HDR_AREA.width()))
ck("[8] 页头月名绘制把切变溢出计入宽度判断（防出框）",
   "SHEAR" in _hd_src and "shear_extra" in _hd_src,
   "阈值=可用 %.1fpx（已扣切变）" % _avail_hdr)
# ⚠⚠ 这是 v1.8.6 才补上的**关键断言**：上面两条只管「右边会不会超宽」，
# 完全没管「左边会不会压线」—— 而用户两次反馈的正是左边出框。
# 切变以 area.left 为轴、SHEAR=-0.25，字形顶部向左倾 |SHEAR|×ascent，
# 叠上字形自身左缘倾斜后，整条月名墨迹会比 area.left 再左移约 20px。
# 故必须**真实渲染并量墨迹左缘**，抽象计算（advance / 估算）在这里完全不可靠。
from PySide6.QtGui import QImage as _QImg2, QPainter as _QP2, QPen as _QPen2, QColor as _QC2
from PySide6.QtCore import Qt as _Qt2


def _hdr_ink_x(m):
    """把月名单独渲染到空白画布，返回 (最左墨迹 x, 最右墨迹 x)。

    不叠加整页，避免页边**框线**（外框 x=14 / 内框 x=21）混进墨迹统计 ——
    早期用整页量测时，12 个月名都「量」到 x=14，那其实是框线而非文字。
    """
    im = _QImg2(520, 120, _QImg2.Format_ARGB32)
    im.fill(_QC2("white"))
    p = _QP2(im)
    p.setRenderHint(_QP2.Antialiasing)
    a = CalendarPage.EN_MONTH_RECT
    fnt = _tf(CalendarPage.EN_MONTH_PX, _enf, _QF.Black)
    fmm = QFontMetricsF(fnt)
    adv, extra = fmm.horizontalAdvance(m), abs(_SHEAR) * (fmm.ascent() + fmm.descent())
    if adv > a[2] - extra:                       # 复刻 _paint_header 的缩字号分支
        fnt = _tf(max(11, int(CalendarPage.EN_MONTH_PX * (a[2] - extra) / adv)),
                  _enf, _QF.Black)
        fmm = QFontMetricsF(fnt)
    left_x = a[0]                                # 复刻 _paint_header 的兜底右移分支
    est = left_x - abs(_SHEAR) * fmm.ascent()
    if est < CalendarPage.EN_MONTH_MIN_X:
        left_x += CalendarPage.EN_MONTH_MIN_X - est
    p.setPen(_QPen2(_QC2("black")))
    p.save()
    from ui.theme import _painter_shear as _ps
    _ps(p, left_x)
    p.setFont(fnt)
    p.drawText(QRect(left_x, a[1], a[2], a[3]), _Qt2.AlignVCenter | _Qt2.AlignLeft, m)
    p.restore()
    p.end()
    xmin, xmax = 9999, -1
    for y in range(im.height()):
        for x in range(im.width()):
            if im.pixelColor(x, y).lightness() < 128:
                xmin, xmax = min(xmin, x), max(xmax, x)
    return xmin, xmax


_hdr_inks = {m: _hdr_ink_x(m) for m in MONTHS_EN}
_hdr_worst = min(_hdr_inks, key=lambda m: _hdr_inks[m][0])
_hdr_right = max(_hdr_inks[m][1] for m in MONTHS_EN)
ck("[8] 12 个月名渲染墨迹左缘均在内框线（x=21）右侧、不压线出框",
   all(_hdr_inks[m][0] >= CalendarPage.EN_MONTH_MIN_X for m in MONTHS_EN),
   "最左 %s = x%d（要求 ≥%d，内框线 21）"
   % (_hdr_worst, _hdr_inks[_hdr_worst][0], CalendarPage.EN_MONTH_MIN_X))
ck("[8] 页头月名绘制含「左缘兜底右移」分支（防压线）",
   "EN_MONTH_MIN_X" in _hd_src and "est_left" in _hd_src,
   "月名最右墨迹 = x%d（年份区起点约 180，无侵占）" % _hdr_right)
ck("[8] 长月名不再缩字号（12 个月名统一 %dpx）" % CalendarPage.EN_MONTH_PX,
   all(_month_px(m) == CalendarPage.EN_MONTH_PX for m in MONTHS_EN),
   "字号集合=%s" % sorted({_month_px(m) for m in MONTHS_EN}))
_src_hd = inspect.getsource(CalendarPage._paint_header)
ck("[8] 页头英文月份走 Black(900) 且字号自适应",
   "_font(self.EN_MONTH_PX, EN_FONT, QFont.Black)" in _src_hd
   and "setPixelSize" in _src_hd)
_src_mb = inspect.getsource(CalendarPage._paint_middle_band)
ck("[8] 英文星期改用 Black(900)，与页头字重一致",
   "_font(11, EN_FONT, QFont.Black)" in _src_mb
   and "_font(11, EN_FONT, QFont.Bold)" not in _src_mb)
_src_ft = inspect.getsource(CalendarPage._paint_footer)
ck("[8] 页脚版权行英文品牌名加粗、中文说明保持常规",
   "VER.COPYRIGHT" in _src_ft and "QFont.Bold" in _src_ft
   and "fm_b" in _src_ft)
_wk = max(("MONDAY", "WEDNESDAY", "SUNDAY"),
          key=lambda s: QFontMetricsF(_tf(11, _enf, _QF.Black)).horizontalAdvance(s))
ck("[8] 英文星期在 150px 框内不溢出",
   QFontMetricsF(_tf(11, _enf, _QF.Black)).horizontalAdvance(_wk) <= 150,
   "%s = %.1fpx / 可用 150px" % (
       _wk, QFontMetricsF(_tf(11, _enf, _QF.Black)).horizontalAdvance(_wk)))

# ---- [9] 箴言 / 谶言：竖排渲染不缺列、不溢出，且全部条目必须 ≤10 字 ----
from calendar_app.engine import OMENS as _OMENS, WISDOM_MAXIMS as _WIS
# v1.8.5 删掉 3 条超 10 字的箴言（「忍耐是金，退一步海阔天空。」「岁寒，然后知松柏
# 之后凋也。」「三军可夺帅也，匹夫不可夺志也。」——11/12/13 字，超出 5 行 × 2 列上限
# 会被截断）。故两库长度**不再相等**：箴 57 / 谶 60，这里按实际值断言并在失败信息里
# 报出偏差，避免以后有人「顺手补齐」又把超长条目塞回来。
ck("[9] 箴言 57 条 / 谶言 60 条", len(_WIS) == 57 and len(_OMENS) == 60,
   "箴=%d 谶=%d" % (len(_WIS), len(_OMENS)))
ck("[9] 箴 / 谶 库内无重复条目",
   len(set(_WIS)) == len(_WIS) and len(set(_OMENS)) == len(_OMENS))
_wc = [CalendarPage._wisdom_chars(t) for t in _WIS]
_oc = [CalendarPage._wisdom_chars(t) for t in _OMENS]
# ⚠ 这条是 v1.8.5 的直接护栏：竖排上限 5 行 × 2 列 = 10 字，超了会被 _wisdom_chars
# 静默截断、条目显示不全。新增条目必须先过这里。
_lim = CalendarPage.WIS_MAX_ROWS * CalendarPage.WIS_MAX_COLS
_over = [t for t, c in list(zip(_WIS, _wc)) + list(zip(_OMENS, _oc)) if len(c) > _lim]
ck("[9] 全部条目字数 ≤10（超出会被竖排截断，v1.8.5 事故）", not _over,
   "超限=%s" % _over if _over else "最长=%d 字" % max(len(c) for c in _wc + _oc))
ck("[9] 全部条目竖排字符数在 1~10 之间",
   all(1 <= len(c) <= _lim for c in _wc + _oc),
   "最长=%d 字（%s）" % (max(len(c) for c in _wc + _oc),
                      max(_WIS + _OMENS, key=lambda t: len(CalendarPage._wisdom_chars(t)))))
ck("[9] 标点不进竖排（剔除，。；、！？— 与空格）",
   all(not set(c) & set("，。；、！？— ") for c in _wc + _oc))
_lens = {len(c) for c in _wc + _oc}
ck("[9] 短条目走单列居中、长条目走两列（列数按字数自适应）",
   min(_lens) <= CalendarPage.WIS_MAX_ROWS < max(_lens),
   "字数分布=%d..%d" % (min(_lens), max(_lens)))


def _wis_ink(d):
    """统计页面上箴 / 谶两个竖排块的深墨像素与占用的行数。"""
    setup(d)
    page._sheen_t = 0.0
    page.repaint()
    img = page.grab().toImage()
    out = []
    for x0 in (26, 444):                       # 箴块 / 谶块
        rows_hit, total = 0, 0
        y0 = 134
        for r in range(CalendarPage.WIS_MAX_ROWS):
            n = 0
            for y in range(y0 + 34 + r * 22, y0 + 34 + r * 22 + 22):
                for x in range(x0, x0 + 50):
                    c = img.pixelColor(x, y)
                    if 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue() < 120:
                        n += 1
            if n > 6:
                rows_hit += 1
            total += n
        out.append((rows_hit, total))
    return out


for _d, _tag in ((date(2026, 9, 28), "短条"), (date(2026, 10, 12), "长条")):
    _r = _wis_ink(_d)
    _ok = all(tot > 60 for _rows, tot in _r)
    ck("[9] %s %s：箴 / 谶 两块均有字" % (_tag, _d), _ok,
       "箴块=%d 谶块=%d" % (_r[0][1], _r[1][1]))
    ck("[9] %s %s：竖排行数不超过 5 行（未溢出块高）" % (_tag, _d),
       all(rows <= CalendarPage.WIS_MAX_ROWS for rows, _t in _r),
       "箴=%d行 谶=%d行" % (_r[0][0], _r[1][0]))


def shot(d, t, path):
    """渲染指定日期 + 高光相位，存为 README 截图。

    ⚠⚠ v1.8.7 修复：此处**绝不能调 `app.processEvents()`**。
    主窗口有一个每 30s 的跨日轮询定时器，`processEvents()` 会把它驱动起来，
    把 `page.info` 重置回「今天」（2026-09-28，绿色主题）—— 于是**红日截图也变成
    绿日**，README 里两张图配色全错（用户 2026-09-28 反馈「修复 README 中的截图」）。
    正确姿势（见 SKILL.md「离屏像素断言的正确姿势」）：
        setup(d) → page._sheen_t = t → page.repaint() → page.grab()
    只用 `repaint()` 同步重绘，不碰事件循环。
    """
    setup(d)
    page._sheen_t = t
    page.repaint()                      # 同步重绘；不用 update()+processEvents()
    img = page.grab()
    img.save(path)
    # 自检：确认存下来的确实是目标日期的画面，而不是被跨日定时器重置回「今天」
    assert page.info["date"] == d, \
        "截图 %s 的 page.info 被重置为 %s（期望 %s）" % (path, page.info["date"], d)
    return Image.open(path).size


print("预览:", shot(RED, 0.34, "docs/screenshots/screenshot-red.png"),
      shot(GREEN, 0.34, "docs/screenshots/screenshot-green.png"))
# ⚠ 同样不能走 processEvents（会把 page.info 重置回今天，窗口截图就变绿日了）
setup(RED)
page._sheen_t = 0.30
page.repaint()
win.grab().save("docs/screenshots/screenshot-window.png")
print("预览: docs/screenshots/screenshot-window.png", Image.open("docs/screenshots/screenshot-window.png").size)

setup(RED)
CROP = QRect(50, 96, 420, 214)
tiles = []
_tmp = "_sheen_tmp.png"
try:
    for t in (0.00, 0.14, 0.28, 0.42, 0.56, 0.70, 0.84, 0.97):
        page._sheen_t = t
        page.repaint()                  # 同步重绘，不驱动事件循环
        page.grab().copy(CROP).save(_tmp)
        tiles.append(Image.open(_tmp).convert("RGB"))
    W, H = tiles[0].size
    canvas = Image.new("RGB", (W * 2 + 12, H * 4 + 36), (255, 255, 255))
    for i, im in enumerate(tiles):
        canvas.paste(im, ((i % 2) * (W + 12), (i // 2) * (H + 12)))
    canvas.save("docs/screenshots/screenshot-sheen.png")
    print("预览: docs/screenshots/screenshot-sheen.png", canvas.size)
finally:
    if os.path.exists(_tmp):       # 自清理：不留过程文件
        os.remove(_tmp)

# ---- 把四张截图以 base64 内嵌进 README（避免外链与图片丢失，v1.8.8）----
# 用户明确要求：「把软件截图直接加入 readme 中避免每次还要外链，并且有图片丢失的可能」。
# 每次跑 verify_ui 都重渲染截图 → 重嵌 base64，保证 README 里的图永远是最新的。
def _embed_shots_to_readme():
    """把四张截图以 base64 内嵌进 README 的「真实截图」小节。

    ⚠ v1.9.12：**整节重建**，不再只做 `![alt](url)` 定点替换。
    原因：曾出现 README 的 `![绿日](data:...)` 被外部（编辑器/格式化）改回**纯占位文字**
    `| 绿日 |`，此时定点替换找不到锚点 → 静默跳过 → 四张图永久丢失（`[10]` 会红）。
    改为用正则定位「## 📸 真实截图 … 至下一个 `---`」整块并重写，无论此前被改成什么样都能自愈。
    """
    import re, base64
    pairs = [("绿日", "screenshot-green.png"), ("红日", "screenshot-red.png"),
             ("窗口", "screenshot-window.png"), ("高光", "screenshot-sheen.png")]
    uris = {}
    for alt, fn in pairs:
        path = os.path.join("docs", "screenshots", fn)
        if not os.path.exists(path):
            print("⚠ 截图缺失，跳过内嵌:", fn)
            return
        uris[alt] = "data:image/png;base64," + base64.b64encode(
            open(path, "rb").read()).decode("ascii")
    section = (
        "## 📸 真实截图\n\n"
        "| 绿日（平日） | 红日（法定假日） |\n"
        "| :----: | :------: |\n"
        "| ![绿日](%s) | ![红日](%s) |\n\n"
        "| 完整窗口（含叠页纸面与边框） | 数字高光流动的瞬间 |\n"
        "| :------------: | :-------: |\n"
        "| ![窗口](%s) | ![高光](%s) |\n\n"
        "> 截图由 `tools/dev_checks/verify_ui.py` 离屏渲染真实窗口内容生成，所见即所得。  \n"
        "> 自 v1.8.0 起软件**内置全部字体**（Noto Serif SC / Noto Sans SC 子集），"
        "因此字形在任何 Windows 设备上都完全一致。"
        % (uris["绿日"], uris["红日"], uris["窗口"], uris["高光"]))
    src = open("README.md", encoding="utf-8").read()
    pat = re.compile(r"## 📸 真实截图\n.*?(?=\n---\n)", re.S)
    if pat.search(src):
        src = pat.sub(lambda _m: section, src, count=1)
    else:
        # 兜底：整节定位失败时，退回定点替换（至少保住已有锚点的情况）
        for alt, fn in pairs:
            _p = r'!\[' + re.escape(alt) + r'\]\([^)]*\)'
            src, n = re.subn(_p, '![' + alt + '](' + uris[alt] + ')', src)
            if n == 0:
                print("⚠ README 未找到 ![alt] 标记且整节定位失败:", alt)
    open("README.md", "w", encoding="utf-8").write(src)

_embed_shots_to_readme()

failed = [n for n, c, _ in R if not c]

# ---- [10] README 截图交付物：渲染路径不得用 processEvents，且文件确实存在 ----
# ⚠ v1.8.7 用户反馈「修复 README 中的软件截图」。两个问题：
#   ① README 的截图表格里**只有占位文字、没有图片引用**；
#   ② `shot()` 用 `update()+processEvents()` 渲染 → 跨日定时器把 page.info 重置回
#      「今天」（绿色），于是**「红日」截图存下来是绿色的**，README 两张图配色全错。
# 这里在截图生成之后（函数已定义）断言路径干净 + 四张图齐备。
_shot_src = inspect.getsource(shot)
_bright_src = inspect.getsource(bright)


def _code_only(src):
    """只保留可执行代码行。

    需要同时剔掉两类「非代码」文本，否则会误报：
      · `#` 注释行；
      · **docstring 里的说明** —— `shot()` / `bright()` 的 docstring 有意写着
        「不能用 processEvents」作为警示，那是文档而不是调用。
    做法：解析 AST，只保留非 docstring 的语句所在行号。
    """
    import ast
    tree = ast.parse(textwrap.dedent(src))
    body = tree.body[0].body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]                      # 丢掉函数自己的 docstring
    nocomment = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
    lines = textwrap.dedent(nocomment).splitlines()
    keep = set()
    for node in body:
        for ln in range(node.lineno - 1,
                        getattr(node, "end_lineno", node.lineno)):
            keep.add(ln)
    return "\n".join(lines[i] for i in sorted(keep) if i < len(lines))


ck("[10] 截图/bright 渲染路径不含 processEvents（防红日存成绿日）",
   "processEvents" not in _code_only(_shot_src)
   and "processEvents" not in _code_only(_bright_src),
   "shot/bright 均走 repaint() 同步重绘")
ck("[10] 截图函数带 page.info 日期自检（防被定时器重置）",
   "assert page.info" in _shot_src and "assert page.info" in _bright_src)
_SHOTS = ("screenshot-red.png", "screenshot-green.png",
          "screenshot-window.png", "screenshot-sheen.png")
_missing = [s for s in _SHOTS
            if not os.path.exists(os.path.join("docs", "screenshots", s))]
ck("[10] README 四张截图文件齐备", not _missing, "缺失=%s" % _missing if _missing else "4/4")
# README 必须把四张图以 base64 data URI 内嵌（v1.8.8：不再用 docs/screenshots/ 外链，
# 避免图片丢失）。曾经是空占位文字，v1.8.7 改为相对路径，v1.8.8 改为 base64 内嵌。
_readme = open("README.md", encoding="utf-8").read()
_b64_count = _readme.count("data:image/png;base64,")
# 用 alt 文本确认四张图都在（base64 内容每次重渲染会变，不能直接当 key）
_have_alts = all(("![" + a + "](data:image/png;base64,") in _readme
                 for a in ("绿日", "红日", "窗口", "高光"))
ck("[10] README 四张截图已 base64 内嵌（非外链 / 非占位文字）",
   _b64_count >= 4 and _have_alts,
   "data URI=%d  alt齐=%s" % (_b64_count, _have_alts))

# ---- [11] 今日成语（v1.8.9）：分段映射 + 居中绘制 + 随主题红绿 ----
# 用户需求：红框区域（年份行与巨大数字之间的居中空带）按今日分数显示成语，
# 分数取「生肖分优先，未选生肖用本日分」；字体参考箴/谶标题（华文中宋 Black）。
# 分段表 + 边界值（每段首尾）全部钉死：
_band_expect = [(0, "否极泰来"), (5, "否极泰来"), (9, "否极泰来"),
                (10, "绝处逢生"), (19, "绝处逢生"),
                (20, "转危为安"), (29, "转危为安"),
                (30, "化险为夷"), (39, "化险为夷"),
                (40, "逢凶化吉"), (49, "逢凶化吉"),
                (50, "时来运转"), (59, "时来运转"),
                (60, "渐入佳境"), (68, "渐入佳境"), (69, "渐入佳境"),
                (70, "万事顺遂"), (79, "万事顺遂"),
                (80, "吉星高照"), (89, "吉星高照"),
                (90, "圆满无缺"), (98, "圆满无缺"), (100, "圆满无缺")]
_bad = [(s, CalendarPage.idiom_for_score(s), want)
        for s, want in _band_expect if CalendarPage.idiom_for_score(s) != want]
ck("[11] 分数段→成语 映射 23 个边界值全对", not _bad, "错=%s" % _bad if _bad else "23/23")
_hd2_src = inspect.getsource(CalendarPage._paint_header)
ck("[11] 成语绘制：生肖分优先、无生肖用本日分",
   'rep.get("score")' in _hd2_src and "fortune_score" in _hd2_src)
ck("[11] 成语字体同箴/谶标题（ZH_FONT Black）+ 颜色随主题（dark）",
   "ZH_FONT" in _hd2_src and "QFont.Black" in _hd2_src and "QPen(dark)" in _hd2_src)
ck("[11] 成语居中绘制于 IDIOM_RECT",
   "IDIOM_RECT" in _hd2_src and "Qt.AlignCenter" in _hd2_src)

def _idiom_ink(d):
    """渲染整页，返回成语带内的墨迹统计 (像素数, bbox中心x, bbox顶y, bbox底y)。
    只统计 x 130–360 / y 96–140 —— 左「丙午年·马」墨迹止于 ~114、
    右「节气」起于 ~369，巨大数字墨迹顶 ~144，均不会混进本窗口。"""
    setup(d)
    page.zodiac_report = None          # 未选生肖口径：用本日分数
    page._sheen_t = 0.0
    page.repaint()
    img = page.grab().toImage()
    n, xmin, xmax, ymin, ymax = 0, 9999, -1, 9999, -1
    for yy in range(96, 141):
        for xx in range(130, 361):
            if img.pixelColor(xx, yy).lightness() < 128:
                n += 1
                xmin, xmax = min(xmin, xx), max(xmax, xx)
                ymin, ymax = min(ymin, yy), max(ymax, yy)
    if not n:
        return 0, -1, -1, -1
    return n, (xmin + xmax) // 2, ymin, ymax

_ink_red = _idiom_ink(RED)
_ink_green = _idiom_ink(GREEN)
ck("[11] 红日页成语带内有墨迹（成语真的画出来了）", _ink_red[0] > 200,
   "n=%d" % _ink_red[0])
ck("[11] 绿日页成语带内有墨迹", _ink_green[0] > 200, "n=%d" % _ink_green[0])
ck("[11] 成语水平居中（红/绿 bbox 中心均在页中线 260±12）",
   abs(_ink_red[1] - 260) <= 12 and abs(_ink_green[1] - 260) <= 12,
   "红中心=%s 绿中心=%s" % (_ink_red[1], _ink_green[1]))
ck("[11] 成语墨迹留在本带内（y 98–138，不压巨大数字）",
   _ink_red[2] >= 98 and _ink_red[3] <= 138 and
   _ink_green[2] >= 98 and _ink_green[3] <= 138,
   "红y=%s..%s 绿y=%s..%s" % (_ink_red[2], _ink_red[3],
                              _ink_green[2], _ink_green[3]))

# ---- [12] v1.9.0 → v1.9.2 累计修复 ----
# v1.9.0 修复①：事业/感情/出行/财务 卡内文字会被截断，鼠标悬停停留后弹 tooltip 显示完整内容。
# v1.9.0 修复②：未选生肖时下拉框显示「生肖 ⋯」，下拉样式随红/绿主题一致。
# v1.9.1 修订②：未选只显示「生肖」两字（占位文本 + index=-1），悬停留出下拉，弹层滚轴主题化；
#            废弃「生肖 ⋯」占位项与红色箭头块。
# v1.9.2 修订②：收起判定排除 combo 自身几何（首次尝试，坐标系用错未根修）+ 生肖框去留白。
# v1.9.3 修订②：闪烁根修（mapToGlobal 统一坐标系，见 [13] 组）+ 生肖框与八字框等宽 46。
_page_src = inspect.getsource(CalendarPage)
_mv_src = inspect.getsource(CalendarPage.mouseMoveEvent)
_th_src = inspect.getsource(CalendarPage._theme_controls)

rects = page._advice_rects()
ck("[12] 建议卡命中几何方法存在且返回 4 张卡",
   len(rects) == 4 and [k for k, _ in rects] == ["事业", "感情", "出行", "财务"],
   "keys=%s" % [k for k, _ in rects])
# 几何必须与 _paint_advice 完全一致（30,652 起；两列 224+12、两行 54+4）
ck("[12] 建议卡几何与绘制一致（首卡 30,647 / 末卡 262,706，栏间距 5px，v1.9.5）",
   rects[0][1] == QRect(30, 647, 227, 54) and rects[3][1] == QRect(262, 706, 227, 54),
   "rects=%s" % [(k, r.getRect()) for k, r in rects])
# 卡片整体在页内、不与版权行/底部按钮重叠（卡片底 760 < 版权行 762 < TAB 793）
ck("[12] 建议卡全部落在页内且不压底部按钮/页脚",
   all(r.x() >= 0 and r.y() >= 0 and r.bottom() <= page.PAGE_H
       and r.bottom() < CalendarPage.COPYRIGHT_Y for _, r in rects),
   "底=%d" % max(r.bottom() for _, r in rects))
# mouseMoveEvent 必须接住卡片悬停并走 dwell 计时（停留才弹）
ck("[12] 鼠标移动接住建议卡悬停（_advice_rects 命中）",
   "_advice_rects" in _mv_src and "_hover_advice_key" in _mv_src)
ck("[12] 悬停停留后才弹（dwell 计时器启动）",
   "_dwell_timer.start" in _mv_src and "QToolTip.hideText" in _mv_src)
ck("[12] 真正弹出完整建议（showText + info['advice']）",
   inspect.getsource(CalendarPage._show_advice_tip).count("QToolTip.showText") >= 1
   and "info[\"advice\"]" in inspect.getsource(CalendarPage._show_advice_tip))
ck("[12] 卡片悬停给手型光标提示可交互",
   "hit_key is not None" in _mv_src)
ck("[12] 离开控件收起提示并复位状态",
   "QToolTip.hideText" in inspect.getsource(CalendarPage.leaveEvent))
# 修复②：生肖框未选显示「生肖 ⋯」，且 QSS 让下拉随主题红绿
# 修复②（v1.9.1 修订）：未选生肖只显示「生肖」两字（占位文本 + index=-1，列表仅 12 生肖），
# 悬停即弹出下拉，弹层滚轴随主题；此前「生肖 ⋯」占位项与红色箭头块均已废弃。
ck("[12] 未选生肖只显示「生肖」两字（占位文本 + currentIndex=-1）",
   'setPlaceholderText("生肖")' in _page_src and "setCurrentIndex(-1)" in _page_src
   and 'addItem("生肖 ⋯"' not in _page_src,
   "下拉列表仅含 12 生肖（无占位项）")
ck("[12] 悬停弹出下拉（eventFilter Enter→150ms 计时→showPopup）",
   "installEventFilter(self)" in _page_src
   and "QEvent.Enter" in inspect.getsource(CalendarPage.eventFilter)
   and "showPopup" in inspect.getsource(CalendarPage._open_zodiac_popup)
   and "_zx_hover_timer" in _page_src)
ck("[12] 生肖框与八字框等宽 46（列宽一致）",
   page.zodiac_box.width() == 46 and page.btn_bazi.width() == 46,
   "生肖=%d 八字=%d" % (page.zodiac_box.width(), page.btn_bazi.width()))
_ef_src = inspect.getsource(CalendarPage.eventFilter)
ck("[12] 离开收起（Leave→hidePopup，且鼠标不在弹层/combo 自身上时才收）",
   "QEvent.Leave" in _ef_src
   and "hidePopup" in _ef_src
   and "mapToGlobal" in _ef_src
   and "frameGeometry().contains" in _ef_src,
   "v1.9.3 根修：mapToGlobal 统一坐标系（父坐标 contains 全局光标恒 False → 闪烁）")
ck("[12] 弹层滚轴主题化（窄滚轴 + main 色把手 + 隐藏上下按钮）",
   "QScrollBar::handle:vertical" in _th_src
   and "QAbstractItemView::item" in _th_src
   and "QScrollBar::add-line:vertical" in _th_src,
   "把手随 main 红/绿，hover 加深为 dark")
ck("[12] 红色箭头块已移除（drop-down 宽 0 + down-arrow 隐藏）",
   "QComboBox::drop-down{border:none;width:0;}" in _th_src.replace(" ", "")
   and "QComboBox::down-arrow{width:0;height:0;border:none;image:none;}"
   in _th_src.replace(" ", ""),
   "悬停弹出取代箭头按钮")
ck("[12] 生肖下拉样式随主题（tooltip 全局配色含 box_bg/dark/main）",
   "QApplication.instance().setStyleSheet" in _th_src and "QToolTip{" in _th_src
   and "box_bg" in _th_src and "selection-color:#ffffff" in _th_src)
# 弹层 QSS 用 %s 占位、再用主题变量 (box_bg/main/dark) 填充 → 随红/绿切换
ck("[12] 生肖下拉弹层主题化（QAbstractItemView 用 box_bg + main 选中）",
   "QAbstractItemView" in _th_src
   and "selection-background-color:%s" in _th_src
   and "selection-color:#ffffff" in _th_src
   and "background:%s" in _th_src and "color:%s" in _th_src,
   "selection 跟随 main 色（红/绿），文字白")

# ---- [13] v1.9.3：闪烁根修（坐标系统一）+ 八字↔生肖联动 + 本日运势细化 ----
# v1.9.2 的 geometry()（父坐标）contains QCursor.pos()（全局坐标）恒 False → 闪烁未除；
# v1.9.3 用 mapToGlobal 把 combo 矩形映射到全局再比较，伪 Leave 判定才真正成立。
ck("[13] 闪烁根修：收起判定 mapToGlobal 统一坐标系（父坐标≠全局坐标）",
   "mapToGlobal" in _ef_src and "combo_rect.contains" in _ef_src,
   "v1.9.2 用 geometry() 父坐标比全局光标恒 False，是闪烁未修好的根因")
ck("[13] 选完生肖 600ms 内不自动重弹（activated 守卫）",
   "_zx_on_activated" in _page_src
   and "_zx_just_selected" in inspect.getsource(CalendarPage._open_zodiac_popup)
   and "activated.connect" in _page_src)
ck("[13] 八字↔生肖联动：录入后由年支自动选中生肖（含启动回显）",
   "shengxiao" in inspect.getsource(ui_main.MainWindow._sync_zodiac_from_bazi)
   and "findData" in inspect.getsource(ui_main.MainWindow._sync_zodiac_from_bazi)
   and "_sync_zodiac_from_bazi" in inspect.getsource(ui_main.MainWindow._open_bazi)
   and "shengxiao" in inspect.getsource(ui_main.MainWindow.__init__))
ck("[13] 本日生肖细化为本日运势（有八字推演时换标签）",
   "本日运势" in inspect.getsource(CalendarPage._paint_fortune)
   and "bazi_text" in inspect.getsource(CalendarPage._paint_fortune),
   "无八字仍显示「本日生肖」")

# ---- [13b] v1.9.5：生肖统一两字显示（子鼠…亥猪）----
from calendar_app.engine import SHENGXIAO_2CHAR
_TWOCHAR_EXPECT = ["子鼠", "丑牛", "寅虎", "卯兔", "辰龙", "巳蛇",
                   "午马", "未羊", "申猴", "酉鸡", "戌狗", "亥猪"]
ck("[13b] 生肖两字表与用户约定完全一致（子鼠…亥猪）",
   SHENGXIAO_2CHAR == _TWOCHAR_EXPECT, str(SHENGXIAO_2CHAR))
ck("[13b] 下拉框显示两字生肖、data 仍存单字（findData 联动不破）",
   [page.zodiac_box.itemText(i) for i in range(page.zodiac_box.count())]
   == _TWOCHAR_EXPECT
   and [page.zodiac_box.itemData(i) for i in range(page.zodiac_box.count())]
   == ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"])
ck("[13b] 年/日生肖文字经 ANIMAL_TO_2CHAR 转两字",
   "ANIMAL_TO_2CHAR.get(info[\"lunar_year_shengxiao\"]" in inspect.getsource(CalendarPage._paint_header)
   and "ANIMAL_TO_2CHAR.get(info[\"day_shengxiao\"]" in inspect.getsource(CalendarPage._paint_big_day))

# ---- [14] v1.9.4：生肖底图缩到 90% + 配置路径可写兜底（frozen 只读目录） ----
import ui.theme as _uit
_src_wm = inspect.getsource(CalendarPage._paint_zodiac_watermark)
ck("[14] 生肖水印恢复 v1.9.4 底部区块版式（×0.9=189、中线 260、20%，v1.9.6）",
   "base_h = 189" in _src_wm and "260 - w // 2" in _src_wm
   and "setOpacity(0.2)" in _src_wm and "block_top, block_bot = 574, 760" in _src_wm,
   "水印居中压在 吉时/颜色+建议 底部区块（用户 image#6 指认区域）")
ck("[14] 宜/忌中缝叠加 20% 八卦水印（居中 + 加大 110px，绘于文字之下，v1.9.8）",
   "IMG_BAGUA" in inspect.getsource(CalendarPage._paint_yiji)
   and "setOpacity(0.2)" in inspect.getsource(CalendarPage._paint_yiji)
   and "wm_h = 110" in inspect.getsource(CalendarPage._paint_yiji),
   "用户反馈「八卦透明度改到20%」：40%→20%")
_src_sp = inspect.getsource(_uit.settings_path)
ck("[14] 配置路径 frozen 回退 APPDATA（防只读目录无法保存）",
   "APPDATA" in _src_sp and "settings_path" in _src_sp,
   "frozen 下 exe 目录只读时回退到 %APPDATA%/农历日历/settings.json")

# ---- [15] v1.9.7：生肖下拉渲染根修（显式 setFont 取代 QSS 字体）----
# v1.9.6 用 QSS font-family:'Noto Serif SC' 渲染生肖，真机上 Qt 归一化多词族名
# → 匹配不到内置族 → 「生肖整列/选中彻底不显示」（用户 image#1）。v1.9.7 改为
# 与全页自绘文字同一条 setFamilies 路径（内置黑体优先），字号降至 12px 与八字同级。
from calendar_app import fonts as _caf
_zx = page.zodiac_box
_zx_qss = _zx.styleSheet().replace(" ", "")
_zx_le = _zx.lineEdit()
_zx_vw = _zx.view()
ck("[15] 生肖框字号统一 12px（与八字按钮同级，不再 15px 加大）",
   _zx.font().pixelSize() == 12 and _zx_le.font().pixelSize() == 12
   and _zx_vw.font().pixelSize() == 12,
   "combo=%d lineEdit=%d view=%d"
   % (_zx.font().pixelSize(), _zx_le.font().pixelSize(), _zx_vw.font().pixelSize()))
ck("[15] 生肖下拉字体族含内置黑体 Noto Sans SC（setFont 而非 QSS，规避多词族名解析）",
   _caf.SANS_FAMILY in _zx.font().families()
   and _caf.SANS_FAMILY in _zx_le.font().families()
   and _caf.SANS_FAMILY in _zx_vw.font().families(),
   "combo/lineEdit/view 三处均 setFamilies(sans 优先)")
ck("[15] QSS 不再声明字体（font-size/font-family 已移除，改由 setFont 控制）",
   "font-size" not in _zx_qss and "font-family" not in _zx_qss
   and "_apply_zodiac_fonts" in inspect.getsource(CalendarPage._theme_controls),
   "QSS 只管配色/边框，字体走 setFont")
ck("[15] 选中生肖居中（editable+readonly+AlignCenter，沿用 v1.9.6）",
   _zx_le is not None and _zx_le.isReadOnly()
   and bool(_zx_le.alignment() & Qt.AlignHCenter),
   "QComboBox 非可编辑态无法用 QSS 对齐，行编辑居中是 Qt 惯用法")
ck("[15] 下拉列表 item min-height 22px（容纳 12px 字）",
   "min-height:22px" in _zx_qss, "弹层滚轴与选中态仍是主题色（[12] 组保底）")
# v1.9.8 根修：combo 宽 46px → 弹层默认也 46px，扣滚轴+内边距后仅 ~20px，
# 两字生肖(~24px) 被 delegate elide 成「…」。显式撑宽弹层（最宽条目 + 44px）。
ck("[15] 下拉弹层显式撑宽（否则两字生肖被 elide 成「…」，v1.9.8）",
   "setMinimumWidth" in inspect.getsource(CalendarPage._apply_zodiac_fonts)
   and _zx_vw.minimumWidth() >= 60,
   "view 最小宽 = %dpx（combo 宽仅 %dpx）" % (_zx_vw.minimumWidth(), _zx.width()))

# ---- [16] v1.9.9：页高收紧 + 外框绝对下沿（版权行/边框 5px）+ 框外条 793 + 去叠页 ----
_src_ft = inspect.getsource(CalendarPage._paint_footer)
_src_bd = inspect.getsource(CalendarPage._paint_border)
_src_pt = inspect.getsource(CalendarPage.paintEvent)
ck("[16] 版权行 = 出行/财务 建议卡底线(760) 下（COPYRIGHT_Y=762）",
   "self.COPYRIGHT_Y" in _src_ft and CalendarPage.COPYRIGHT_Y == 762,
   "v1.9.7 下移到 781 致离 出行/财务 过远；v1.9.8 起退回 762")
ck("[16] 内框下沿 783 = 版权行框底(778)+5px，外框 789、不再压字",
   CalendarPage.FRAME_IN_BOTTOM == CalendarPage.COPYRIGHT_Y + 16 + 5
   and CalendarPage.FRAME_OUT_BOTTOM == CalendarPage.FRAME_IN_BOTTOM + 6
   and "self.FRAME_OUT_BOTTOM" in _src_bd and "self.FRAME_IN_BOTTOM" in _src_bd
   and "self.PAGE_H - 80" not in _src_bd,
   "用户反馈「版权信息和边框间隔也是 5px 避免重叠」：内框 776→783、外框 782→789")
ck("[16] 底部四按钮距外框线 5px（TAB_Y=796 = 外框 789 + 7）",
   CalendarPage.TAB_Y == CalendarPage.FRAME_OUT_BOTTOM + 7,
   "v1.9.10 用户反馈「四个按钮距离外框改为 5px 间距」：外框 3px 线占 787..790，"
   "TAB_Y-790-1=5 ⇒ 789+7=796（原 793 时仅 2px 空白）")
ck("[16] 页高随之 838→841（提示行 + 本月/本日面板同步下移，页底仍 5px）",
   CalendarPage.PAGE_H == 841
   and CalendarPage.TAB_Y + CalendarPage.TAB_H + 2 + 12 + 5 == CalendarPage.PAGE_H,
   "v1.9.10 按钮下移 3px：提示行与行事历面板同步下移，页底留白不变")
ck("[16] 删除底部「叠页」装饰 _paint_stack（浅灰横带 #eeebe0）",
   not hasattr(CalendarPage, "_paint_stack") and "_paint_stack" not in _src_pt,
   "用户反馈「红框部分好像有一个灰色的框，删除」：满宽 y802..820 横带")

# ---- [17] v1.9.16：八字评分 = 「本命生肖分」锚定 ±10 内的子平法修正 ----
from datetime import timedelta as _td
from calendar_app import engine as _eng
_src_bz = inspect.getsource(_eng.bazi_day_report)
_src_eng = inspect.getsource(_eng)
ck("[17] 旧固定加减式已退役（0.6*f+30+adj / 0.5*f+50 均不再出现），改走子平法底座",
   "* 0.6 + 30 + adj" not in _src_bz and "* 0.5 + 50" not in _src_bz
   and "_BAZI_ADJ" not in _src_eng and "day_master_profile(pillars)" in _src_bz,
   "用户反馈「个人录入后的分数，引入更加专业的计算方式」")
ck("[17] v1.9.15 的虚高基座已退役（常数 64 + (fs-55)*0.55 不再出现），改锚定生肖分",
   "64.0 + ys" not in _src_bz and "(info[\"fortune_score\"] - 55.0)" not in _src_bz
   and "refine_baseline(pillars, prof)" in _src_bz
   and "analyze_zodiac_day(info, y_sx)" in _src_bz,
   "用户反馈「分数普遍偏高」：基座把中位抬到 70，现锚定生肖分后回归中性")
ck("[17] 子平法底座齐备：地支藏干加权 + 旺相休囚死 + 十神 + 扶抑取用神",
   all(k in _src_eng for k in ("ZHI_CANGGAN", "GAN_YINYANG", "WANG_STAGE_TABLE",
                               "WANG_STAGE_SCORE", "def shishen(",
                               "def day_master_profile(", "def wang_stage(")),
   "月支权重 3.0（得令）/ 日支 2.0（得地）")
ck("[17] 十神推断正确（日主丙火：甲偏印 丁劫财 戊食神 己伤官 庚偏财 辛正财 壬七杀 癸正官）",
   [_eng.shishen("丙", g) for g in "甲丁戊己庚辛壬癸"]
   == ["偏印", "劫财", "食神", "伤官", "偏财", "正财", "七杀", "正官"])
_bz = _eng.compute_eightchar(1994, 3, 21, 13)
_pf = _eng.day_master_profile(_bz["pillars"])
ck("[17] 用户样本（甲戌·丁卯·丙午·乙未）判「身强」，喜克泄耗（水土金）/ 忌印比（木火）",
   _pf["strong"] and set(_pf["xi"]) == {"水", "土", "金"}
   and set(_pf["ji"]) == {"木", "火"},
   "日主%s ratio=%.3f（印重比助）" % (_pf["ri_gan"], _pf["ratio"]))
_bs = sorted(_eng.bazi_day_report(_bz, get_day_info(date(2026, 1, 1) + _td(days=i)))["score"]
             for i in range(0, 365, 7))
ck("[17] 抽样全年得分中位落在 55~70（回归中性）、分数恒在 5..98",
   55 <= _bs[len(_bs) // 2] <= 70 and 5 <= _bs[0] and _bs[-1] <= 98,
   "中位=%d 范围=%d..%d" % (_bs[len(_bs) // 2], _bs[0], _bs[-1]))
# 个性化硬指标：同一天不同八字应给出明显不同的分数（旧式「换个八字分布一样」做不到）
_bzs = [_eng.compute_eightchar(*a) for a in
        ((1994, 3, 21, 13), (1975, 12, 30, 22), (2001, 6, 15, 5))]
_infos = [get_day_info(date(2026, 1, 1) + _td(days=i)) for i in range(0, 365, 7)]
_seq = [[_eng.bazi_day_report(b, inf)["score"] for inf in _infos] for b in _bzs]
_spread = sum(max(c) - min(c) for c in zip(*_seq)) / float(len(_infos))
ck("[17] 同日不同八字平均分差 ≥ 12、且三条序列互不相同（评分真正因人而异）",
   _spread >= 12 and len({tuple(s) for s in _seq}) == len(_seq),
   "平均分差 %.1f" % _spread)
# ★ v1.9.16 用户口径：个人分恒在「本命生肖分」±10 内，且年均偏离 ≈ 0（整体中性）
_dev = []
for _b in _bzs:
    _sx = _b["shengxiao"]
    for _inf in _infos:
        _dev.append(_eng.bazi_day_report(_b, _inf)["score"]
                    - _eng.analyze_zodiac_day(_inf, _sx)["score"])
ck("[17] ⭐ 个人分恒在「本命生肖分」±10 以内（用户口径）",
   all(abs(d) <= 10 for d in _dev),
   "越界 %d / %d，极值 %d..%d" % (sum(1 for d in _dev if abs(d) > 10),
                                  len(_dev), min(_dev), max(_dev)))
ck("[17] ⭐ 个人分与生肖分年均偏离 ≈ 0（整体中性，不再普遍偏高）",
   abs(sum(_dev) / len(_dev)) <= 1.5,
   "平均偏离 %+.2f" % (sum(_dev) / len(_dev)))
ck("[17] refine_baseline 已剪掉干支关系的结构性正偏（各命盘期望 > 0）",
   all(_eng.refine_baseline(_b["pillars"], _eng.day_master_profile(_b["pillars"])) > 0
       for _b in _bzs),
   "不修则每张命盘白拿 2~3 分")

# ---- [18] v1.9.10：八字推行加粗 + 文案英文汉译 + 宜/忌居中 ----
_src_zx = inspect.getsource(CalendarPage._paint_zodiac)
ck("[18] 八字推演行加粗（_font(12, ZH_SONG, QFont.Bold)）",
   "_font(12, ZH_SONG, QFont.Bold)" in _src_zx,
   "用户反馈「八字推演 字体加粗」")
_src_dp = inspect.getsource(CalendarPage._draw_para)
_src_yj = inspect.getsource(CalendarPage._paint_yiji)
ck("[18] 宜/忌内容水平居中（_draw_para 走 Qt.AlignHCenter，且仅宜/忌调用）",
   "Qt.AlignHCenter" in _src_dp and "_draw_para" in _src_yj,
   "用户反馈「宜 和 忌 的内容保持居中」")
import re as _re18
_en18 = []
for _sx18 in ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]:
    for _t18 in _eng.analyze_zodiac_day(get_day_info(date(2026, 9, 30)), _sx18)["tips"]:
        if _re18.search(r"[A-Za-z]{3,}", _t18):
            _en18.append((_sx18, _t18))
ck("[18] 生肖文案无英文残留（friction → 摩擦）",
   not _en18, "含英文: %s" % _en18[:3])

# ---- [19] v1.9.11：宜/忌跨行居中错位（行尾顿号）修复 + 软件 logo 更新 ----
_src_wp = inspect.getsource(CalendarPage._wrap_px)
ck("[19] _wrap_px 抹去换行点行尾顿号（修复跨行居中错位）",
   'ln.endswith("、")' in _src_wp and "ln[:-1]" in _src_wp,
   "用户反馈「因为最后一个、导致第二行与第一行错位」")
_wl19 = CalendarPage._wrap_px(_fm_demi, "会亲友、出行、安床、祭祀、祈福、安葬", 92)
ck("[19] 断行结果无任何行以「、」结尾（各行墨迹可精确居中）",
   len(_wl19) >= 2 and all(not ln.endswith("、") for ln in _wl19), str(_wl19))
# 反向验证：若保留行尾顿号，则该行墨迹中点会左偏（此处量化偏差以证明修法有效）
_ln_sep = [ln + "、" for ln in _wl19]          # 模拟未抹除的旧行为
_dev19 = []
for _ln in _ln_sep:
    _w_ink = _fm_demi.horizontalAdvance(_ln.rstrip("、"))
    _w_full = _fm_demi.horizontalAdvance(_ln)
    _dev19.append((_w_full - _w_ink) / 2.0)     # 居中时墨迹左偏量
ck("[19] 旧行为确有左偏、新行为已消除（量化验证）",
   max(_dev19) > 3 and all(_fm_demi.horizontalAdvance(ln) > 0 for ln in _wl19),
   "旧左偏最大 %.1fpx / 新偏差 0px" % max(_dev19))
ck("[19] logo.png 已替换为新版（1.03MB，旧版 32KB）",
   os.path.getsize(IMG_LOGO) > 500000,
   "logo.png = %d B" % os.path.getsize(IMG_LOGO))
_ico19 = os.path.join(os.path.dirname(IMG_LOGO), "logo.ico")
ck("[19] logo.ico 已按新版重生成（多尺寸，含 256²）",
   os.path.exists(_ico19) and os.path.getsize(_ico19) > 100000,
   "logo.ico = %d B" % (os.path.getsize(_ico19) if os.path.exists(_ico19) else -1))

# ---- [20] v1.9.12：宜/忌分隔虚线改到「分数区」与「八字推演行」之间的居中 ----
_src_zx2 = inspect.getsource(CalendarPage._paint_zodiac)
ck("[20] 虚线移到「分数区」与「八字推演行」之间居中（line_y = y + 2 → 行 541..542）",
   "line_y = y + 2" in _src_zx2 and "drawLine(30, line_y" in _src_zx2,
   "用户反馈「虚线放在 分数 和 八字推演 居中位置」：行 536..537 → 541..542")

# ---- [21] v1.9.14：任务栏图标「有 / 无」两态切换（悬浮窗交互规格） ----
# 用户确认的规格：启动有图标 / 最小化只摘图标但窗口留在桌面 / 关闭全消失驻留托盘 /
#   托盘左键唤起不带图标 / 托盘右键「显示/隐藏」唤起带图标。
_src_ui = inspect.getsource(ui_main)
_src_ex = inspect.getsource(MainWindow._write_exstyle)
_src_sync = inspect.getsource(MainWindow._sync_taskbar_tab)
_src_st = inspect.getsource(MainWindow._set_taskbar)
ck("[21] _write_exstyle 两态：有→置 WS_EX_APPWINDOW 清 TOOLWINDOW",
   "WS_EX_APPWINDOW = 0x00040000" in _src_ex and "WS_EX_TOOLWINDOW = 0x00000080" in _src_ex
   and "| WS_EX_APPWINDOW) & ~WS_EX_TOOLWINDOW" in _src_ex)
ck("[21] _write_exstyle 无图标态：置 WS_EX_TOOLWINDOW 清 APPWINDOW",
   "| WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW" in _src_ex)
ck("[21] ITaskbarList 即时增删 AddTab(4)/DeleteTab(5) + COM 兜底 hide/show",
   "_taskbar_call(4 if self._taskbar_mode else 5, hwnd)" in _src_sync
   and "self.hide()" in _src_sync)
ck("[21] ⭐ showEvent 显示后**延一拍**显式增删按钮（修「托盘右键唤起仍无任务栏图标」）",
   "QTimer.singleShot(0, lambda: self._sync_taskbar_tab(fallback=False))"
   in inspect.getsource(MainWindow.showEvent),
   "只改扩展样式位不足以让 shell 把按钮加回来 → 必须显式 AddTab")
ck("[21] 可见态切换（_set_taskbar resync）走 _sync_taskbar_tab(fallback=True)",
   "_sync_taskbar_tab(fallback=True)" in _src_st)
ck("[21] _set_taskbar 记入 self._taskbar_mode（供 showEvent 自愈）",
   "self._taskbar_mode = bool(taskbar)" in _src_st)
_src_minf = inspect.getsource(MainWindow._minimize_to_float)
ck("[21] 「最小化」= 只摘任务栏图标、窗口留在桌面（不调 showMinimized）",
   "_set_taskbar(False, resync=True)" in _src_minf
   and "self.showMinimized(" not in _src_minf,
   "用户规格：最小化后任务栏图标不存在、桌面界面保持存在")
ck("[21] btn_min 已改接 _minimize_to_float（不再走真最小化）",
   "btn_min.clicked.connect(self._minimize_to_float)"
   in inspect.getsource(MainWindow.__init__)
   and "def showMinimized" not in inspect.getsource(ui_main),
   "已删除 v1.9.13 的 showMinimized 覆写（QWidget 自带的 showMinimized 不再被改写）")
_src_tg = inspect.getsource(MainWindow._toggle_visible)
ck("[21] 托盘右键「显示/隐藏」唤起时带任务栏图标",
   "_show_window(taskbar=True)" in _src_tg)
_src_ta = inspect.getsource(MainWindow._on_tray_activated)
ck("[21] 托盘左键唤起时不带任务栏图标",
   "_show_window(taskbar=False)" in _src_ta)
_src_sw = inspect.getsource(MainWindow._show_window)
ck("[21] _show_window 先定样式位再 show（shell 才会按新位建按钮）",
   "_set_taskbar(taskbar)" in _src_sw and "showNormal()" in _src_sw)
_src_ce = inspect.getsource(MainWindow.closeEvent)
ck("[21] 关闭：切无图标态 + hide（桌面与任务栏都消失，驻留托盘）",
   "_set_taskbar(False, resync=True)" in _src_ce and "self.hide()" in _src_ce)
ck("[21] 启动默认有任务栏图标（_taskbar_mode 初值 True）",
   "self._taskbar_mode = True" in inspect.getsource(MainWindow.__init__))
ck("[21] ITaskbarList 即时增删接口在位（CLSID/IID + AddTab/DeleteTab）",
   "56FDF344" in _src_ui and "56FDF342" in _src_ui
   and "def _taskbar_call(" in _src_ui and "def _guid(" in _src_ui)
ck("[21] 真机探针 window_mode_probe.py 存在（任务栏两态实测）",
   os.path.exists(os.path.join(_ROOT, "tools", "dev_checks",
                               "window_mode_probe.py")))

failed = [n for n, c, _ in R if not c]
print("\n==== UI 复核 (v%s) ==== total=%d passed=%d failed=%d"
      % (APP_VERSION, len(R), sum(1 for _, c, _ in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
app.quit()
sys.exit(1 if failed else 0)
