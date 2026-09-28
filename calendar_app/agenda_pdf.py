# -*- coding: utf-8 -*-
"""农历日历 - 行事历数据层：模板 / 导入 / 导出 / 缓存 / 手写覆写。

支持的数据源（全部**离线**解析，不依赖网络与外置模型）：
  · Excel 表格  .xlsx          —— 结构化读取（推荐，模板即此格式）
  · CSV 表格    .csv
  · PDF         .pdf           —— pypdf 提取文本
  · Word        .docx          —— 读 zip 内 word/document.xml
  · 纯文本      .txt / 其它

解析策略（两层）：
  1. 结构化：表格类按表头列名直接映射（农历月 / 干支 / 公历起止 / 重点内容）；
  2. 锚点文本：先按《月度行事历》严格格式匹配，失败再走**宽松逐行锚点** ——
     逐行识别「年份头」「农历月条目头」（干支与（约 x.x–x.x）区间均可省略），
     条目头之后的行归属该月要点。因此对换行、断行、列错位都不敏感。

行事历条目记录结构：
  {year, year_ganzhi, months:[正/二/…/十/冬/腊], ganzhi, range, content}
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import sys
from datetime import date

from calendar_app.engine import LUNAR_MONTH_ALIAS

# frozen exe：数据文件与 exe 同目录；源码运行：与模块同目录
if getattr(sys, "frozen", False):
    _BASE = os.path.dirname(os.path.abspath(sys.executable))
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CACHE_PATH = os.path.join(_BASE, "agenda_cache.json")
EDIT_PATH = os.path.join(_BASE, "agenda_edit.json")

# 标准农历月名（与 LUNAR_MONTH_ALIAS 的取值一致，用于和 engine 匹配）
MONTH_ORDER = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
_MONTH_NUM = {n: i + 1 for i, n in enumerate(MONTH_ORDER)}
_MONTH_NAME = {i + 1: n for i, n in enumerate(MONTH_ORDER)}
_MONTH_CN_NUM = {"正": 1, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
                 "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "冬": 11,
                 "十二": 12, "腊": 12}

_GZ = r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]"
_MK = r"[正二三四五六七八九十冬腊]"

# 严格格式：九月戊戌（约 10.8–11.6 ）：
_RE_MONTH = re.compile(
    r"([正二三四五六七八九十冬腊]{1,2})月\s*([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])?\s*"
    r"[（(]\s*约?\s*([\d.]+)\s*[-–—～]\s*([\d.]+)\s*[)）]\s*[：:]\s*")
# 合并月写法：四 / 五月丙午（约 5–7 ）：
_RE_MONTH_COMBINED = re.compile(
    r"([正二三四五六七八九十冬腊]{1,2})\s*/\s*([正二三四五六七八九十冬腊]{1,2})月\s*"
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])?\s*"
    r"[（(]\s*约?\s*([\d.]+)\s*[-–—～]\s*([\d.]+)\s*[)）]\s*[：:]\s*")
# 年份标题：1）2027 丁未年 / 2026 丙午年
_RE_YEAR = re.compile(r"(\d{4})\s*([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])年")
_RE_RANGE = re.compile(r"(\d{1,2})\.(\d{1,2})\s*[-–—～]\s*(\d{1,2})\.(\d{1,2})")


# --------------------------------------------------------------------------
# 文本归一化
# --------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """统一全角/半角与各类破折号，便于锚点匹配。"""
    table = str.maketrans({
        "（": "(", "）": ")", "：": ":", "，": ",", "；": ";",
        "～": "-", "—": "-", "–": "-",
        "０": "0", "１": "1", "２": "2", "３": "3", "４": "4",
        "５": "5", "６": "6", "７": "7", "８": "8", "９": "9",
    })
    return text.translate(table)


def _month_from_token(tok) -> str:
    """『九 / 九月 / 9 / 9月 / 冬月 / 十一』→ 标准月名；无法识别返回 ''。"""
    t = re.sub(r"\s+", "", str(tok or "")).replace("月", "").replace("闰", "")
    if not t:
        return ""
    if t.isdigit():
        n = int(t)
        return _MONTH_NAME.get(n, "")
    n = _MONTH_CN_NUM.get(t)
    if n:
        return _MONTH_NAME[n]
    if t in _MONTH_NUM:
        return t
    if len(t) > 1 and t[-1] in _MONTH_NUM:
        return t[-1]
    return ""


# --------------------------------------------------------------------------
# 各格式文本提取
# --------------------------------------------------------------------------
def extract_pdf_text(path: str) -> str:
    """提取 PDF 全文文本。"""
    from pypdf import PdfReader
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(parts)


def extract_docx_text(path: str) -> str:
    """提取 Word (.docx) 全文文本（docx 即 zip 包内的 word/document.xml）。"""
    import zipfile
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)      # 段落换行
    xml = re.sub(r"<[^>]+>", "", xml)       # 去标签
    return xml


def extract_xlsx_rows(path: str) -> list:
    """读取 Excel 工作簿全部单元格（值），返回二维字符串表。"""
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    rows = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            rows.append(["" if v is None else
                         (v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v)
                         for v in row])
    wb.close()
    return rows


def extract_csv_rows(path: str) -> list:
    """读取 CSV（自动识别 utf-8 / gbk / utf-8-sig），返回二维字符串表。"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", "ignore")
    return [row for row in csv.reader(text.splitlines()) if row]


