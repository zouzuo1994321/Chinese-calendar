# -*- coding: utf-8 -*-
"""八字「子平法专业评分」实测（v1.9.16）。

校验：
  ① 十神推断（比肩/劫财/食神/伤官/正财/偏财/正官/七杀/正印/偏印）全对；
  ② 用户样本 1994-03-21 13:00 → 甲戌·丁卯·丙午·乙未，日主丙火判「身强」、
     喜用含 水/土/金（克泄耗）、忌 木/火（生扶）；
  ③ 分数**真正随出生数据变化**：多个不同八字各自的中位/均值/极值不同，
     且中位落在中性区间（不再人人 70+）。
  ④ v1.9.16 口径：**个人分恒在「本命生肖分」±10 以内，且年均偏离 ≈ 0**。
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from calendar_app import engine as E          # noqa: E402
from calendar_app.engine import get_day_info  # noqa: E402

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


# ---------- ① 十神 ----------
_base = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
_ss = {g: E.shishen("丙", g) for g in _base}      # 日主 丙（阳火）
_expect = {"甲": "偏印", "乙": "正印", "丙": "比肩", "丁": "劫财", "戊": "食神",
           "己": "伤官", "庚": "偏财", "辛": "正财", "壬": "七杀", "癸": "正官"}
ck("① 十神推断全部正确（日主丙火对十天干）", _ss == _expect, str(_ss))

# ---------- ② 用户样本 ----------
bz = E.compute_eightchar(1994, 3, 21, 13)
ck("② 四柱 = 甲戌 · 丁卯 · 丙午 · 乙未",
   bz["pillars"] == ["甲戌", "丁卯", "丙午", "乙未"] and bz["shengxiao"] == "狗",
   "%s / 生肖 %s" % (bz["pillars"], bz["shengxiao"]))
prof = E.day_master_profile(bz["pillars"])
ck("② 日主丙火判「身强」（印重比助，ratio>0.5）",
   prof["strong"] and prof["ratio"] > 0.5,
   "ratio=%.3f 五行力量=%s" % (prof["ratio"],
                               {k: round(v, 2) for k, v in prof["power"].items()}))
ck("② 身强 → 喜克泄耗（官杀水 / 食伤土 / 财金）、忌印比（木 / 火）",
   set(prof["xi"]) == {"水", "土", "金"} and set(prof["ji"]) == {"木", "火"},
   "喜=%s 忌=%s" % ("".join(prof["xi"]), "".join(prof["ji"])))

_d = date(2026, 9, 28)
_rep = E.bazi_day_report(bz, get_day_info(_d))
ck("② 报告含 profile 且 text 带「身强 / 十神」信息",
   isinstance(_rep, dict) and _rep.get("profile") and "身强" in _rep["text"]
   and "日主丙午" in _rep["text"],
   "%s（%d分）" % (_rep["text"], _rep["score"]))

# ---------- ③ 分布随出生数据变化 ----------
SAMPLES = [(1994, 3, 21, 13), (1988, 7, 4, 9), (1975, 12, 30, 22),
           (2001, 6, 15, 5), (1963, 1, 8, 17), (1999, 10, 2, 11)]
DAYS = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
INFOS = [get_day_info(d) for d in DAYS]          # 通书当日分（分母基线）
rows = []
matrix = []
for (y, m, dd, h) in SAMPLES:
    b = E.compute_eightchar(y, m, dd, h)
    pr = E.day_master_profile(b["pillars"])
    raw = [E.bazi_day_report(b, inf)["score"] for inf in INFOS]
    matrix.append(raw)
    sc = sorted(raw)
    med = sc[len(sc) // 2]
    hi = sum(1 for v in sc if v >= 90) * 100.0 / len(sc)
    lo = sum(1 for v in sc if v <= 40) * 100.0 / len(sc)
    rows.append((("%04d-%02d-%02d %02d时" % (y, m, dd, h)), b["pillars"][2],
                 pr["ratio"], "身强" if pr["strong"] else "身弱",
                 med, sum(sc) / len(sc), sc[0], sc[-1], hi, lo))
    print("  %s 日柱%s ratio=%.2f %s → 中位%d 均值%.1f 范围%d..%d ≥90占%.0f%% ≤40占%.0f%%"
          % rows[-1])

meds = [r[4] for r in rows]
means = [round(r[5], 1) for r in rows]
strong_meds = [r[4] for r in rows if r[3] == "身强"]
weak_meds = [r[4] for r in rows if r[3] == "身弱"]
ck("③ 各八字均值不全相同（个性化生效）",
   len(set(means)) >= 4, "均值 = %s" % means)
ck("③ 全体中位落在 55~70（锚定生肖分后趋于中性，不再人人 70+）",
   all(55 <= m <= 70 for m in meds), "中位区间 %d..%d" % (min(meds), max(meds)))
# —— 真正的个性化：同一天、不同八字给出明显不同的分数 ——
_spread = [max(col) - min(col) for col in zip(*matrix)]
_avg_spread = sum(_spread) / len(_spread)
ck("③ 同一天不同八字分差平均 ≥ 12（评分确实因人而异）",
   _avg_spread >= 12, "平均分差 %.1f（最大 %d）" % (_avg_spread, max(_spread)))
_identical = sum(1 for a in range(len(matrix)) for b2 in range(a + 1, len(matrix))
                 if matrix[a] == matrix[b2])
ck("③ 任意两个八字的全年序列都不相同", _identical == 0,
   "%d 对完全相同" % _identical)
_diff_almanac = sum(abs(matrix[0][i] - INFOS[i]["fortune_score"])
                    for i in range(len(DAYS))) / len(DAYS)
ck("③ 个人分 ≠ 通书当日分（平均偏离 ≥ 8，说明确有个人化）",
   _diff_almanac >= 8, "平均偏离 %.1f" % _diff_almanac)
ck("③ 单八字年内分数跨度 ≥ 25（有起伏，不是一条平线）",
   all((r[7] - r[6]) >= 25 for r in rows),
   "跨度 = %s" % [r[7] - r[6] for r in rows])
ck("③ 分数恒在 5..98", all(5 <= r[6] and r[7] <= 98 for r in rows))
ck("③ 【去偏】身强 / 身弱两组中位不再系统性拉开（差 ≤6 分）",
   strong_meds and weak_meds
   and abs(sum(strong_meds) / len(strong_meds)
           - sum(weak_meds) / len(weak_meds)) <= 6,
   "身强中位 %s / 身弱中位 %s" % (strong_meds, weak_meds))
ck("③ 高分不泛滥：≥90 分的天数占比 ≤ 12%",
   all(r[8] <= 12 for r in rows), "≥90 占比 = %s" % [round(r[8]) for r in rows])
ck("③ 低分不泛滥：≤40 分的天数占比 ≤ 18%（生肖六冲会拉低，故上限放宽）",
   all(r[9] <= 18 for r in rows), "≤40 占比 = %s" % [round(r[9]) for r in rows])

# ---------- ④ v1.9.16 口径：个人分锚定「本命生肖分」±10 ----------
_anchor_dev = []
_out_of_band = 0
for (y, m, dd, h) in SAMPLES:
    b = E.compute_eightchar(y, m, dd, h)
    sx = b["shengxiao"]
    for inf in INFOS:
        p = E.bazi_day_report(b, inf)["score"]
        a = E.analyze_zodiac_day(inf, sx)["score"]
        d = p - a
        _anchor_dev.append(d)
        if abs(d) > 10:
            _out_of_band += 1
ck("④ 个人分恒在「本命生肖分」±10 以内（用户口径）",
   _out_of_band == 0, "越界 %d / %d" % (_out_of_band, len(_anchor_dev)))
_dev_mean = sum(_anchor_dev) / len(_anchor_dev)
ck("④ 个人分与生肖分年均偏离 ≈ 0（整体中性）",
   abs(_dev_mean) <= 1.5, "平均偏离 %+.2f（极值 %d..%d）"
   % (_dev_mean, min(_anchor_dev), max(_anchor_dev)))

print("\n==== 八字子平法评分实测 ====")
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
