# -*- coding: utf-8 -*-
"""国定假日 / 调休上班 实测（v1.9.18）。

校验：
  ① 内置表（2026 依国办发明电〔2025〕7 号）：放假区间与 6 个调休上班日逐条正确；
  ② 调休上班日**不算法定假日**、且页面信息里 `workday=True`、配色走绿；
  ③ 模板可生成 → 可原样回导（放假 14 段 / 调休 6 天，与内置表一致）；
  ④ 导入后**同一年整体覆盖**内置表，其余年份保持内置；
  ⑤ CSV 导入、无表头朴素读取、异常文件报错 均正常；
  ⑥ 用户表只落在指定路径，不污染工程目录。
"""
import os
import sys
import tempfile
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from calendar_app import holidays as H           # noqa: E402
from calendar_app.engine import get_day_info     # noqa: E402
from ui.theme import palette_for                 # noqa: E402

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))


# ---------- ① 内置表 ----------
_EXPECT_2026 = [("元旦", "2026-01-01", "2026-01-03"),
                ("春节", "2026-02-15", "2026-02-23"),
                ("清明节", "2026-04-04", "2026-04-06"),
                ("劳动节", "2026-05-01", "2026-05-05"),
                ("端午节", "2026-06-19", "2026-06-21"),
                ("中秋节", "2026-09-25", "2026-09-27"),
                ("国庆节", "2026-10-01", "2026-10-07")]
_EXPECT_WORK = ["2026-01-04", "2026-02-14", "2026-02-28",
                "2026-05-09", "2026-09-20", "2026-10-10"]
ck("① 2026 放假 7 段（含春节 2/15–2/23 共 9 天）",
   [tuple(x) for x in H.BUILTIN_YEARS[2026]["holidays"]] == _EXPECT_2026,
   str(H.BUILTIN_YEARS[2026]["holidays"]))
ck("① 2026 调休上班 6 天", sorted(H.BUILTIN_YEARS[2026]["workdays"]) == _EXPECT_WORK,
   str(sorted(H.BUILTIN_YEARS[2026]["workdays"])))
# 逐日核对放假区间端点与调休日
_bad = []
for name, s, e in _EXPECT_2026:
    if H.get_holiday(date(*map(int, s.split("-")))) != name:
        _bad.append(("起", name, s))
    if H.get_holiday(date(*map(int, e.split("-")))) != name:
        _bad.append(("止", name, e))
ck("① 7 段放假的起止端点均判定正确", not _bad, str(_bad))
ck("① 6 个调休日全部 is_makeup_workday=True",
   all(H.is_makeup_workday(date(*map(int, w.split("-")))) for w in _EXPECT_WORK))
ck("① 调休日都不是法定假日（get_holiday=None）",
   all(H.get_holiday(date(*map(int, w.split("-")))) is None for w in _EXPECT_WORK))
# 假期外的工作日不应被误判
ck("① 普通工作日（2026-10-12 周一）非假非调休",
   H.get_holiday(date(2026, 10, 12)) is None
   and not H.is_makeup_workday(date(2026, 10, 12)))

# ---------- ② 页面信息与配色 ----------
_cases = [
    (date(2026, 10, 10), True, "#1f9c3d", "周六调休上班 → 绿"),
    (date(2026, 10, 17), False, "#c62828", "普通周六 → 红"),
    (date(2026, 10, 11), False, "#c62828", "周日 → 红"),
    (date(2026, 10, 1), False, "#c62828", "国庆 → 红"),
    (date(2026, 10, 12), False, "#1f9c3d", "周一 → 绿"),
    (date(2026, 2, 14), True, "#1f9c3d", "春节前调休周六 → 绿"),
]
_bad2 = []
for d, expect_wd, color, tip in _cases:
    info = get_day_info(d)
    if info["workday"] != expect_wd or palette_for(info)["main"].name() != color:
        _bad2.append((str(d), info["workday"], palette_for(info)["main"].name()))