def rows_to_text(rows: list) -> str:
    """把二维表拼成逐行文本（供锚点解析兜底）。"""
    return "\n".join("\t".join("" if c is None else str(c) for c in row)
                     for row in rows)


# --------------------------------------------------------------------------
# 解析 · 一：表格结构化（表头列名映射）
# --------------------------------------------------------------------------
_HEAD_KEYS = {
    "month": ("农历月", "月份", "农历月份", "月"),
    "ganzhi": ("干支", "月干支", "干支月"),
    "range": ("区间", "公历", "公历区间", "日期", "大致区间"),
    "start": ("起", "起日", "开始", "自"),
    "end": ("止", "止日", "结束", "至"),
    "content": ("重点", "重点内容", "内容", "注意事项", "要点", "行事历", "备注"),
}


def _header_score(row) -> dict:
    """返回该行命中的列类别 -> 列号（同一类别取第一个命中列）。"""
    hit = {}
    for ci, cell in enumerate(row):
        val = re.sub(r"\s+", "", str(cell or ""))
        for cat, keys in _HEAD_KEYS.items():
            if cat in hit:
                continue
            for k in keys:
                if val == k or (len(val) <= 6 and k in val and k != "月"):
                    hit[cat] = ci
                    break
                if k == "月" and val == "月":
                    hit[cat] = ci
                    break
    return hit


