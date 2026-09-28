# -*- coding: utf-8 -*-
"""行事历面板与导入 / 导出对话框（AgendaPanel · AgendaImport/ExportDialog）。"""
import os

from PySide6.QtCore import QDate, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDateEdit, QDialog, QFileDialog,
                               QHBoxLayout, QLabel, QPushButton,
                               QPlainTextEdit, QVBoxLayout, QWidget)

from calendar_app.agenda_pdf import (export_agenda, get_import_date,
                                     get_override, import_agenda, load_cache,
                                     make_agenda_template, match_current_month,
                                     record_end_date, save_override)
from ui.theme import (_font, _tone_of, palette_for, PAPER, PAPER_EDGE,
                      ZH_FONT, ZH_SONG)


class AgendaPanel(QWidget):
    """行事历重点面板：mode='month' 本月行事历重点 / mode='day' 本日行事历重点。

    右下角内置「编辑 / 保存」：可直接改写面板内容，写入 agenda_edit.json 覆写层——
      · month 按『干支年|农历月』存键（导入新行事历后同月条目仍复用同一份手写内容）；
      · day 按『YYYY-MM-DD』存键（可逐日手写备注）。
    显示时覆写层优先于导入内容。
    """

    PANEL_W, PANEL_H = 520, 178
    BTN_W, BTN_H = 46, 22
    EDIT_RECT = QRect(20, 62, 484, 80)

    def __init__(self, parent=None, mode="month"):
        super().__init__(parent)
        self.mode = mode
        self.setFixedSize(self.PANEL_W, self.PANEL_H)
        self.records = load_cache()
        self.index = -1
        self.theme_info = None   # 由 MainWindow 注入当日 info，实现标题带颜色联动
        self._editing = False
        self._btn_theme = None
        self._editor_key = None
        self._last_main = QColor("#1f9c3d")
        self._match_current()
        self._build_editor()

    # ---------- 内嵌正文 / 编辑控件 ----------
    def _build_editor(self):
        # 正文改用常驻 QPlainTextEdit：文字过多时出**主题色细滚动条**，可滚轮翻看
        # （用户 2026-09-28 反馈「文字过多的时候显示会不全」）；只读态透明背景，
        # 观感与旧版纸面印刷一致；「编辑」时解除只读。
        self.editor = QPlainTextEdit(self)
        self.editor.setGeometry(self.EDIT_RECT)
        self.editor.setFrameShape(QPlainTextEdit.NoFrame)
        self.editor.setReadOnly(True)
        self.editor.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.editor.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.editor.setFont(_font(14, ZH_SONG))
        self.editor.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.editor.setVisible(True)
        self.editor.raise_()
        self._apply_editor_style(self._last_main)   # 首帧前就带上主题色样式
        self._sync_body()
        bw, bh, gap = self.BTN_W, self.BTN_H, 6
        x_save = self.PANEL_W - 6 - bw
        x_edit = x_save - gap - bw
        y = self.PANEL_H - 32
        self.btn_save = QPushButton("保存", self)
        self.btn_save.setGeometry(x_save, y, bw, bh)
        self.btn_edit = QPushButton("编辑", self)
        self.btn_edit.setGeometry(x_edit, y, bw, bh)
        self.btn_save.setEnabled(False)
        self.btn_edit.clicked.connect(self._toggle_edit)
        self.btn_save.clicked.connect(self._save_edit)

    def _apply_theme(self, color):
        """按当日主题色给编辑/保存按钮、正文与滚动条上色（颜色变化时才重建样式）。"""
        name = color.name()
        self._last_main = QColor(color)
        if self._btn_theme != name:
            self._btn_theme = name
            hover = QColor(color).darker(112).name()
            st = ("QPushButton{background:%s;color:#ffffff;border:none;"
                  "border-radius:4px;font-size:11px;font-family:'Microsoft YaHei';}"
                  "QPushButton:hover{background:%s;}"
                  "QPushButton:disabled{background:#c9c5b5;color:#f7f5ec;}" % (name, hover))
            self.btn_edit.setStyleSheet(st)
            self.btn_save.setStyleSheet(st)
        self._apply_editor_style(color)

    def _apply_editor_style(self, color):
        """正文框样式：只读态透明（融入纸面印刷），编辑态纸色底 + 主题色边框；
        滚动条槽透明、滑块用当日主题色（用户要求「滚轴颜色和软件当日颜色保持一致」）；
        正文墨色亦随红 / 绿主题切换（红日深红 #8e1a1a / 绿日墨绿 #136b29，
        用户 2026-09-28 反馈「文字也随软件的颜色在红绿中切换」）。"""
        name = color.name()
        key = (name, self._editing)
        if self._editor_key == key:
            return
        self._editor_key = key
        ink = "#8e1a1a" if _tone_of(color) == "红" else "#136b29"
        bar = ("QScrollBar:vertical{background:transparent;width:8px;margin:0;}"
               "QScrollBar::handle:vertical{background:%s;border-radius:4px;"
               "min-height:22px;}"
               "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
               "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical"
               "{background:transparent;}" % name)
        if self._editing:
            st = ("QPlainTextEdit{background:#fffdf4;border:1px solid %s;"
                  "border-radius:3px;padding:2px;color:#333;}" % name)
        else:
            st = ("QPlainTextEdit{background:transparent;border:none;"
                  "padding:0;color:%s;}" % ink)
        self.editor.setStyleSheet(st + bar)

    def _override_key(self):
        """覆写存储键：day 用日期，month 用『干支年|农历月』。"""
        if self.mode == "day":
            d = (self.theme_info or {}).get("date")
            return d.isoformat() if d else ""
        rec = self.current_record()
        if not rec:
            return ""
        return "%s|%s" % (rec.get("year_ganzhi") or rec.get("year") or "",
                          "、".join(rec.get("months") or []))

    def _body_text(self):
        """面板正文：手写覆写 > 导入内容 > 提示文案。"""
        key = self._override_key()
        if key:
            ov = get_override(self.mode, key)
            if ov:
                return ov
        rec = self.current_record()
        if rec:
            return rec["content"]
        if self.mode == "day":
            return ("尚未导入行事历。点「编辑」可直接手写本日注意事项（按日期保存），"
                    "或导入《月度行事历》后自动匹配。")
        return ("点击上方「导入行事历」选择《月度行事历》表格 / PDF，\n"
                "本面板将按当前农历月自动匹配并重点显示本月注意事项。")

    def _sync_body(self):
        """非编辑态下把正文刷进编辑器（记录切换 / 导入 / 保存后调用）。"""
        if self._editing:
            return
        self.editor.setPlainText(self._body_text())
        sb = self.editor.verticalScrollBar()
        if sb:
            sb.setValue(0)

    def _toggle_edit(self):
        if self._editing:
            self._end_edit()
            return
        self._editing = True
        self.editor.setReadOnly(False)
        self.editor.setPlainText(self._body_text())
        self.editor.raise_()
        self.editor.setFocus()
        self.btn_edit.setText("取消")
        self.btn_save.setEnabled(True)
        self._apply_editor_style(self._last_main)

    def _end_edit(self):
        self._editing = False
        self.editor.setReadOnly(True)
        self._sync_body()
        self.btn_edit.setText("编辑")
        self.btn_save.setEnabled(False)
        self._apply_editor_style(self._last_main)

    def _save_edit(self):
        key = self._override_key()
        if key:
            save_override(self.mode, key, self.editor.toPlainText())
        self._end_edit()
        self.update()

    def _match_current(self):
        d = (self.theme_info or {}).get("date")
        r = match_current_month(self.records, d)
        if r:
            self.index = self.records.index(r)
        elif self.records:
            self.index = 0

    def refresh_current(self):
        self._match_current()
        self._sync_body()
        self.update()

    def import_pdf(self, path):
        self.records = import_agenda(path)
        self._match_current()
        self._sync_body()
        self.update()
        return len(self.records)

    def step(self, delta):
        if not self.records:
            return
        self.index = (self.index + delta) % len(self.records)
        self._sync_body()
        self.update()

    def current_record(self):
        if self.records and 0 <= self.index < len(self.records):
            return self.records[self.index]
        return None

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        main = palette_for(self.theme_info or {})["main"]
        self._apply_theme(main)
        p.setPen(QPen(PAPER_EDGE, 1))
        p.setBrush(PAPER)
        p.drawRoundedRect(QRectF(4, 2, self.PANEL_W - 8, self.PANEL_H - 10), 6, 6)
        p.setBrush(main)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(4, 2, self.PANEL_W - 8, 38), 6, 6)
        p.drawRect(QRectF(4, 24, self.PANEL_W - 8, 16))
        p.setFont(_font(18, ZH_FONT, QFont.Black))
        p.setPen(QPen(QColor("#ffffff")))
        title = "本月行事历重点" if self.mode == "month" else "本日行事历重点"
        p.drawText(QRect(20, 4, 320, 34), Qt.AlignLeft | Qt.AlignVCenter, title)
        p.setFont(_font(12, ZH_FONT))
        rec = self.current_record()
        # 副标题行：本月/本日 对应农历月 + 导入日期 + 结束日期
        if self.mode == "month":
            if rec:
                sub = "%s年%s %s（约 %s）" % (
                    rec["year_ganzhi"] or rec["year"],
                    "、".join(m + "月" for m in rec["months"]),
                    rec["ganzhi"], rec["range"])
            else:
                sub = "未导入行事历"
        else:
            info = self.theme_info or {}
            solar = info.get("date")
            sub = "%s（%s%s%s）" % (
                solar.strftime("%Y-%m-%d") if solar else "—",
                info.get("lunar_year_cn", ""), info.get("lunar_month_cn", ""),
                info.get("lunar_day_cn", ""))
        p.drawText(QRect(150, 8, 350, 28), Qt.AlignRight | Qt.AlignVCenter, sub)

        # 导入日期 / 结束日期（两面板均展示）
        p.setFont(_font(11, ZH_FONT))
        p.setPen(QPen(QColor("#7a7a6e")))
        import_d = get_import_date()
        end_d = record_end_date(rec) if rec else ""
        meta = "导入日期：%s   结束日期：%s" % (import_d or "—", end_d or "—")
        p.drawText(QRect(20, 44, self.PANEL_W - 40, 17),
                   Qt.AlignLeft | Qt.AlignVCenter, meta)

        # 正文不再 paintEvent 直绘：由常驻 editor（只读透明）承载，超长出主题色滚动条
        p.setFont(_font(11, ZH_FONT))
        p.setPen(QPen(QColor("#7a7a6e")))
        total = len(self.records)
        cur = (self.index + 1) if total else 0
        p.drawText(QRect(20, self.PANEL_H - 30, 330, 16),
                   Qt.AlignLeft | Qt.AlignVCenter,
                   "共 %d 条 · 第 %d 条" % (total, cur))
        if self._override_key() and get_override(self.mode, self._override_key()):
            # 「已手工修改」标记放在「编辑」按钮左侧同行（用户 2026-09-28 反馈）
            p.drawText(QRect(0, self.PANEL_H - 32, self.btn_edit.geometry().left() - 8,
                             self.BTN_H),
                       Qt.AlignRight | Qt.AlignVCenter, "✎ 本条内容已手工修改")
        p.end()