ck("② 调休/假日 的 workday 标志与红绿配色逐日正确", not _bad2, str(_bad2))

# ---------- ③ 模板生成 → 原样回导 ----------
tmp = tempfile.mkdtemp()
tpl = os.path.join(tmp, "国定假日模板.xlsx")
dest = os.path.join(tmp, "holidays.json")
H.make_template(tpl)
ck("③ 模板生成成功且非空", os.path.getsize(tpl) > 3000,
   "%d B" % os.path.getsize(tpl))
res = H.import_holidays(tpl, dest=dest)
ck("③ 模板原样回导：放假 14 段 / 调休 6 天 / 覆盖 2026+2027",
   res["holiday_rows"] == 14 and res["workday_rows"] == 6
   and res["years"] == [2026, 2027], str(res))
ck("③ 用户表落在指定路径（未污染工程目录）",
   os.path.exists(dest) and not os.path.exists(H.holidays_path()),
   "dest=%s" % dest)

# ---------- ④ 同年覆盖 / 异年保留 ----------
_save = H.holidays_path
try:
    H.holidays_path = lambda: dest
    H.reload()
    csvp = os.path.join(tmp, "h.csv")
    with open(csvp, "w", encoding="utf-8-sig") as f:
        f.write("类型,名称,开始日期,结束日期\n"
                "放假,元旦,2028-01-01,2028-01-03\n"
                "调休上班,,2028-01-08\n"
                "放假,春节,2028-01-25,2028-01-31\n")
    res2 = H.import_holidays(csvp, dest=dest)
    H.reload()
    mg = H.merged_years()
    ck("④ 导入 2028 后：2028 生效、2026/2027 保持内置",
       sorted(mg) == [2026, 2027, 2028] and len(mg[2026]["holidays"]) == 7
       and mg[2028]["holidays"][0][0] == "元旦", str(sorted(mg)))
    ck("④ CSV 导入计数正确（放假 2 段 / 调休 1 天）",
       res2["holiday_rows"] == 2 and res2["workday_rows"] == 1, str(res2))
    ck("④ 同一年（2028）再次导入整体覆盖",
       H.is_makeup_workday(date(2028, 1, 8), mg)
       and H.get_holiday(date(2028, 1, 1)) == "元旦")
finally:
    H.holidays_path = _save
    H.reload()

# ---------- ⑤ 解析健壮性 ----------
ck("⑤ 无表头文件按「首列即类型」朴素读取",
   H.years_from_rows([["放假", "清明", "2029-04-04", "2029-04-06"]])
   == {2029: {"holidays": [["清明", "2029-04-04", "2029-04-06"]], "workdays": []}})
ck("⑤ 日期宽松解析（- / . / 年月日 / 紧凑 8 位）",
   all(H._parse_date(s) == date(2026, 1, 4)
       for s in ("2026-01-04", "2026/1/4", "2026.01.04",
                 "2026年1月4日", "20260104")))
_dummy = os.path.join(tmp, "bad.csv")
with open(_dummy, "w", encoding="utf-8") as f:
    f.write("随便写点东西,没有日期\n")
try:
    H.import_holidays(_dummy, dest=dest)
    _raised = False
except Exception:
    _raised = True
ck("⑤ 无效文件抛异常（不静默写坏表）", _raised)
ck("⑤ 天数倒置自动纠正（结束 < 开始 → 交换）",
   H.years_from_rows([["放假", "x", "2030-05-10", "2030-05-01"]])
   == {2030: {"holidays": [["x", "2030-05-01", "2030-05-10"]], "workdays": []}})

print("\n==== 国定假日 / 调休 实测 ====")
for name, ok, detail in R:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, ("  :: " + detail) if detail else ""))
bad = [n for n, ok, _ in R if not ok]
print("total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, ok, _ in R if ok), len(bad)))
if bad:
    print("FAILED:", bad)
sys.exit(1 if bad else 0)