def parse_table(rows: list) -> list:
    """把二维表格解析为行事历记录（表头映射优先，无表头则按首列月名兜底）。"""
    rows = [[("" if c is None else str(c)) for c in (r or [])] for r in rows]

    best, best_score = None, 0
    for i, row in enumerate(rows):
        hit = _header_score(row)
        score = len(hit)
        if "month" in hit and score > best_score:
            best, best_score = (i, hit), score
    if best and best_score >= 3:
        hdr_i, hit = best
        year, year_gz = _find_year(rows[:hdr_i] + rows[hdr_i + 1:])
        out = []
        for row in rows[hdr_i + 1:]:
            cells = list(row) + [""] * 8
            m = _month_from_token(cells[hit["month"]])
            if not m:
                continue
            if "start" in hit and "end" in hit:
                s, e = str(cells[hit["start"]]).strip(), str(cells[hit["end"]]).strip()
                rng = "%s-%s" % (s, e)
            elif "range" in hit:
                rng = str(cells[hit["range"]])
            else:
                rng = ""
            mm = _RE_RANGE.search(rng.replace("–", "-").replace("—", "-")
                                  .replace("～", "-"))
            rng = ("%s-%s" % (mm.group(1) + "." + mm.group(2),
                              mm.group(3) + "." + mm.group(4))) if mm else rng.strip()
            content = str(cells[hit["content"]]).strip() if "content" in hit else ""
            if not content:
                tail = [c for j, c in enumerate(row) if j != hit["month"]]
                content = " ".join(str(c).strip() for c in tail if str(c).strip())
            out.append({"year": year, "year_ganzhi": year_gz, "months": [m],
                        "ganzhi": str(cells[hit["ganzhi"]]).strip()
                        if "ganzhi" in hit else "",
                        "range": rng, "content": re.sub(r"\s+", " ", content).strip()})
        out = [r for r in out if r["content"]]
        if out:
            return out

    # 兜底：无表头 —— 首列是月名即视为一条记录
    year, year_gz = _find_year(rows)
    out = []
    for row in rows:
        cells = [str(c).strip() for c in row if str(c).strip()]
        if not cells:
            continue
        m = _month_from_token(cells[0])
        if not m:
            continue
        rest = cells[1:]
        gz = rest[0] if rest and re.fullmatch(_GZ, rest[0]) else ""
        if gz:
            rest = rest[1:]
        rng = ""
        joined = " ".join(rest)
        mm = _RE_RANGE.search(joined)
        if mm:
            rng = "%s.%s-%s.%s" % (mm.group(1), mm.group(2), mm.group(3), mm.group(4))
            rest = [p for p in rest if not _RE_RANGE.search(p)]
        content = " ".join(p for p in rest
                           if not re.fullmatch(r"[\d.]+", p.strip())).strip()
        if content:
            out.append({"year": year, "year_ganzhi": year_gz, "months": [m],
                        "ganzhi": gz, "range": rng,
                        "content": re.sub(r"\s+", " ", content)})
    return out


def _find_year(rows):
    """在表格单元格里找『2026 丙午年』之类的年份声明。"""
    for row in rows:
        for cell in row:
            m = _RE_YEAR.search(str(cell or ""))
            if m:
                return m.group(1), m.group(2)
    for row in rows:
        for cell in row:
            m = re.search(_GZ + r"年", str(cell or ""))
            if m:
                return "", m.group(0)[:-1]
    return "", ""


# --------------------------------------------------------------------------
# 解析 · 二：锚点文本（严格 → 宽松逐行）
# --------------------------------------------------------------------------
def parse_agenda(text: str) -> list:
    """把行事历文本解析为记录列表（严格匹配失败时自动走宽松逐行锚点）。"""
    text = normalize_text(text)
    cut = re.search(r"引用\s*\d+\s*篇资料", text)
    if cut:
        text = text[:cut.start()]

    records = _parse_strict(text)
    if not records:
        records = _parse_loose(text)
    return records


def _parse_strict(text: str) -> list:
    """按《月度行事历》原始格式精确匹配（保留旧版兼容）。"""
    records = []
    year, year_gz = None, ""
    events = []
    for m in _RE_YEAR.finditer(text):
        events.append((m.start(), "year", (m.group(1), m.group(2))))
    for m in _RE_MONTH.finditer(text):
        events.append((m.start(), "month",
                       (m.group(1), m.group(2), "%s-%s" % (m.group(3), m.group(4)), m.end())))
    for m in _RE_MONTH_COMBINED.finditer(text):
        events.append((m.start(), "month2",
                       (m.group(1), m.group(2), m.group(3),
                        "%s-%s" % (m.group(4), m.group(5)), m.end())))
    events.sort(key=lambda x: x[0])
    seen, dedup = set(), []
    for ev in events:
        if ev[0] in seen:
            continue
        seen.add(ev[0])
        dedup.append(ev)
    # 2) 去掉嵌在上一条条目头内部的匹配（如『十 / 冬月』整体匹配后，内部『冬月』不再单算）
    #    必须在切片前完成：否则下一条条目头的起点会取到被丢弃的重复项，正文被截成空串
    kept, last_end = [], -1
    for ev in dedup:
        pos, kind, payload = ev[0], ev[1], ev[2]
        if kind != "year" and pos < last_end:
            continue
        if kind != "year":
            last_end = max(last_end, payload[-1])
        kept.append(ev)
    # 3) 按保留下来的条目头切片取正文
    for idx, (pos, kind, payload) in enumerate(kept):
        if kind == "year":
            year, year_gz = payload[0], payload[1]
            continue
        if year is None:
            continue
        end = payload[-1]
        if kind == "month":
            month_key, gz, rng = payload[0], payload[1] or "", payload[2]
            months = [LUNAR_MONTH_ALIAS.get(month_key, month_key)]
        else:
            mk1, mk2, gz, rng = payload[0], payload[1], payload[2] or "", payload[3]
            months = [LUNAR_MONTH_ALIAS.get(mk1, mk1), LUNAR_MONTH_ALIAS.get(mk2, mk2)]
        nxt = kept[idx + 1][0] if idx + 1 < len(kept) else len(text)
        content = re.sub(r"\s+", " ", text[end:nxt]).strip()
        if not content:
            continue
        records.append({"year": year, "year_ganzhi": year_gz, "months": months,
                        "ganzhi": gz, "range": rng, "content": content})
    return records