class AgendaImportDialog(QDialog):
    """行事历数据：下载表格模板 / 导入（Excel·CSV·PDF·Word）/ 按区间导出。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("行事历 · 导入 / 导出")
        self.setFixedWidth(470)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        tip = QLabel(
            "「本月 / 本日行事历重点」数据来自《月度行事历》：<br>"
            "1. 点「下载行事历模板」得到 <b>Excel 表格模板</b>（也可选 PDF），"
            "每行一个农历月填写要点；<br>"
            "2. 点「导入行事历」选择填好的 <b>Excel / CSV / PDF / Word</b> 文件，"
            "软件<b>内置离线智能解析</b>（无需联网），自动按当前农历月匹配；<br>"
            "3. 点「导出行事历」可按日期区间导出为 Excel / CSV / 文本。")
        tip.setWordWrap(True)
        root.addWidget(tip)

        hb = QHBoxLayout()
        self.btn_template = QPushButton("下载行事历模板")
        self.btn_template.setFixedHeight(32)
        self.btn_pick = QPushButton("导入行事历")
        self.btn_pick.setFixedHeight(32)
        self.btn_export = QPushButton("导出行事历")
        self.btn_export.setFixedHeight(32)
        for b in (self.btn_template, self.btn_pick, self.btn_export):
            hb.addWidget(b)
        root.addLayout(hb)

        self.lb_result = QLabel("")
        self.lb_result.setWordWrap(True)
        self.lb_result.setStyleSheet("color:#555;")
        root.addWidget(self.lb_result)

        close = QPushButton("关闭")
        close.setFixedWidth(80)
        close.clicked.connect(self.accept)
        hb2 = QHBoxLayout()
        hb2.addStretch(1)
        hb2.addWidget(close)
        root.addLayout(hb2)

        self.btn_template.clicked.connect(self._download_template)
        self.btn_pick.clicked.connect(self._pick_file)
        self.btn_export.clicked.connect(self._export)
        self.imported = False

    def _download_template(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存行事历模板",
            os.path.join(os.path.expanduser("~"), "Desktop", "月度行事历模板.xlsx"),
            "Excel 表格 (*.xlsx);;PDF 文件 (*.pdf)")
        if not path:
            return
        try:
            make_agenda_template(path)
            self.lb_result.setText("✔ 模板已保存：%s" % path)
        except Exception as e:
            self.lb_result.setText("✘ 模板生成失败：%s" % e)

    def _pick_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择月度行事历文件（Excel / CSV / PDF / Word）",
            os.path.expanduser("~"),
            "行事历文件 (*.xlsx *.csv *.pdf *.docx *.txt);;"
            "Excel 表格 (*.xlsx);;CSV (*.csv);;PDF 文件 (*.pdf);;"
            "Word 文件 (*.docx)")
        if not path:
            return
        try:
            records = import_agenda(path)
            n = len(records)
            self.lb_result.setText("✔ 已解析 %d 条农历月行事历，关闭后自动定位当前农历月。" % n)
            self.imported = True
        except Exception as e:
            self.lb_result.setText("✘ 导入失败：%s" % e)

    def _export(self):
        dlg = AgendaExportDialog(self)
        dlg.exec()


class AgendaExportDialog(QDialog):
    """导出行事历：选日期区间 → 导出该区间内有交集的条目为 Excel / CSV / 文本。"""

    FMTS = [("Excel 表格 (*.xlsx)", ".xlsx"), ("CSV (*.csv)", ".csv"),
            ("文本文件 (*.txt)", ".txt")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出行事历")
        self.setFixedWidth(430)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        tip = QLabel("选择日期区间，导出区间内（与条目公历区间有交集）的行事历重点。"
                     "数据来自已导入的行事历。")
        tip.setWordWrap(True)
        root.addWidget(tip)

        hb = QHBoxLayout()
        today = QDate.currentDate()
        self.date_from = QDateEdit(today)
        self.date_to = QDateEdit(today.addMonths(1))
        for w in (self.date_from, self.date_to):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            w.setFixedHeight(28)
        self.cmb = QComboBox()
        for label, _ext in self.FMTS:
            self.cmb.addItem(label)
        self.cmb.setFixedHeight(28)
        hb.addWidget(QLabel("从"))
        hb.addWidget(self.date_from)
        hb.addWidget(QLabel("到"))
        hb.addWidget(self.date_to)
        hb.addWidget(self.cmb)
        root.addLayout(hb)

        self.btn_go = QPushButton("导出…")
        self.btn_go.setFixedHeight(32)
        root.addWidget(self.btn_go)

        self.lb_result = QLabel("")
        self.lb_result.setWordWrap(True)
        self.lb_result.setStyleSheet("color:#555;")
        root.addWidget(self.lb_result)

        close = QPushButton("关闭")
        close.setFixedWidth(80)
        close.clicked.connect(self.accept)
        hb2 = QHBoxLayout()
        hb2.addStretch(1)
        hb2.addWidget(close)
        root.addLayout(hb2)

        self.btn_go.clicked.connect(self._do_export)

    def _do_export(self):
        # PySide6 的 QDate → datetime.date 是 toPython()（PyQt 才叫 toPyDate）
        d1 = self.date_from.date().toPython()
        d2 = self.date_to.date().toPython()
        if d2 < d1:
            d1, d2 = d2, d1
        ext = self.FMTS[self.cmb.currentIndex()][1]
        name = "行事历_%s_%s%s" % (d1.isoformat(), d2.isoformat(), ext)
        path, _ = QFileDialog.getSaveFileName(
            self, "导出行事历",
            os.path.join(os.path.expanduser("~"), "Desktop", name),
            ";;".join(label for label, _e in self.FMTS))
        if not path:
            return
        try:
            n = export_agenda(load_cache(), d1, d2, path)
            self.lb_result.setText("✔ 已导出 %d 条 → %s" % (n, path))
        except Exception as e:
            self.lb_result.setText("✘ 导出失败：%s" % e)
