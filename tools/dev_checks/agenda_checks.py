# -*- coding: utf-8 -*-
"""行事历数据层校验：严格/宽松解析、表格导入、模板往返、区间导出、手写覆写。

全部写到独立临时目录，不触碰用户的 agenda_cache.json / agenda_edit.json。
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from calendar_app import agenda_pdf as AG

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _box import make_box                                   # noqa: E402

BOX = make_box("_agenda_case")      # 退出时自动回收，不再累积在 build/
AG.CACHE_PATH = os.path.join(BOX, "agenda_cache.json")
AG.EDIT_PATH = os.path.join(BOX, "agenda_edit.json")

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""))


# ---------- 1. 严格格式（模板原格式，含全角括号/长破折号） ----------
strict = ("1）2027 丁未年\n"
          "九月丙戌（约 10.11–11.9 ）：本命伏吟，工作按标答辩。\n"
          "十 / 冬月丁亥（约 11.10–1.7 ）：宜静不宜动。\n"
          "引用 3 篇资料：……")
rs = AG.parse_agenda(strict)
ck("严格解析：2 条记录", len(rs) == 2, "得到 %d" % len(rs))
if len(rs) == 2:
    ck("严格解析：年份/干支年", rs[0]["year"] == "2027" and rs[0]["year_ganzhi"] == "丁未",
       "%s/%s" % (rs[0]["year"], rs[0]["year_ganzhi"]))
    ck("严格解析：合并月『十/冬』→ 两个月", rs[1]["months"] == ["十", "冬"],
       str(rs[1]["months"]))
    ck("严格解析：区间归一化", rs[0]["range"] == "10.11-11.9", rs[0]["range"])
    ck("严格解析：截断引用资料段", "引用" not in rs[1]["content"], rs[1]["content"][:30])

# ---------- 2. 宽松逐行（无括号区间 / 断行 / 无干支 / 阿拉伯月） ----------
loose = ("2026 丙午年\n"
         "\n"
         "九 丙戌 10.11-11.9\n"
         "本命伏吟，工作按标答辩。\n"
         "宜祈福。\n"
         "\n"
         "9月： plain 内容\n"
         "腊：腊月要点\n")
rl = AG.parse_agenda(loose)
ck("宽松解析：3 条记录", len(rl) == 3, "得到 %d :: %s" % (len(rl), [r["months"] for r in rl]))
if len(rl) == 3:
    ck("宽松解析：区间已从正文剥离",
       rl[0]["range"] == "10.11-11.9" and "10.11" not in rl[0]["content"],
       "range=%s content=%s" % (rl[0]["range"], rl[0]["content"][:24]))
    ck("宽松解析：多行归属同一条目", "宜祈福" in rl[0]["content"], rl[0]["content"])
    ck("宽松解析：阿拉伯数字月份", rl[1]["months"] == ["九"], str(rl[1]["months"]))
    ck("宽松解析：『腊』月", rl[2]["months"] == ["腊"], str(rl[2]["months"]))

# ---------- 3. 表格结构化（含表头） ----------
rows = [["月度行事历（模板）"],
        ["说明：每行一个农历月，「重点内容」填写注意事项。"],
        ["2026 丙午年"],
        ["农历月", "干支", "公历起", "公历止", "重点内容"],
        ["九月", "丙戌", "10.11", "11.9", "本命伏吟，工作按标答辩。"],
        ["十月", "丁亥", "11.10", "12.9", "宜静不宜动。"]]
rt = AG.parse_table(rows)
ck("表格解析：2 条记录", len(rt) == 2, "得到 %d" % len(rt))
if len(rt) == 2:
    ck("表格解析：年份取自标题行", rt[0]["year"] == "2026" and rt[0]["year_ganzhi"] == "丙午",
       "%s/%s" % (rt[0]["year"], rt[0]["year_ganzhi"]))
    ck("表格解析：起/止两列拼区间", rt[0]["range"] == "10.11-11.9", rt[0]["range"])
    ck("表格解析：正文不混入其它列", rt[0]["content"] == "本命伏吟，工作按标答辩。", rt[0]["content"])

# 无表头兜底
rows2 = [["九", "丙戌", "10.11-11.9", "本命伏吟"],
         ["冬", "戊子", "12.10-1.7", "宜静不宜动"]]
rt2 = AG.parse_table(rows2)
ck("表格解析：无表头兜底 2 条", len(rt2) == 2, "得到 %d" % len(rt2))
if len(rt2) == 2:
    ck("表格解析：无表头区间/正文", rt2[0]["range"] == "10.11-11.9"
       and rt2[0]["content"] == "本命伏吟", "%s | %s" % (rt2[0]["range"], rt2[0]["content"]))

# ---------- 4. Excel 模板生成 → 导入往返 ----------
xlsx = os.path.join(BOX, "月度行事历模板.xlsx")
AG.make_agenda_template(xlsx, 2026, "丙午年")
ck("模板：xlsx 已生成", os.path.exists(xlsx), "%.1f KB" % (os.path.getsize(xlsx) / 1024))
recs = AG.import_agenda(xlsx)
ck("模板往返：导入 12 个农历月", len(recs) == 12, "得到 %d" % len(recs))
if len(recs) == 12:
    ck("模板往返：月份与区间", recs[8]["months"] == ["九"] and recs[8]["range"] == "10.11-11.9",
       "%s %s" % (recs[8]["months"], recs[8]["range"]))
    ck("模板往返：年份声明被识别", recs[0]["year"] == "2026", recs[0]["year"])
    ck("模板往返：import_agenda 返回 list（len 可用）", isinstance(recs, list))

# PDF 模板仍可用
pdf = os.path.join(BOX, "月度行事历模板.pdf")
AG.make_agenda_template(pdf, 2026, "丙午年")
ck("模板：PDF 兼容生成", os.path.exists(pdf), "%.1f KB" % (os.path.getsize(pdf) / 1024))
rp = AG.import_agenda(pdf)
ck("模板往返：PDF 导入 12 条", len(rp) == 12, "得到 %d" % len(rp))

# ---------- 5. 区间导出 ----------
# 模板区间：八 9.11-10.10 / 九 10.11-11.9 / 十 11.10-12.9 / 冬 12.10-1.7(跨年→2027) / 腊 1.8-2.5
# 与 [2026-10-01, 2026-12-31] 有交集的是 八(尾段 10.1~10.10) / 九 / 十 / 冬 → 4 条
d1, d2 = date(2026, 10, 1), date(2026, 12, 31)
hit = AG.select_records_in_range(recs, d1, d2)
hit_months = ["".join(r["months"]) for r in hit]
ck("区间筛选：10-12 月命中 4 条（八/九/十/冬）", len(hit) == 4, "命中 %d :: %s" % (len(hit), hit_months))
ck("区间筛选：命中的正是八九十冬", hit_months == ["八", "九", "十", "冬"], str(hit_months))
ck("区间筛选：腊月(1.8-2.5) 不落在窗口内",
   all("".join(r["months"]) != "腊" for r in hit), str(hit_months))
# 跨年条目：冬月 12.10-1.7 应被识别为 2026-12-10 ~ 2027-01-07
winter = [r for r in recs if "".join(r["months"]) == "冬"]
if winter:
    a, b = AG.record_span(winter[0])
    ck("区间推算：冬月跨年 → 2026-12-10~2027-01-07",
       (a, b) == (date(2026, 12, 10), date(2027, 1, 7)), "%s~%s" % (a, b))
for ext in (".xlsx", ".csv", ".txt"):
    p = os.path.join(BOX, "export%s" % ext)
    cnt = AG.export_agenda(recs, d1, d2, p)
    ok = os.path.exists(p) and os.path.getsize(p) > 50
    ck("导出 %s：4 条且文件非空" % ext, ok and cnt == 4,
       "%d 条, %.1f KB" % (cnt, os.path.getsize(p) / 1024))
try:
    AG.export_agenda(recs, date(2001, 1, 1), date(2001, 2, 1),
                     os.path.join(BOX, "none.txt"))
    ck("导出：空区间应报错", False, "未抛异常")
except ValueError as e:
    ck("导出：空区间给出可读提示", "没有可导出" in str(e), str(e)[:40])

# ---------- 6. 手写覆写 ----------
AG.save_override("day", "2026-09-28", "今日手写备注")
ck("覆写：写入后可读", AG.get_override("day", "2026-09-28") == "今日手写备注")
AG.save_override("day", "2026-09-28", "")
ck("覆写：空串即删除", AG.get_override("day", "2026-09-28") == "")
AG.save_override("month", "丙午年|九", "本月手写")
ck("覆写：month 作用域独立", AG.get_override("month", "丙午年|九") == "本月手写"
   and AG.get_override("day", "丙午年|九") == "")

failed = [n_ for n_, c, _ in R if not c]
print("\n==== 行事历数据层校验 ==== total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, c, _ in R if c), len(failed)))
if failed:
    print("FAILED:", failed)
sys.exit(1 if failed else 0)