# 宽松逐行：条目头 = [行首]月名[月][干支][(约 a-b)][:] ；干支与区间均可省略
_RE_LINE_MONTH = re.compile(
    r"^\s*([正二三四五六七八九十冬腊]|十[一二]|[1-9]|1[0-2])\s*月?\s*"
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])?\s*"
    r"(?:\(约?\s*(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\s*\))?\s*[:：,，]?\s*(.*)$")
_RE_LINE_MONTH2 = re.compile(
    r"^\s*([正二三四五六七八九十冬腊]{1,2})\s*/\s*([正二三四五六七八九十冬腊]{1,2})\s*月?\s*"
    r"([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])?\s*"
    r"(?:\(约?\s*(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\s*\))?\s*[:：,，]?\s*(.*)$")


def _is_year_line(line: str):
    m = _RE_YEAR.search(line)
    if m and len(line) <= 40:
        return m.group(1), m.group(2)
    m = re.search("(" + _GZ + ")年", line)
    if m and len(line) <= 24:
        return "", m.group(1)
    return None


def _parse_loose(text: str) -> list:
    """逐行锚点解析：对 PDF 断行 / Word 段落 / 手写排版都不敏感。"""
    lines = [ln.strip() for ln in text.splitlines()]
    records, year, year_gz = [], None, ""
    cur = None          # 当前正在收集内容的记录
    for ln in lines:
        if not ln:
            continue
        y = _is_year_line(ln)
        if y:
            if cur and cur["content"]:
                records.append(cur)
            cur = None
            year, year_gz = y[0], y[1]
            continue
        got = _head_month_line(ln)
        if got:
            if cur and cur["content"]:
                records.append(cur)
            months, gz, rng, rest = got
            cur = {"year": year, "year_ganzhi": year_gz, "months": months,
                   "ganzhi": gz, "range": rng, "content": rest.strip()}
            continue
        if cur is not None:
            cur["content"] = (cur["content"] + " " + ln).strip()
    if cur and cur["content"]:
        records.append(cur)
    out = []
    for r in records:
        r["content"] = re.sub(r"\s+", " ", r["content"]).strip()
        if r["content"]:
            out.append(r)
    return out


def _head_month_line(line: str):
    """识别一行是否为农历月条目头，返回 (months, ganzhi, range, 其余文本)。"""
    m = _RE_LINE_MONTH2.match(line)
    if m:
        mk1, mk2, gz, a, b, c, d, rest = m.groups()
        months = [_month_from_token(mk1), _month_from_token(mk2)]
        nums = (a, b, c, d)
    else:
        m = _RE_LINE_MONTH.match(line)
        if not m:
            return None
        mk, gz, a, b, c, d, rest = m.groups()
        months = [_month_from_token(mk)]
        nums = (a, b, c, d)
    if not months or not all(months):
        return None
    rng = ""
    if all(nums):
        rng = "%s.%s-%s.%s" % tuple(nums)
    else:
        mm = _RE_RANGE.search(rest or "")
        if mm:
            rng = "%s.%s-%s.%s" % (mm.group(1), mm.group(2), mm.group(3), mm.group(4))
            rest = (rest[:mm.start()] + " " + rest[mm.end():]).strip()
    return months, gz or "", rng, rest or ""


