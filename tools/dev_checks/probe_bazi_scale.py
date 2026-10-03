# -*- coding: utf-8 -*-
"""个人八字分 · 口径归因（v1.9.16）。

v1.9.16 口径：**个人分 = 本命生肖分 + 个人化修正**，修正 = 用神五行契合 + 逐柱
干支关系（剪掉 60 甲子结构偏置）经 tanh 压到 ±10。本探针拆解各分项均值，并给出
与生肖分的偏离分布，用于后续调参时快速看「有没有偏、偏在哪」。

背景（v1.9.15 曾出问题）：旧口径 = 常数 64 + 通书基座 (fs-55)*0.55 + 干支项，
三项叠加后中位虚高到 70（通书分中位仅 60），整体上移一整档。新口径已修正。
"""
import os
import sys
import statistics
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from calendar_app import engine as E          # noqa: E402

DAYS = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
INFOS = [E.get_day_info(d) for d in DAYS]

SAMPLES = [
    ("1994-03-21 13时", E.compute_eightchar(1994, 3, 21, 13)),
    ("1988-08-08 08时", E.compute_eightchar(1988, 8, 8, 8)),
    ("2000-01-01 00时", E.compute_eightchar(2000, 1, 1, 0)),
    ("1975-12-31 22时", E.compute_eightchar(1975, 12, 31, 22)),
    ("2010-06-15 06时", E.compute_eightchar(2010, 6, 15, 6)),
]

print("=" * 78)
print("① 结构偏置修补：个人化修正项的 60 甲子期望（越接近 0 越中性）")
print("   %-16s %-8s %10s %10s" % ("样本", "本命生肖", "修正项期望", "身强/身弱"))
for label, bz in SAMPLES:
    prof = E.day_master_profile(bz["pillars"])
    base = E.refine_baseline(bz["pillars"], prof)
    print("   %-16s %-8s %10.3f %10s"
          % (label, bz["shengxiao"], base, "身强" if prof["strong"] else "身弱"))
print("   （此值即从原始修正项中减掉的量；不修则每张命盘白拿 2~3 分）")

print("-" * 78)
print("② 个人分 vs 本命生肖分：偏离分布（规格：|偏离| ≤ 10，年均 ≈ 0）")
print("   %-16s %6s %6s %6s %7s %7s" % ("样本", "个人中位", "生肖中位", "均值偏", "极值偏", "越界"))
all_dev = []
for label, bz in SAMPLES:
    sx = bz["shengxiao"]
    ps = [E.bazi_day_report(bz, inf)["score"] for inf in INFOS]
    anc = [E.analyze_zodiac_day(inf, sx)["score"] for inf in INFOS]
    dev = [p - a for p, a in zip(ps, anc)]
    all_dev += dev
    print("   %-16s %6.0f %6.0f %+6.2f %7s %7d"
          % (label, statistics.median(ps), statistics.median(anc),
             statistics.mean(dev), "%d..%d" % (min(dev), max(dev)),
             sum(1 for d in dev if abs(d) > 10)))

print("-" * 78)
print("③ 合成池（N=%d）整体统计" % len(all_dev))
ps_all = []
for _, bz in SAMPLES:
    ps_all += [E.bazi_day_report(bz, inf)["score"] for inf in INFOS]
fs_all = [i["fortune_score"] for i in INFOS]
print("   个人分：均值 %.1f  中位 %.0f  min %d  max %d"
      % (statistics.mean(ps_all), statistics.median(ps_all), min(ps_all), max(ps_all)))
print("   通书分：均值 %.1f  中位 %.0f" % (statistics.mean(fs_all), statistics.median(fs_all)))
print("   与生肖分偏离：均值 %+.2f  中位 %+.0f  越界 %d/%d"
      % (statistics.mean(all_dev), statistics.median(all_dev),
         sum(1 for d in all_dev if abs(d) > 10), len(all_dev)))

names = ["<50", "50-59", "60-69", "70-79", "80+"]


def bands(vals):
    edges = [(-1, 49), (50, 59), (60, 69), (70, 79), (80, 999)]
    return [100.0 * sum(1 for v in vals if lo <= v <= hi) / len(vals) for lo, hi in edges]


print("   %-12s %7s %7s %7s %7s %7s" % ("口径", *names))
print("   %-12s %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%%" % ("个人八字分", *bands(ps_all)))
print("   %-12s %6.1f%% %6.1f%% %6.1f%% %6.1f%% %6.1f%%" % ("通书生吉分", *bands(fs_all)))
print("=" * 78)
