# -*- coding: utf-8 -*-
"""国定假日：内置放假 / 调休表 + 用户导入（模板下载 · 表格导入）。

数据结构（years）::

    {2026: {"holidays": [["国庆节", "2026-10-01", "2026-10-07"], ...],
            "workdays": ["2026-10-10", ...]}}

- ``holidays``：放假区间（三元组「名称 / 起始日 / 结束日」）→ 触发**红色**主题。
- ``workdays``：**调休上班日**（周末被调为工作日）→ 保持**绿色**（平日）主题，
  且页头标注「调休上班」。

内置表随程序发布（``BUILTIN_YEARS``；2026 依《国务院办公厅关于 2026 年部分节假日
安排的通知》国办发明电〔2025〕7 号，2025-11-04）。用户在「关于本软件 → 国定假日导入」
下载 Excel 模板、填好导入后，写入可写配置目录下的 ``holidays.json``；**同一年**由
导入数据整体覆盖内置表，其余年份保留内置。

⚠ 全部离线：不联网、不上报。
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import date, datetime

from lunar_python import Solar

# --------------------------------------------------------------------------
# 内置表：年份 → {"holidays": [(名称, 起, 止)], "workdays": [日期]}
# --------------------------------------------------------------------------

BUILTIN_YEARS = {
    2026: {
        "holidays": [
            ("元旦", "2026-01-01", "2026-01-03"),
            ("春节", "2026-02-15", "2026-02-23"),      # 9 天（史上最长）
            ("清明节", "2026-04-04", "2026-04-06"),
            ("劳动节", "2026-05-01", "2026-05-05"),
            ("端午节", "2026-06-19", "2026-06-21"),
            ("中秋节", "2026-09-25", "2026-09-27"),
            ("国庆节", "2026-10-01", "2026-10-07"),
        ],
        # 调休上班（周末上班，不放假）
        "workdays": ["2026-01-04", "2026-02-14", "2026-02-28",
                     "2026-05-09", "2026-09-20", "2026-10-10"],
    },
    2027: {
        "holidays": [
            ("元旦", "2027-01-01", "2027-01-03"),
            ("春节", "2027-02-05", "2027-02-11"),
            ("清明节", "2027-04-03", "2027-04-05"),
            ("劳动节", "2027-05-01", "2027-05-05"),
            ("端午节", "2027-06-09", "2027-06-11"),
            ("中秋节", "2027-09-14", "2027-09-16"),
            ("国庆节", "2027-10-01", "2027-10-07"),
        ],
        "workdays": [],                                # 待国务院通知（可用导入更新）
    },
}

# 兜底：这些节日即便没进表，也按「节日当日」识别为法定假日
_FESTIVAL_NAMES = {"元旦", "国庆节", "劳动节", "春节", "端午节", "中秋节", "清明节"}

# 模板 / 导入共用的列名
COLS = ["类型", "名称", "开始日期", "结束日期"]
KIND_OFF = "放假"
KIND_WORK = "调休上班"


# --------------------------------------------------------------------------
# 路径与用户数据
# --------------------------------------------------------------------------

def _writable_dir():
    """可写目录：frozen 优先 exe 同目录，只读时回退 %APPDATA%/农历日历/。"""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(os.path.abspath(sys.executable))
        if os.access(base or ".", os.W_OK):
            return base
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"),
                            "农历日历")
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def holidays_path():
    """用户导入的假日表路径（与 settings.json 同目录）。"""
    return os.path.join(_writable_dir(), "holidays.json")


_CACHE = None          # (路径, mtime, years) —— 依 mtime 自动失效


def load_user_years():
    """读取用户导入表；文件不存在 / 损坏时返回 {}。"""
    global _CACHE
    p = holidays_path()
    try:
        mt = os.path.getmtime(p)
    except OSError:
        _CACHE = None
        return {}
    if _CACHE and _CACHE[0] == p and _CACHE[1] == mt:
        return _CACHE[2]
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        years = _coerce_years(raw.get("years") if isinstance(raw, dict) else raw)
    except Exception:
        years = {}
    _CACHE = (p, mt, years)
    return years


def save_user_years(years, dest=None):
    """写出用户导入表（默认写到 ``holidays_path()``）。"""
    global _CACHE
    p = dest or holidays_path()
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "years": years}, f, ensure_ascii=False, indent=1)
    _CACHE = None
    return p


def clear_user_years(dest=None):
    """删除用户导入表（恢复内置）。"""
    global _CACHE
    p = dest or holidays_path()
    try:
        if os.path.exists(p):
            os.remove(p)
    except OSError:
        pass
    _CACHE = None


def reload():
    """丢弃缓存（导入后调用，令页面立即用上新表）。"""
    global _CACHE
    _CACHE = None


def _coerce_years(raw):
    """把任意来源（JSON / 解析结果）规整成 ``{int: {"holidays", "workdays"}}``。"""
    out = {}
    if not isinstance(raw, dict):
        return out
    for y, slot in raw.items():
        try:
            yi = int(y)
        except (TypeError, ValueError):
            continue
        hs, ws = [], []
        if isinstance(slot, dict):
            for it in (slot.get("holidays") or []):
                if isinstance(it, (list, tuple)) and len(it) >= 3:
                    a, b, c = str(it[0]), str(it[1]), str(it[2])
                    if _parse_date(b) and _parse_date(c):
                        hs.append([a, b, c])
            for it in (slot.get("workdays") or []):
                if _parse_date(str(it)):
                    ws.append(str(it))
        out[yi] = {"holidays": hs, "workdays": ws}
    return out


def merged_years():
    """内置表 ← 用户导入表（同年整体覆盖）。"""
    years = {y: {"holidays": list(v["holidays"]),
                 "workdays": list(v["workdays"])}
             for y, v in BUILTIN_YEARS.items()}
    for y, v in load_user_years().items():
        years[y] = {"holidays": list(v["holidays"]),
                    "workdays": list(v["workdays"])}
    return years


# --------------------------------------------------------------------------
# 查询
# --------------------------------------------------------------------------

def get_holiday(d: date):
    """若为法定假日返回假名（如「国庆节」），否则 None。

    ⚠ 调休上班日（周末上班）**不算**假日，返回 None。
    """
    years = merged_years()
    if is_makeup_workday(d, years):
        return None
    for name, s, e in years.get(d.year, {}).get("holidays", []):
        ds, de = _parse_date(s), _parse_date(e)
        if ds and de and ds <= d <= de:
            return name
    # 兜底：节日当日识别（未来年份未及时更新表时仍能标红当天）
    try:
        solar = Solar.fromYmd(d.year, d.month, d.day)
        lunar = solar.getLunar()
        fests = set(solar.getFestivals()) | set(lunar.getFestivals())
        hit = fests & _FESTIVAL_NAMES
        if hit:
            return sorted(hit)[0]
        if lunar.getJieQi() == "清明":
            return "清明节"
    except Exception:
        pass
    return None


def is_makeup_workday(d: date, years=None):
    """是否为「调休上班日」（周末被调为工作日）。"""
    years = years if years is not None else merged_years()
    ws = years.get(d.year, {}).get("workdays", [])
    iso = d.isoformat()
    return iso in ws


# --------------------------------------------------------------------------
# 模板 / 导入
# --------------------------------------------------------------------------

def _parse_date(v):
    """宽松解析日期：date / datetime / 'YYYY-MM-DD' / 'YYYY/M/D' / 'YYYYMMDD'。"""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.split("T")[0].split(" ")[0]
    for sep in ("-", "/", ".", "年"):
        if sep in s:
            parts = [p for p in s.replace("月", "-").replace("日", "")
                     .replace(sep, "-").split("-") if p.strip()]
            if len(parts) >= 3:
                try:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
                except ValueError:
                    return None
    s2 = s.replace("-", "").replace("/", "")
    if len(s2) == 8 and s2.isdigit():
        try:
            return date(int(s2[:4]), int(s2[4:6]), int(s2[6:]))
        except ValueError:
            return None
    return None


def make_template(path):
    """生成国定假日模板（.xlsx；表头与 `parse_rows` 的列名映射一致）。

    预填内置表（当前年份），用户改成需要的内容后再导入。
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "国定假日"
    ws["A1"] = "国定假日 / 调休安排（模板）"
    ws["A1"].font = Font(size=14, bold=True)
    ws["A2"] = ("填法：① 放假 —— 类型填「放假」，名称填节日名，开始/结束日期都填"
                "（如 2026-10-01 / 2026-10-07）；"
                "② 调休上班 —— 类型填「调休上班」，只填开始日期（如 2026-10-10）。"
                "红色=放假，绿色=调休上班。导入后同一年整体覆盖内置表。")
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells("A2:D2")
    ws.row_dimensions[2].height = 46

    head_fill = PatternFill("solid", fgColor="C0392B")
    for c, name in enumerate(COLS, start=1):
        cell = ws.cell(row=4, column=c, value=name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center")

    years = merged_years()
    r = 5
    for y in sorted(years):
        for name, s, e in years[y]["holidays"]:
            for c, v in enumerate((KIND_OFF, name, s, e), start=1):
                ws.cell(row=r, column=c, value=v)
            r += 1
        for w in years[y]["workdays"]:
            for c, v in enumerate((KIND_WORK, "", w, ""), start=1):
                ws.cell(row=r, column=c, value=v)
            r += 1

    for col, w in zip("ABCD", (12, 12, 14, 14)):
        ws.column_dimensions[col].width = w
    wb.save(path)
    return path


def _rows_from_xlsx(path):
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    return [[("" if c is None else str(c).strip()) for c in row]
            for row in ws.iter_rows(values_only=True)]


def _rows_from_csv(path):
    for enc in ("utf-8-sig", "gbk", "utf-8"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                return [[(c or "").strip() for c in row]
                        for row in csv.reader(f)]
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别文件编码（请另存为 UTF-8 或 Excel）")


_COL_KEYS = (("kind", ("类型", "类别", "说明", "项")),
             ("name", ("名称", "节日", "假日", "备注")),
             ("start", ("开始", "起始", "起")),
             ("end", ("结束", "截止", "止")))


def _match_header(row):
    """若该行是表头则返回 {key: 列号}，否则 None。

    ⚠ 只认**短单元格**（≤8 字）里的列名：模板里有一行很长的填写说明同样含
    「类型 / 开始 / 日期」等字样，若按「行内含关键词」判断会把它误当成表头。
    """
    idx = {}
    for j, c in enumerate(row):
        c = str(c).strip()
        if not c or len(c) > 8:
            continue
        for key, names in _COL_KEYS:
            if key not in idx and any(c == n or c.startswith(n) for n in names):
                idx[key] = j
                break
    return idx if ("kind" in idx and "start" in idx) else None


def parse_rows(rows):
    """从二维表里提取 (类型, 名称, 开始, 结束) 行。

    先定位表头行（见 `_match_header`），再按列名取值；找不到表头时退化为
    「首列即类型」的朴素读取。
    """
    idx, hi = None, -1
    for i, row in enumerate(rows[:60]):
        got = _match_header(row)
        if got:
            idx, hi = got, i
            break
    out = []
    for row in rows[hi + 1:] if hi >= 0 else rows:
        if not any(str(c).strip() for c in row):
            continue
        if idx is None:
            kind = row[0] if len(row) > 0 else ""
            name = row[1] if len(row) > 1 else ""
            start = row[2] if len(row) > 2 else ""
            end = row[3] if len(row) > 3 else ""
        else:
            def _at(k):
                j = idx.get(k)
                return row[j] if j is not None and j < len(row) else ""
            kind, name, start, end = _at("kind"), _at("name"), _at("start"), _at("end")
        if not str(start).strip():
            continue
        if not _parse_date(start):
            continue
        out.append((str(kind), str(name), str(start), str(end)))
    return out


def years_from_rows(rows):
    """把 (类型, 名称, 开始, 结束) 行规整成 years 结构（按开始日的年份归档）。"""
    years = {}
    for kind, name, start, end in parse_rows(rows):
        d0 = _parse_date(start)
        if not d0:
            continue
        slot = years.setdefault(d0.year, {"holidays": [], "workdays": []})
        k = kind.strip()
        if ("班" in k) or ("工作" in k):
            slot["workdays"].append(d0.isoformat())
        else:
            d1 = _parse_date(end) or d0
            if d1 < d0:
                d0, d1 = d1, d0
            slot["holidays"].append([(name.strip() or "假日"),
                                     d0.isoformat(), d1.isoformat()])
    for slot in years.values():
        slot["workdays"] = sorted(set(slot["workdays"]))
        uniq, seen = [], set()
        for it in slot["holidays"]:
            key = tuple(it)
            if key not in seen:
                seen.add(key)
                uniq.append(it)
        slot["holidays"] = sorted(uniq, key=lambda x: x[1])
    return years


def import_holidays(path, dest=None):
    """导入国定假日文件（Excel / CSV）→ 规整 → 保存 → 返回摘要 dict。"""
    ext = os.path.splitext(path)[1].lower()
    rows = _rows_from_csv(path) if ext in (".csv", ".txt") else _rows_from_xlsx(path)
    years = years_from_rows(rows)
    if not years:
        raise ValueError("未解析到任何有效日期行，请检查「类型 / 开始日期」列是否填全")
    save_user_years(years, dest=dest)
    n_h = sum(len(v["holidays"]) for v in years.values())
    n_w = sum(len(v["workdays"]) for v in years.values())
    return {"years": sorted(years), "holiday_rows": n_h, "workday_rows": n_w,
            "path": dest or holidays_path()}
