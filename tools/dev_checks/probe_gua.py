# -*- coding: utf-8 -*-
"""今日卦象（六十四卦）实测（v1.9.17）。

校验：
  ① 覆盖率：连续 800 天 **64 卦全覆盖**，且无一天缺卦（旧「日干→上/日支→下」只有 32/64）；
  ② 六爻自洽：``lines`` 六位，反推内/外卦三爻 → 卦名与 GUA64 表一致；
  ③ 起卦式独立复算：按「梅花易数年月日式」独立算上/下卦数，与 daily_gua 输出一致；
  ④ 确定性：同一天多次调用结果恒等；
  ⑤ 文案完整：64 卦皆有简释；八纯卦全名作「乾为天」式；
  ⑥ 分布：每卦至少出现一次，最密/最稀 < 6。
"""
import os
import sys
from datetime import date, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from calendar_app import gua as G                    # noqa: E402
from calendar_app.engine import get_day_info         # noqa: E402

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


D0 = date(2026, 1, 1)
N = 800
infos = [get_day_info(D0 + timedelta(days=i)) for i in range(N)]

# ---------- ① 覆盖 ----------
names = [inf["gua"]["name"] if inf.get("gua") else None for inf in infos]
missing = [i for i, n in enumerate(names) if not n]
ck("① 800 天无一天缺卦", not missing, "缺卦 %d 天" % len(missing))
uniq = {n for n in names if n}
ck("① 卦覆盖率 64 / 64（旧法仅 32）", len(uniq) == 64,
   "覆盖 %d / 64，缺 %s" % (len(uniq), sorted(set(G.GUA_DESC) - uniq)))

# ---------- ② 六爻自洽 ----------
_rev = {}
for _n, (_name, _nat, _ln) in G.XIAN_TIAN.items():
    _rev[tuple(_ln)] = _name
bad_lines = []
for inf in infos:
    g = inf.get("gua")
    if not g:
        continue
    ln = g["lines"]
    if len(ln) != 6 or set(ln) - {0, 1}:
        bad_lines.append((inf["date"], "长度/取值", ln))
        continue
    lo = _rev.get(tuple(ln[:3]))
    up = _rev.get(tuple(ln[3:]))
    if not lo or not up:
        bad_lines.append((inf["date"], "三爻非法", ln))
        continue
    r, c = G._TRIGRAM_SEQ.index(up), G._TRIGRAM_SEQ.index(lo)
    if G.GUA64[r][c] != g["name"]:
        bad_lines.append((inf["date"], "卦名不符", g["name"]))
ck("② 六爻反推的卦名与 GUA64 表一致", not bad_lines, str(bad_lines[:3]))

# ---------- ③ 起卦式独立复算 ----------
ZHI = G.ZHI_ORDER
bad_formula = []
for inf in infos[:200]:
    yb = ZHI.index(inf["year_ganzhi"][1]) + 1
    zb = ZHI.index(inf["day_ganzhi"][1]) + 1
    base = yb + inf["lunar_month_num"] + inf["lunar_day_num"]

    def _num(n):
        r = n % 8
        return r if r else 8
    up_n, lo_n = _num(base), _num(base + zb)
    up_name = G.XIAN_TIAN[up_n][0]
    lo_name = G.XIAN_TIAN[lo_n][0]
    g = inf["gua"]
    if g["upper"] != "%s(%s)" % (up_name, G.XIAN_TIAN[up_n][1]) or \
       g["lower"] != "%s(%s)" % (lo_name, G.XIAN_TIAN[lo_n][1]):
        bad_formula.append((inf["date"], g["upper"], g["lower"], up_name, lo_name))
ck("③ 起卦式独立复算 = daily_gua 输出", not bad_formula, str(bad_formula[:3]))

# ---------- ④ 确定性 ----------
d = date(2026, 10, 3)
ck("④ 同一天多次调用恒等", G.daily_gua(get_day_info(d)) == G.daily_gua(get_day_info(d)))

# ---------- ⑤ 文案完整 ----------
ck("⑤ 64 卦皆有简释", len(G.GUA_DESC) == 64 and all(G.GUA_DESC.values()),
   "desc 条目 %d" % len(G.GUA_DESC))
_ba = [inf["gua"]["full"] for inf in infos if inf["gua"]["name"] == "乾"]
ck("⑤ 八纯卦全名作「乾为天」式", _ba and all(f == "乾为天" for f in _ba), str(_ba[:2]))
ck("⑤ 每卦 tip 文案含卦名与简释",
   all(G.gua_tip(inf["gua"]).startswith(inf["gua"]["name"] + "卦")
       and inf["gua"]["desc"] in G.gua_tip(inf["gua"]) for inf in infos[:120]))

# ---------- ⑥ 分布 ----------
cnt = Counter(names)
lo_c, hi_c = min(cnt.values()), max(cnt.values())
ck("⑥ 分布：每卦皆现，最密/最稀 < 6", lo_c >= 1 and hi_c / lo_c < 6,
   "最稀 %d 最密 %d（%d 天）" % (lo_c, hi_c, N))

print("\n==== 今日卦象（六十四卦）实测 ====")
for _d in (date(2026, 10, 3), date(2026, 10, 10), date(2026, 10, 11)):
    _g = get_day_info(_d)["gua"]
    print("  %s  卦=%s（%s）  上%s 下%s  爻=%s"
          % (_d, _g["name"], _g["full"], _g["upper"], _g["lower"],
             "".join(str(x) for x in _g["lines"])))
print("  样例提示：\n    " + G.gua_tip(get_day_info(date(2026, 10, 3))["gua"])
      .replace("\n", "\n    "))
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d" % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
