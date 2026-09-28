# -*- coding: utf-8 -*-
"""冻结环境（单文件 exe）行事历全链路探针：模板 → 导入 → 区间导出 → 覆写。

用法：
  pyinstaller --onefile --console --paths . --distpath build/_frozen_probe \
              --workpath build/_frozen_work --specpath build/_frozen_work \
              tools/dev_checks/frozen_agenda_probe.py
  build/_frozen_probe/frozen_agenda_probe.exe <输出目录>

退出码 0 = 全部通过。用它验证 openpyxl / pypdf 确实被打进冻结包且可用。
"""
import os
import sys
from datetime import date

OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)

R = []


def ck(name, cond, detail=""):
    R.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (("  :: " + detail) if detail else ""),
          flush=True)


ck("冻结环境：frozen 标记", getattr(sys, "frozen", False) is True,
   "sys.executable=%s" % sys.executable)

try:
    import openpyxl
    ck("openpyxl 已打入冻结包", True, "v%s" % openpyxl.__version__)
except Exception as e:
    ck("openpyxl 已打入冻结包", False, repr(e))
try:
    import pypdf
    ck("pypdf 已打入冻结包", True, "v%s" % pypdf.__version__)
except Exception as e:
    ck("pypdf 已打入冻结包", False, repr(e))
try:
    import reportlab
    ck("reportlab 已打入冻结包", True, "v%s" % reportlab.Version)
except Exception as e:
    ck("reportlab 已打入冻结包", False, repr(e))

try:
    from calendar_app import agenda_pdf as AG
    ok = True
except Exception as e:
    ck("导入 calendar_app.agenda_pdf", False, repr(e))
    sys.exit(1)
ck("导入 calendar_app.agenda_pdf", True)

AG.CACHE_PATH = os.path.join(OUT, "agenda_cache.json")
AG.EDIT_PATH = os.path.join(OUT, "agenda_edit.json")

# 1) Excel 模板 → 导入
xlsx = os.path.join(OUT, "月度行事历模板.xlsx")
AG.make_agenda_template(xlsx, 2026, "丙午年")
ck("冻结：生成 xlsx 模板", os.path.exists(xlsx), "%.1f KB" % (os.path.getsize(xlsx) / 1024))
recs = AG.import_agenda(xlsx)
ck("冻结：导入 xlsx 模板 12 条", len(recs) == 12, "得到 %d" % len(recs))

# 2) PDF 模板 → 导入
pdf = os.path.join(OUT, "月度行事历模板.pdf")
AG.make_agenda_template(pdf, 2026, "丙午年")
rp = AG.import_agenda(pdf)
ck("冻结：导入 PDF 模板 12 条", len(rp) == 12, "得到 %d" % len(rp))

# 3) 区间导出（三种格式）
d1, d2 = date(2026, 10, 1), date(2026, 12, 31)
for ext in (".xlsx", ".csv", ".txt"):
    p = os.path.join(OUT, "export%s" % ext)
    try:
        n = AG.export_agenda(recs, d1, d2, p)
        ck("冻结：导出 %s" % ext, os.path.getsize(p) > 50 and n == 4, "%d 条" % n)
    except Exception as e:
        ck("冻结：导出 %s" % ext, False, repr(e))

# 4) 覆写层
AG.save_override("month", "丙午年|九", "冻结环境手写")
ck("冻结：覆写读写", AG.get_override("month", "丙午年|九") == "冻结环境手写")

failed = [n for n, c, _ in R if not c]
print("\n==== 冻结环境行事历探针 ==== total=%d passed=%d failed=%d"
      % (len(R), sum(1 for _, c, _ in R if c), len(failed)), flush=True)
sys.exit(1 if failed else 0)
