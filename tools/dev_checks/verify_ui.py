# -*- coding: utf-8 -*-
"""源码态综合复核：覆盖本次需求 + 性能 + 回归（版本号随 version.py 迭代）。"""
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from datetime import date
from PIL import Image
from PySide6.QtCore import QRect
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
           (14, page.PAGE_H - 46), (page.PAGE_W - 14, page.PAGE_H - 46)]
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
   _paper_pixmap(520, 848) is _paper_pixmap(520, 848))

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
    setup(d)
    page._sheen_t = t
    page.update()
    app.processEvents()
    img = page.grab().toImage()
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
   APP_VERSION == "1.8.6" and BUILD_CODE == "2609280027", VERSION_TITLE)
ck("回归 生肖水印素材齐备",
   all(os.path.exists(os.path.join(_ZODIAC_DIR, "%s（%s）.png" % (s, t)))
       for s in ("龙", "马") for t in ("红", "绿")))
ck("回归 页面尺寸 520x848", (page.PAGE_W, page.PAGE_H) == (520, 848))
from calendar_app import fonts as _fonts
from ui_main import ZH_FONT as _zhf, EN_FONT as _enf
ck("回归 内置字体已注册", _fonts.SERIF_FAMILY in _fonts.install_fonts(),
   _fonts.report())
ck("回归 ZH_FONT 首位为内置宋体", _zhf and _zhf[0] == _fonts.SERIF_FAMILY,
   str(_zhf[:2]))

# ---- [6] 中栏「喜神/财神/福神/冲煞/X命互禄」：五行必须全部显示完整 ----
# 背景：内置 Noto Serif SC 默认行距 1.42em（14px → 20px），五行需 100px，
# 而中栏可用高仅 86px → 旧写法用 "\n".join 会整行裁掉第 5 行（v1.8.0 后暴露）。
MID_X, MID_Y, MID_W, MID_H = 184, 387, 152, 90     # = QRect(184, y+3, 152, h-6)
MID_STEP = MID_H / 5.0


def _mid_ink(img, y0, y1):
    """统计中栏文字区内的「深墨」像素（阈值 120 可滤掉 40% 的八卦水印）。"""
    n = 0
    for yy in range(int(y0), int(y1)):
        for xx in range(MID_X, MID_X + MID_W):
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
    per = [_mid_ink(img, MID_Y + i * MID_STEP, MID_Y + (i + 1) * MID_STEP)
           for i in range(5)]
    below = _mid_ink(img, MID_Y + MID_H, MID_Y + MID_H + 4)   # 方框之外
    return per, below


for d, tag in ((RED, "红日"), (GREEN, "绿日")):
    per, below = mid_rows(d)
    ck("[6] 中栏五行全部有字 · %s" % tag, all(v > 40 for v in per),
       "各槽像素=%s" % per)
    ck("[6] 中栏文字未溢出到方框之外 · %s" % tag, below == 0,
       "越界像素=%d" % below)

_src_mid = inspect.getsource(CalendarPage._paint_yiji)
ck("[6] 中栏改逐行等分绘制（不再依赖字体行距）",
   "_draw_rows(p, rows" in _src_mid and '"\\n".join(rows)' not in _src_mid)
ck("[6] 八卦水印透明度已调至 40%",
   "setOpacity(0.4)" in _src_mid and "IMG_BAGUA" in _src_mid)

from PySide6.QtGui import QFontMetricsF
from ui.theme import _font as _tf, SHEAR as _SHEAR
_fm14 = QFontMetricsF(_tf(14, _zhf))
_worst = ("", 0.0)


def _scan_widest():
    from datetime import timedelta
    global _worst
    for i in range(1096):                      # 2026-01-01 起三年逐日
        info = get_day_info(date(2026, 1, 1) + timedelta(days=i))
        for r in ("喜神 %s" % info["pos_xi"], "财神 %s" % info["pos_cai"],
                  "福神 %s" % info["pos_fu"], "冲煞 %s" % info["chong"],
                  "%s" % info["lu"]):
            w = _fm14.horizontalAdvance(r)
            if w > _worst[1]:
                _worst = (r, w)
    return _worst


_scan_widest()
ck("[6] 三年内最宽一行仍可容于中栏", _worst[1] <= MID_W,
   "%r = %.1fpx / 可用 %dpx" % (_worst[0], _worst[1], MID_W))

# ---- [7] 宜 / 忌 文本块：内置字体行距 20px，三行需 60px，旧文字区仅 48px ----
# 2026-01-06 宜「会亲友」第三行被裁（v1.8.1 修复）。此处锁定「最多三行 + 三行全可见」。
YIJI_X, YIJI_Y, YIJI_W, YIJI_H, YIJI_MAX = 38, 424, 140, 54, 3
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
    for x0, key in ((YIJI_X, "yi"), (YIJI_X + 310, "ji")):
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
   "_draw_para(p," in _src_yi and "TextWordWrap" not in _src_yi)
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
    setup(d)
    page._sheen_t = t
    page.update()
    app.processEvents()
    page.grab().save(path)
    return Image.open(path).size


print("预览:", shot(RED, 0.34, "docs/screenshots/screenshot-red.png"),
      shot(GREEN, 0.34, "docs/screenshots/screenshot-green.png"))
page.info = get_day_info(RED)
page.P = palette_for(page.info)
page._sheen_t = 0.30
page.update()
app.processEvents()
win.grab().save("docs/screenshots/screenshot-window.png")
print("预览: docs/screenshots/screenshot-window.png", Image.open("docs/screenshots/screenshot-window.png").size)

setup(RED)
CROP = QRect(50, 96, 420, 214)
tiles = []
_tmp = "_sheen_tmp.png"
try:
    for t in (0.00, 0.14, 0.28, 0.42, 0.56, 0.70, 0.84, 0.97):
        page._sheen_t = t
        page.update()
        app.processEvents()
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

failed = [n for n, c, _ in R if not c]
print("\n==== UI 复核 (v%s) ==== total=%d passed=%d failed=%d"
      % (APP_VERSION, len(R), sum(1 for _, c, _ in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
app.quit()
sys.exit(1 if failed else 0)