# --------------------------------------------------------------------------
# 导入入口
# --------------------------------------------------------------------------
TABLE_EXT = (".xlsx", ".xlsm", ".csv")


def import_agenda(path: str) -> list:
    """按扩展名导入行事历，返回记录列表并写入缓存。"""
    ext = os.path.splitext(path)[1].lower()
    records = []
    if ext in (".xlsx", ".xlsm"):
        rows = extract_xlsx_rows(path)
        records = parse_table(rows) or parse_agenda(rows_to_text(rows))
    elif ext == ".csv":
        rows = extract_csv_rows(path)
        records = parse_table(rows) or parse_agenda(rows_to_text(rows))
    elif ext == ".pdf":
        records = parse_agenda(extract_pdf_text(path))
    elif ext == ".docx":
        records = parse_agenda(extract_docx_text(path))
    elif ext in (".xls", ".doc"):
        raw = open(path, "rb").read()
        for enc in ("utf-8", "gbk", "utf-16"):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", "ignore")
        records = parse_agenda(text)
    else:
        raw = open(path, "rb").read()
        text = raw.decode("utf-8", "ignore")
        if "月" not in text:
            text = raw.decode("gbk", "ignore")
        records = parse_agenda(text)

    if not records:
        raise ValueError(
            "未能识别出农历月行事历条目。支持：Excel 表格（表头含 农历月/干支/公历区间/重点内容）、"
            "《月度行事历》格式 PDF / Word（九月戊戌（约 10.8–11.6）：要点）。"
            "可先下载模板对照。")
    save_cache(records, source=os.path.basename(path))
    return records


# --------------------------------------------------------------------------
# 模板
# --------------------------------------------------------------------------
_TEMPLATE_MONTHS = [("正", "戊寅", "2.17", "3.18"), ("二", "己卯", "3.19", "4.16"),
                    ("三", "庚辰", "4.17", "5.16"), ("四", "辛巳", "5.17", "6.14"),
                    ("五", "壬午", "6.15", "7.13"), ("六", "癸未", "7.14", "8.12"),
                    ("七", "甲申", "8.13", "9.10"), ("八", "乙酉", "9.11", "10.10"),
                    ("九", "丙戌", "10.11", "11.9"), ("十", "丁亥", "11.10", "12.9"),
                    ("冬", "戊子", "12.10", "1.7"), ("腊", "己丑", "1.8", "2.5")]


def make_agenda_template(path: str, year: int = 2026, year_gz: str = "丙午年"):
    """生成行事历模板：.xlsx 为表格（推荐），.pdf 为旧版逐行文档。"""
    if os.path.splitext(path)[1].lower() in (".xlsx", ".xlsm"):
        _make_xlsx_template(path, year, year_gz)
    else:
        _make_pdf_template(path, year, year_gz)


def _make_xlsx_template(path: str, year: int, year_gz: str):
    """生成 Excel 表格模板（表头与 parse_table 的列名映射一致）。"""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "月度行事历"
    head_fill = PatternFill("solid", fgColor="1F9C3D")
    head_font = Font(color="FFFFFF", bold=True, size=11)
    thin = Side(style="thin", color="BBBBBB")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = "月度行事历（模板）"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = ("说明：每行一个农历月，「重点内容」填写该月注意事项；"
                "填写后通过「导入行事历」选择本文件即可。"
                "可增删行，也可只填需要的月份。")
    ws["A2"].font = Font(size=10, color="666666")
    ws["A3"] = "%d %s" % (year, year_gz)
    ws["A3"].font = Font(bold=True, size=12)

    headers = ["农历月", "干支", "公历起", "公历止", "重点内容"]
    for ci, h in enumerate(headers, start=1):
        cell = ws.cell(row=5, column=ci, value=h)
        cell.fill = head_fill
        cell.font = head_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border
    for ri, (mk, gz, r1, r2) in enumerate(_TEMPLATE_MONTHS, start=6):
        vals = [mk + "月", gz, r1, r2, "在此填写该农历月的注意事项……"]
        for ci, v in enumerate(vals, start=1):
            cell = ws.cell(row=ri, column=ci, value=v)
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=(ci == 5))
    for ci, wd in enumerate((10, 10, 10, 10, 68), start=1):
        ws.column_dimensions[get_column_letter(ci)].width = wd
    ws.freeze_panes = "A6"
    wb.save(path)


