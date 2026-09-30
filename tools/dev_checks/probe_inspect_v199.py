# -*- coding: utf-8 -*-
"""v1.9.9 真机探针：页底留白 / 版权行与边框 5px / 叠页横带已删除。

用户三项反馈（2026-09-30）：
  ① 版权信息 与 边框 之间间隔 5px，避免重叠；
  ② 框外条区域那条浅灰横带（原 _paint_stack 叠页装饰）删除；
  ③ 「（双击按钮 打开/关闭 对应面板）」提示行下方留白过大。

断言全部基于**真实平台渲染**（非 offscreen），逐像素量墨迹/色带。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

os.environ.pop("QT_QPA_PLATFORM", None)          # 必须真实平台（同 font_weight_probe）

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from PySide6.QtGui import QImage  # noqa: E402

OK = []


def ck(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s%s" % ("OK" if cond else "NO", name, ("  " + detail) if detail else ""))


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    from ui.page import CalendarPage
    from ui.theme import PAPER

    pg = CalendarPage()
    pg.repaint()
    img = pg.grab().toImage()
    W, H = img.width(), img.height()
    print("platform = %s · page = %dx%d · PAPER=%s" % (
        app.platformName(), W, H, PAPER.name()))

    # ---- ① 页高与边框下沿 ----
    ck("页高收紧到 838（原 848）", (W, H) == (520, 838), "%dx%d" % (W, H))
    ck("外框下沿 = FRAME_OUT_BOTTOM(%d)" % CalendarPage.FRAME_OUT_BOTTOM,
       CalendarPage.FRAME_OUT_BOTTOM == 789)

    # ---- ① 版权行墨迹底 与 内框线 间隔 ≥5px ----
    def ink_rows(x0, x1, y0, y1):
        """只认**中性灰**墨迹（版权行 #7a7a6e：R≈G≈B），排除绿色框线（G≫R）。"""
        rows = []
        for y in range(y0, y1):
            n = 0
            for x in range(x0, x1):
                c = img.pixelColor(x, y)
                rgb = sorted((c.red(), c.green(), c.blue()))
                if sum(rgb) / 3.0 < 190 and (rgb[2] - rgb[0]) < 25:
                    n += 1
            if n >= 3:
                rows.append(y)
        return rows
    cop = ink_rows(40, 480, 755, 795)
    ck("版权行墨迹位于 762..780", bool(cop) and cop[0] >= 762 and cop[-1] <= 780,
       "墨迹 y %s..%s" % (cop[0] if cop else "-", cop[-1] if cop else "-"))
    # 框线：取左侧空白列 x=45（版权行文字居中，此处无字）逐行找绿色
    from ui.theme import palette_for
    main = palette_for(pg.info)["main"]
    lines = [y for y in range(770, 800)
             if (lambda c: c.green() > c.red() + 20 and c.green() > 90)(img.pixelColor(45, y))]
    inner = lines[0] if lines else None
    gap = (inner - cop[-1]) if (inner and cop) else -1
    ck("版权行墨迹底 到 内框线 间隔 ≥5px（不再重叠）", gap >= 5,
       "墨迹底 %s → 内框 %s，间隔 %dpx（绿线行 %s）" % (cop[-1] if cop else "-", inner, gap, lines))

    # ---- ② 叠页浅灰横带（#eeebe0 = 238,235,224）已消失 ----
    worst = (0, -1)
    for y in range(782, 838):
        n = 0
        for x in range(12, 508):
            c = img.pixelColor(x, y)
            if abs(c.red() - 238) <= 1 and abs(c.green() - 235) <= 1 and abs(c.blue() - 224) <= 1:
                n += 1
        if n > worst[0]:
            worst = (n, y)
    ck("框外条区域已无 #eeebe0 满宽横带（叠页装饰已删）", worst[0] < 50,
       "最大同色行长 = %d px @ y=%d" % worst)

    # ---- ③ 提示行下方的页底留白 ----
    TAB_Y, TAB_H = CalendarPage.TAB_Y, CalendarPage.TAB_H
    hint_bottom = TAB_Y + TAB_H + 2 + 12
    ck("页底留白 ≤6px（提示行底 %d → 页底 %d）" % (hint_bottom, H),
       H - hint_bottom <= 6, "留白 %dpx（原 848 时为 22px）" % (H - hint_bottom))
    ck("框外条 TAB_Y 随外框下移到 793", TAB_Y == 793, "TAB_Y=%d" % TAB_Y)

    print("\n==== v1.9.9 探针结果: %s ====" % ("全部通过" if all(OK) else "存在失败"))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
