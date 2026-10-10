# -*- coding: utf-8 -*-
"""单行缩排自适应探针（v1.9.19 起，v1.9.20 扩充）—— 分数区「本日运势 / 值神」两行行为验证。

背景（用户反馈）：
  · 「本日运势 保持整体居中显示」
  · 「值神还是不用分两行了，保持一行显示，如果太长显示不全则自动缩小字体间隔」
  · 「本日运势 正常情况下 左侧留白太多」（v1.9.20：改为紧跟分数之后）

本探针只验**行为与度量**（不依赖 MainWindow，跑得快），校验：
  1. `_fit_size` 的搜索确实命中「视觉密度代价最小」的可行档（穷举对照）；
  2. 366 天值神行**天天**排得进一行，且选定档位实测不溢出；
  3. 缩排克制：多数日子保持 12px，且不会一路缩到不可读；
  4. 本日运势行各种文案口径（未录入 / 八字 / 长 tag）在 1/2/3 位分数下都能整条放下；
  5. 极端超长文本仍能优雅退化（返回 None → 调用方 elide）；
  6. 结果缓存有效（同一输入第二次不再重算）、确定性（同输入同输出）；
  7. `_draw_fit_line` 实际绘制后墨迹不越出给定矩形。

运行：
  "C:/Users/zouzu/.workbuddy/binaries/python/envs/default/Scripts/python.exe" \
      tools/dev_checks/probe_fit.py
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRect                                    # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication                          # noqa: E402

app = QApplication(sys.argv)

from calendar_app.engine import get_day_info                         # noqa: E402
from ui.theme import _font, use_builtin_fonts, NUM_FONT              # noqa: E402
use_builtin_fonts()
from ui.page import CalendarPage                                     # noqa: E402
from ui_main import ZH_FONT                                          # noqa: E402

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond)))
    print("%s %s%s" % ("PASS" if cond else "FAIL", name,
                       ("  ← %s" % detail) if detail else ""))


TX0, TXW = 94, CalendarPage.GUA_RECT.left() - 8 - 94
ZX0, ZXW = 182, CalendarPage.GUA_RECT.left() - 8 - 182
SPACINGS = [round(-0.2 * i, 1) for i in range(0, 7)]        # 0 … -1.2


def adv(size, spacing, text):
    f = _font(size, ZH_FONT)
    if spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return QFontMetricsF(f).horizontalAdvance(text)


def cost(size, spacing, base):
    return (base - size) + 2.0 * abs(spacing)


def brute_best(text, width, base, floor):
    """穷举所有可行档，返回代价最小的 (字号, 字距)；无解 None。"""
    best = None
    for size in range(floor, base + 1):
        for sp in SPACINGS:
            if adv(size, sp, text) <= width:
                key = (cost(size, sp, base), -size, -sp)
                if best is None or key < best[0]:
                    best = (key, (size, sp))
    return best[1] if best else None


ck("页面可用宽为正（值神 %dpx / 本日运势保底 %dpx，后者为更严的下限）"
   % (TXW, ZXW), TXW > 200 and ZXW > 150)

# ① 366 天全量
tails, bad_none, bad_over, hist = [], 0, [], {}
for i in range(366):
    inf = get_day_info(date(2026, 1, 1) + timedelta(days=i))
    t = "值神%s·%s｜吉神%d 凶煞%d ｜ %s" % (
        inf["tianshen_type"], inf["tianshen"], len(inf["jishen"]),
        len(inf["xiongsha"]), inf["fortune_tip"])
    tails.append((inf["date"], t))
    fit = CalendarPage._fit_size(t, TXW, 12, ZH_FONT)
    if fit is None:
        bad_none += 1
        continue
    if adv(fit[0], fit[1], t) > TXW:
        bad_over.append((inf["date"], t, fit, adv(fit[0], fit[1], t)))
    hist[fit[0]] = hist.get(fit[0], 0) + 1

ck("366 天值神行全部求得出缩排档（无一天回退省略号）", bad_none == 0,
   "无解 %d 天" % bad_none)
ck("缩排后实测宽度均不超过可用宽（不溢出）", not bad_over,
   "溢出 %d 天 %s" % (len(bad_over), bad_over[:2]))
ck("缩排克制：≥200 天保持 12px 原号", hist.get(12, 0) >= 200,
   "字号分布 %s" % dict(sorted(hist.items(), reverse=True)))
ck("缩排克制：无一天缩到 10px 以下（下限 %d）" % CalendarPage.FIT_MIN_SIZE,
   min(hist) >= max(10, CalendarPage.FIT_MIN_SIZE))
w12 = [(d, adv(12, 0.0, t)) for d, t in tails]
w12.sort(key=lambda p: -p[1])
ck("原始 12px 下确有大量日子超宽（缩排不是摆设）",
   sum(1 for _, w in w12 if w > TXW) >= 50,
   "超宽 %d 天；最宽 %s %.0fpx" % (sum(1 for _, w in w12 if w > TXW),
                                   w12[0][0], w12[0][1]))

# ② 穷举对照：搜索顺序必须等价于「代价最小」
mis = []
for d, t in tails:
    fit = CalendarPage._fit_size(t, TXW, 12, ZH_FONT)
    want = brute_best(t, TXW, 12, max(12 - CalendarPage.FIT_FLOOR_GAP,
                                      CalendarPage.FIT_MIN_SIZE))
    if (fit or None) != (want or None):
        mis.append((d, fit, want))
ck("缩排档位与穷举「最小视觉密度代价」完全一致（366 天）", not mis,
   "不一致 %d 天 %s" % (len(mis), mis[:2]))

# ③ 本日运势行各口径
# v1.9.20 起该行**紧跟分数之后**：可用宽 = 卦象框左缘 − 8 − (94 + 分数实际宽 + 12)，
# 随分数位数浮动（一位 ~283px / 两位 ~267px / 三位 ~257px）。
z_cases = {
    "未录入生肖": "在页顶选择你的生肖，查看本日运势 →",
    "八字口径（截图同款）": "本日运势 戊狗：值日 · 三合火局（81分）",
    "八字口径（满分）": "本日运势 子鼠：当值 · 六合木局（100分）",
    "生肖口径（长 tag）": "本日生肖 亥猪：三合 · 天德 · 月德 · 驿马（88分）",
    "生肖口径（短）": "本日生肖 辰龙：六合（95分）",
}


def zod_x(score):
    """复算 v1.9.20 的「本日运势」行左起点（与 _paint_fortune 同式）。"""
    f = _font(22, NUM_FONT, QFont.Black)
    return 94 + int(QFontMetricsF(f).horizontalAdvance("%d 分" % score)) + 12


_zod_w = {s: CalendarPage.GUA_RECT.left() - 8 - zod_x(s) for s in (5, 54, 80, 100)}
ck("本日运势行可用宽随分数位数浮动且都 >240px（一位 %d / 三位 %d）"
   % (_zod_w[5], _zod_w[100]),
   all(w > 240 for w in _zod_w.values()) and _zod_w[5] > _zod_w[100])
z_bad = {}
for sc, w in _zod_w.items():
    for name, txt in z_cases.items():
        if CalendarPage._fit_size(txt, w, 14, ZH_FONT, QFont.Black) is None:
            z_bad["%s@%d分" % (name, sc)] = w
ck("1/2/3 位分数下 5 种文案口径都能整条放下（共 %d 组合）"
   % (len(z_cases) * len(_zod_w)), not z_bad,
   "无解：%s" % list(z_bad) if z_bad else
   "；".join("%s→%dpx" % (k, CalendarPage._fit_size(
       v, _zod_w[54], 14, ZH_FONT, QFont.Black)[0]) for k, v in z_cases.items()))

# ④ 极端退化
huge = "本日运势 某生肖：" + "、".join("某事应宜忌%d" % i for i in range(30)) + "（99分）"
ck("极端超长文案返回 None（调用方回退 elide，绝不溢出）",
   CalendarPage._fit_size(huge, ZXW, 14, ZH_FONT, QFont.Black) is None,
   "len=%d（按更窄的 %dpx 测，比实际可用宽更严）" % (len(huge), ZXW))

# ⑤ 缓存与确定性
CalendarPage.FIT_CACHE.clear()
t0 = tails[0][1]
r1 = CalendarPage._fit_size(t0, TXW, 12, ZH_FONT)
n1 = len(CalendarPage.FIT_CACHE)
r2 = CalendarPage._fit_size(t0, TXW, 12, ZH_FONT)
n2 = len(CalendarPage.FIT_CACHE)
ck("结果缓存生效（第二次调用不新增条目）且结果一致",
   r1 == r2 and n1 == 1 and n2 == 1, "cache %d → %d，结果 %s" % (n1, n2, r1))
ck("确定性：清缓存重算结果不变",
   (lambda: (CalendarPage.FIT_CACHE.clear(),
             CalendarPage._fit_size(t0, TXW, 12, ZH_FONT) == r1)[1])())

# ⑥ 字距真的紧致（-1.2px 必须比 0 窄）
w0 = adv(11, 0.0, t0)
w1 = adv(11, -1.2, t0)
ck("收紧字距确实变窄（QFontMetricsF 计入 AbsoluteSpacing）",
   w1 < w0 - 5, "11px 下 %.1f → %.1f（差 %.1f）" % (w0, w1, w0 - w1))

# ⑦ 真实绘制：墨迹不越出矩形
img = QImage(520, 40, QImage.Format_ARGB32)
img.fill(QColor("#ffffff"))
p = QPainter(img)
CalendarPage._draw_fit_line(CalendarPage, p, tails[0][1],
                            QRect(TX0, 0, TXW, 40), 12, ZH_FONT)
p.end()
xmin, xmax = 9999, -1
for yy in range(40):
    for xx in range(520):
        if img.pixelColor(xx, yy).lightness() < 140:
            xmin, xmax = min(xmin, xx), max(xmax, xx)
ck("_draw_fit_line 在 QImage 上实测墨迹不越出矩形",
   xmax <= TX0 + TXW and xmin >= TX0 - 2,
   "墨迹 %d..%d，矩形 %d..%d" % (xmin, xmax, TX0, TX0 + TXW))

failed = [n for n, c in R if not c]
print("\n==== 缩排自适应探针 (v1.9.20) ==== total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, c in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
