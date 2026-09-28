# -*- coding: utf-8 -*-
"""次级对话框：祭拜三清（SanqingDialog）· 八字录入（BaziDialog）。"""
from PySide6.QtCore import QRect, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QComboBox, QDialog, QGridLayout,
                               QWidget,
                               QHBoxLayout, QLabel, QMessageBox, QPushButton,
                               QSpinBox, QVBoxLayout)

from calendar_app.engine import compute_eightchar

from ui.theme import _font, IMG_XIANGLU, IMG_ZUSHIYE, ZH_FONT


class SanqingDialog(QDialog):
    """祭拜三清（参考《钦天监》祖师爷圣像 · 上香彩蛋）。

    三清道祖 ＝ 玉清元始天尊 · 上清灵宝天尊 · 太清道德天尊。
    纯传统民俗体验，不涉任何网络与数据上报。
    """

    DEITIES = [("玉清", "元始天尊"), ("上清", "灵宝天尊"), ("太清", "道德天尊")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("祭 拜 三 清")
        self.setFixedSize(380, 600)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QDialog{background:#1c1712;}")
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        title = QLabel("祭 拜 三 清")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color:#e8c87a;font-size:22px;font-weight:bold;background:transparent;")
        root.addWidget(title)

        sub = QLabel("三清道祖 ＝ 玉清元始天尊 · 上清灵宝天尊 · 太清道德天尊")
        sub.setAlignment(Qt.AlignCenter)
        sub.setWordWrap(True)
        sub.setStyleSheet("color:#b9a06a;font-size:11px;background:transparent;")
        root.addWidget(sub)

        # 三清圣像（素材祖师爷.png；缺失时回退自绘牌位）
        self._img_zushiye = QPixmap(IMG_ZUSHIYE)
        if not self._img_zushiye.isNull():
            self._img_zushiye = self._img_zushiye.scaled(
                324, 234, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            lb_img = QLabel()
            lb_img.setPixmap(self._img_zushiye)
            lb_img.setAlignment(Qt.AlignCenter)
            lb_img.setStyleSheet("background:transparent;")
            self._seat = None
            root.addWidget(lb_img)
        else:
            seat = QWidget()
            seat.setMinimumHeight(170)
            seat.setStyleSheet("background:transparent;")
            seat.paintEvent = self._paint_seat
            self._seat = seat
            root.addWidget(seat)

        # 香炉（素材香炉.png 整尊绘制，叠加三炷香与烟；缺失时回退自绘）
        self._img_xianglu = QPixmap(IMG_XIANGLU)
        if not self._img_xianglu.isNull():
            self._img_xianglu = self._img_xianglu.scaled(
                105, 105, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        burner = QWidget()
        burner.setFixedHeight(200)
        burner.setStyleSheet("background:transparent;")
        burner.paintEvent = self._paint_burner
        self._burner = burner
        root.addWidget(burner)

        self.lb_bless = QLabel("")
        self.lb_bless.setAlignment(Qt.AlignCenter)
        self.lb_bless.setWordWrap(True)
        self.lb_bless.setStyleSheet("color:#e8c87a;font-size:13px;background:transparent;")
        root.addWidget(self.lb_bless)

        self.btn_incense = QPushButton("敬 香")
        self.btn_incense.setFixedSize(120, 34)
        self.btn_incense.setStyleSheet(
            "QPushButton{background:#7a5a2a;color:#fff;border:none;border-radius:5px;"
            "font-size:14px;} QPushButton:hover{background:#8c6a34;}")
        self.btn_incense.clicked.connect(self._light_incense)
        root.addWidget(self.btn_incense, 0, Qt.AlignCenter)

        note = QLabel("纯传统民俗体验，不涉任何网络与数据上报。")
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color:#7a6f5a;font-size:10px;background:transparent;")
        root.addWidget(note)

        self._smoke = []      # [(x, y, r, alpha)]
        self._incense_on = False

    # ---------- 自绘：三清宝座 ----------
    def _paint_seat(self, ev):
        p = QPainter(self._seat)
        p.setRenderHint(QPainter.Antialiasing)
        w = self._seat.width()
        n = len(self.DEITIES)
        cw = (w - 40) / n
        for i, (pre, name) in enumerate(self.DEITIES):
            x = 20 + i * cw + cw / 2
            p.setPen(QPen(QColor("#e8c87a"), 2))
            p.setBrush(QColor("#2a2118"))
            p.drawRoundedRect(int(x - cw / 2 + 8), 12, int(cw - 16), 150, 6, 6)
            p.setPen(QPen(QColor("#e8c87a")))
            p.setFont(_font(20, ZH_FONT, QFont.Black))
            p.drawText(QRect(int(x - cw / 2 + 8), 30, int(cw - 16), 34),
                       Qt.AlignCenter, pre)
            p.setFont(_font(18, ZH_FONT, QFont.Black))
            p.drawText(QRect(int(x - cw / 2 + 8), 70, int(cw - 16), 80),
                       Qt.AlignCenter | Qt.TextWordWrap, name)
        p.end()

    # ---------- 绘制：香炉素材 + 三炷香 + 烟 ----------
    def _stick_base(self):
        """香脚 y（炉身内部）：素材炉时香先画、炉体后画盖住香脚。"""
        h = self._burner.height()
        if not self._img_xianglu.isNull():
            y0 = h - self._img_xianglu.height()
            return y0 + int(self._img_xianglu.height() * 0.42)
        return h - 34

    def _paint_burner(self, ev):
        p = QPainter(self._burner)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self._burner.width(), self._burner.height()
        cx = w / 2
        has_img = not self._img_xianglu.isNull()
        # 三炷香（先画：炉体随后盖上，香脚藏于炉内；点燃后缓缓燃短）
        if self._incense_on:
            base_y = self._stick_base()
            stick_len = 108 - 80 * self._burn_t
            for dx in (-14, 0, 14):
                sx = int(cx + dx)
                p.setPen(QPen(QColor("#d8c89a"), 3))
                p.drawLine(sx, base_y, sx, int(base_y - stick_len))
                p.setBrush(QColor(220, 60, 30))
                p.setPen(Qt.NoPen)
                p.drawEllipse(sx - 3, int(base_y - stick_len - 3), 6, 6)
        if has_img:
            px = self._img_xianglu
            p.drawPixmap(int(cx - px.width() / 2), h - px.height(), px)
        else:
            # 回退：自绘炉体
            p.setPen(QPen(QColor("#9a7b3a"), 2))
            p.setBrush(QColor("#3a2e1f"))
            p.drawRoundedRect(int(cx - 50), int(h - 40), 100, 34, 8, 8)
            p.setBrush(QColor("#9a7b3a"))
            p.drawRect(int(cx - 54), int(h - 42), 108, 6)
        # 烟（粒子：上升、扩散、变淡）
        for (sx, sy, r, alpha, _vy) in self._smoke:
            p.setBrush(QColor(205, 205, 200, max(0, int(alpha))))
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(sx - r / 2), int(sy - r / 2), int(r), int(r))
        p.end()

    def _stick_tips(self):
        """当前三炷香香头的坐标。"""
        w = self._burner.width()
        cx = w / 2
        stick_len = 108 - 80 * self._burn_t
        base_y = self._stick_base()
        return [(cx + dx, base_y - stick_len) for dx in (-14, 0, 14)]

    # ---------- 敬香 ----------
    def _light_incense(self):
        self._incense_on = True
        self._burn_t = 0.0
        self.lb_bless.setText("")
        self._smoke = []
        if getattr(self, "_fade", None):
            self._fade.stop()
        self.btn_incense.setEnabled(False)
        self._timer = QVariantAnimation(self)
        self._timer.setDuration(21000)   # 燃速为原来的 20%（拉长到 21 秒）
        self._timer.setStartValue(0.0)
        self._timer.setEndValue(1.0)
        self._timer.valueChanged.connect(self._smoke_tick)
        self._timer.finished.connect(self._on_incense_done)
        self._timer.start()

    def _smoke_tick(self, t):
        import random
        self._burn_t = t
        # 既有粒子：上升、扩散、变淡（烟更轻更慢）
        alive = []
        for (sx, sy, r, alpha, vy) in self._smoke:
            sy -= vy
            r += 0.35
            alpha -= 1.6
            if alpha > 5:
                alive.append((sx + random.uniform(-0.7, 0.7), sy, r, alpha, vy))
        self._smoke = alive
        # 香头生成新粒子（出现量与速度下调）
        for (tx, ty) in self._stick_tips():
            if random.random() < 0.22:
                self._smoke.append((tx + random.uniform(-2.0, 2.0), ty - 4,
                                    random.uniform(3.0, 4.5),
                                    random.uniform(90, 130),
                                    random.uniform(0.6, 1.1)))
        self._smoke = self._smoke[-90:]
        self._burner.update()

    def _fade_smoke(self):
        """燃香结束后余烟自然散尽。"""
        import random
        alive = []
        for (sx, sy, r, alpha, vy) in self._smoke:
            sy -= vy
            r += 0.35
            alpha -= 1.6
            if alpha > 5:
                alive.append((sx + random.uniform(-0.7, 0.7), sy, r, alpha, vy))
        self._smoke = alive
        self._burner.update()
        if not self._smoke and getattr(self, "_fade", None):
            self._fade.stop()

    def _on_incense_done(self):
        self._burn_t = 1.0
        self.btn_incense.setEnabled(True)
        blessings = [
            "心香一瓣，三清垂慈；福泽绵长，诸事顺遂。",
            "三清庇佑，灾消福至；身心安宁，百事亨通。",
            "诚心祭拜，感应道交；吉星高照，家宅平安。",
        ]
        import random
        self.lb_bless.setText(random.choice(blessings))
        # 余烟自然散尽（不再瞬间清空）
        self._fade = QTimer(self)
        self._fade.timeout.connect(self._fade_smoke)
        self._fade.start(33)


class BaziDialog(QDialog):
    """个人八字（四柱）录入：公历 / 农历 + 年月日时，实时预览四柱。"""

    def __init__(self, parent=None, input_list=None):
        super().__init__(parent)
        self.setWindowTitle("八字录入 · 个人四柱")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.bazi = None           # compute_eightchar 结果（四柱 + 生肖）
        self.input_list = None     # [年, 月, 日, 时, 农历?] 用于下次回填
        self.cleared = False       # 用户是否点「清除」
        self._build()
        # 回填既有录入
        y, m, d, hh, lunar = (input_list if isinstance(input_list, (list, tuple))
                              and len(input_list) == 5 else [1990, 1, 1, 12, False])
        self.cal_box.setCurrentIndex(1 if lunar else 0)
        self.sb_year.setValue(int(y)); self.sb_month.setValue(int(m))
        self.sb_day.setValue(int(d)); self.sb_hour.setValue(int(hh))
        self._refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(10)

        row_cal = QHBoxLayout()
        row_cal.addWidget(QLabel("历法"))
        self.cal_box = QComboBox()
        self.cal_box.addItems(["公历", "农历"])
        self.cal_box.currentIndexChanged.connect(self._refresh)
        row_cal.addWidget(self.cal_box)
        row_cal.addStretch(1)
        root.addLayout(row_cal)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        def mk_spin(rng, val):
            sb = QSpinBox()
            sb.setRange(*rng)
            sb.setValue(val)
            sb.valueChanged.connect(self._refresh)
            return sb

        grid.addWidget(QLabel("年"), 0, 0, Qt.AlignRight)
        self.sb_year = mk_spin((1900, 2100), 1990)
        grid.addWidget(self.sb_year, 0, 1)
        grid.addWidget(QLabel("月"), 0, 2, Qt.AlignRight)
        self.sb_month = mk_spin((1, 12), 1)
        grid.addWidget(self.sb_month, 0, 3)
        grid.addWidget(QLabel("日"), 1, 0, Qt.AlignRight)
        self.sb_day = mk_spin((1, 31), 1)
        grid.addWidget(self.sb_day, 1, 1)
        grid.addWidget(QLabel("时（24h）"), 1, 2, Qt.AlignRight)
        self.sb_hour = mk_spin((0, 23), 12)
        grid.addWidget(self.sb_hour, 1, 3)
        root.addLayout(grid)

        self.preview = QLabel("")
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet("QLabel{color:#5a5a50;font-size:13px;}")
        root.addWidget(self.preview)

        hb = QHBoxLayout()
        hb.addStretch(1)
        self.btn_clear = QPushButton("清除")
        self.btn_clear.clicked.connect(self._on_clear)
        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("保存")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)
        for b in (self.btn_clear, self.btn_cancel, self.btn_save):
            hb.addWidget(b)
        root.addLayout(hb)

    def _refresh(self):
        lunar = self.cal_box.currentIndex() == 1
        y, m, d, hh = (self.sb_year.value(), self.sb_month.value(),
                      self.sb_day.value(), self.sb_hour.value())
        try:
            res = compute_eightchar(y, m, d, hh, lunar_mode=lunar)
        except Exception:
            self.preview.setText("日期无效，请检查年月日（农历月 / 日范围可能不符）。")
            self.bazi = None
            return
        pillars = res["pillars"]
        sx = res["shengxiao"] or "—"
        self.preview.setText("四柱：%s ｜ 生肖：%s" % (
            " ".join(p or "—" for p in pillars), sx))
        self.bazi = res
        self.input_list = [y, m, d, hh, lunar]

    def _on_save(self):
        self._refresh()
        if not self.bazi:
            QMessageBox.warning(self, "八字录入",
                                "当前日期无法排盘，请检查输入。")
            return
        self.accept()

    def _on_clear(self):
        self.cleared = True
        self.accept()