def _make_pdf_template(path: str, year: int, year_gz: str):
    """旧版 PDF 模板（保留兼容，格式与严格解析一致）。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 60
    c.setFont("STSong-Light", 16)
    c.drawString(60, y, "月度行事历（模板）")
    c.setFont("STSong-Light", 10)
    y -= 24
    c.drawString(60, y, "说明：按下方格式逐月填写，「（约 x.x–x.x）」为该农历月大致公历区间，")
    y -= 16
    c.drawString(60, y, "冒号后写该农历月注意事项。填写完成后，通过「导入行事历」选择本文件导入。")
    y -= 30
    c.setFont("STSong-Light", 13)
    c.drawString(60, y, "1）%d %s" % (year, year_gz))
    y -= 24
    c.setFont("STSong-Light", 11)
    for mk, gz, r1, r2 in _TEMPLATE_MONTHS:
        c.drawString(60, y, "%s月%s（约 %s–%s ）：在此填写该农历月的注意事项……"
                     % (mk, gz, r1, r2))
        y -= 20
        if y < 60:
            c.showPage()
            c.setFont("STSong-Light", 11)
            y = h - 60
    c.save()


# --------------------------------------------------------------------------
# 导出（按日期区间）
# --------------------------------------------------------------------------
def record_span(rec: dict, default_year=None):
    """由 range（如 10.8-11.6）与年份推算该条目的公历起止日期。"""
    rng = (rec or {}).get("range", "") or ""
    m = _RE_RANGE.search(rng.replace("–", "-").replace("—", "-").replace("～", "-"))
    try:
        year = int(str(rec.get("year") or default_year or 0) or 0)
    except (TypeError, ValueError):
        year = 0
    if not (m and year):
        return None, None
    m1, d1, m2, d2 = (int(x) for x in m.groups())
    try:
        a = date(year, m1, d1)
    except ValueError:
        return None, None
    try:
        b = date(year, m2, d2)
    except ValueError:
        return None, None
    if b < a:                       # 区间跨年（如 冬月 12.10-1.7）
        try:
            b = date(year + 1, m2, d2)
        except ValueError:
            pass
    return a, b


def select_records_in_range(records: list, d1: date, d2: date) -> list:
    """选出与 [d1, d2] 有交集的行事历条目（无区间的按年份兜底）。"""
    out = []
    for rec in records or []:
        a, b = record_span(rec)
        if a and b:
            if not (b < d1 or a > d2):
                out.append(rec)
            continue
        try:
            if int(str(rec.get("year") or 0)) in (d1.year, d2.year):
                out.append(rec)
        except (TypeError, ValueError):
            continue
    return out


def export_agenda(records: list, d1: date, d2: date, path: str) -> int:
    """导出 [d1, d2] 区间内的行事历，按扩展名写 txt / csv / xlsx。返回条数。"""
    picked = select_records_in_range(records, d1, d2)
    if not picked:
        raise ValueError("该日期区间内没有可导出的行事历条目（请先导入行事历，"
                         "或核对区间是否落在条目的公历区间内）。")
    ext = os.path.splitext(path)[1].lower()
    if d2 < d1:
        d1, d2 = d2, d1
    if ext == ".xlsx":
        _export_xlsx(picked, d1, d2, path)
    elif ext == ".csv":
        _export_csv(picked, d1, d2, path)
    else:
        _export_txt(picked, d1, d2, path)
    return len(picked)


def _xlsx_rows(picked, d1, d2):
    return [["年份", "干支年", "农历月", "月干支", "公历区间", "重点内容"]] + [
        [r.get("year") or "", r.get("year_ganzhi") or "",
         "、".join(m + "月" for m in (r.get("months") or [])),
         r.get("ganzhi") or "", r.get("range") or "", r.get("content") or ""]
        for r in picked]


def _export_xlsx(picked, d1, d2, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    ws = wb.active
    ws.title = "行事历"
    ws["A1"] = "行事历导出（%s ~ %s）" % (d1.isoformat(), d2.isoformat())
    ws["A1"].font = Font(bold=True, size=13)
    rows = _xlsx_rows(picked, d1, d2)
    for ri, row in enumerate(rows, start=3):
        for ci, v in enumerate(row, start=1):
            cell = ws.cell(row=ri, column=ci, value=v)
            if ri == 3:
                cell.font = Font(color="FFFFFF", bold=True)
                cell.fill = PatternFill("solid", fgColor="1F9C3D")
                cell.alignment = Alignment(horizontal="center")
            cell.alignment = Alignment(vertical="top", wrap_text=(ci == 6))
    for ci, wd in enumerate((8, 10, 12, 10, 14, 80), start=1):
        ws.column_dimensions[get_column_letter(ci)].width = wd
    wb.save(path)


def _export_csv(picked, d1, d2, path):
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write("行事历导出（%s ~ %s）\n" % (d1.isoformat(), d2.isoformat()))
        w = csv.writer(f)
        for row in _xlsx_rows(picked, d1, d2):
            w.writerow(row)


def _export_txt(picked, d1, d2, path):
    lines = ["行事历导出（%s ~ %s）" % (d1.isoformat(), d2.isoformat()),
             "=" * 46, ""]
    for r in picked:
        head = "%s年%s %s（约 %s）" % (
            r.get("year_ganzhi") or r.get("year") or "",
            "、".join(m + "月" for m in (r.get("months") or [])),
            r.get("ganzhi") or "—", r.get("range") or "—")
        lines.append(head)
        lines.append(r.get("content") or "")
        lines.append("")
    with io.open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(lines))


# --------------------------------------------------------------------------
# 缓存与手写覆写
# --------------------------------------------------------------------------
def load_cache():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("records", [])
    except Exception:
        return []


def get_import_date():
    """返回行事历的导入日期（YYYY-MM-DD），未导入则为空串。"""
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("imported_at", "")
    except Exception:
        return ""


def save_cache(records, source=""):
    try:
        payload = {
            "source": source,
            "imported_at": date.today().isoformat(),
            "records": records,
        }
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def record_end_date(rec: dict):
    """解析记录 range（如 10.8-11.6）的结束日期，返回『结束日期：11月6日』。"""
    rng = (rec or {}).get("range", "") or ""
    m = re.search(r"[-–—～]\s*([\d.]+)$", rng)
    if not m:
        return ""
    tail = m.group(1).strip()
    parts = tail.split(".")
    try:
        if len(parts) >= 2:
            mon, day = int(parts[0]), int(parts[1])
        else:
            mon, day = int(parts[0]), 0
    except ValueError:
        return ""
    if day:
        return "%d月%d日" % (mon, day)
    return "%d月" % mon


def load_overrides() -> dict:
    """读取手写覆写（agenda_edit.json）。"""
    try:
        with open(EDIT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_override(scope: str, key: str) -> str:
    return str(load_overrides().get(scope, {}).get(key, "") or "")


def save_override(scope: str, key: str, text: str) -> None:
    data = load_overrides()
    data.setdefault(scope, {})
    if (text or "").strip():
        data[scope][key] = text
    else:
        data[scope].pop(key, None)
    try:
        with open(EDIT_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def current_lunar_month_key(d: date = None) -> str:
    """当前农历月别名（正/二/…/十/冬/腊），用于匹配行事历。"""
    from calendar_app.engine import get_day_info
    info = get_day_info(d or date.today())
    m = info["lunar_month_plain"]
    return LUNAR_MONTH_ALIAS.get(m, m)


def match_current_month(records: list, d: date = None):
    """匹配当前农历月的行事历记录。"""
    if not records:
        return None
    from calendar_app.engine import get_day_info
    info = get_day_info(d or date.today())
    key = LUNAR_MONTH_ALIAS.get(info["lunar_month_plain"], info["lunar_month_plain"])
    year_gz = info["lunar_year_cn"]
    for r in records:
        if r.get("year_ganzhi") == year_gz and key in (r.get("months") or []):
            return r
    for r in records:
        if key in (r.get("months") or []):
            return r
    return None
