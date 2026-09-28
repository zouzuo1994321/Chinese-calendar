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
   APP_VERSION == "1.8.1" and BUILD_CODE == "2609280022", VERSION_TITLE)
ck("回归 生肖水印素材齐备",
   all(os.path.exists(os.path.join(_ZODIAC_DIR, "%s（%s）.png" % (s, t)))
       for s in ("龙", "马") for t in ("红", "绿")))
ck("回归 页面尺寸 520x848", (page.PAGE_W, page.PAGE_H) == (520, 848))
from calendar_app import fonts as _fonts
from ui_main import ZH_FONT as _zhf
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
from ui.theme import _font as _tf
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
