# -*- coding: utf-8 -*-
"""撕页日历主页自绘控件（CalendarPage）。"""
import os
from datetime import date, datetime

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                           QPen)
from PySide6.QtWidgets import QComboBox, QPushButton, QSlider, QWidget

from calendar_app import fonts as calendar_app_fonts
from calendar_app.engine import get_day_info, SHENGXIAO_LIST
from calendar_app import version as VER

from ui.theme import (COLOR_CHIPS, _font, _lf_asset, _paper_pixmap, _pix_cached,
                      _pix_scaled, _tone_of, palette_for, use_builtin_fonts,
                      EN_FONT, IMG_BAGUA, INK, NUM_FONT, PAPER_EDGE,
                      ZH_FONT, ZH_SONG, ZH_WISDOM, _ZODIAC_DIR)


class CalendarPage(QWidget):
    """纸质撕页日历页面（全部自绘 + 内嵌功能按钮）。"""

    PAGE_W, PAGE_H = 520, 848
    CENTER_DATE_RECT = QRect(56, 108, 404, 192)   # 巨大日期命中区（按 10 次触发祭拜三清）
    TITLE_RECT = QRect(24, 20, 84, 32)            # 「农历日历」标题行：按住拖动窗口
    # 巨大日期数字：主字 / 印影两个绘制框（龙·凤水印与高光均以 NUM_RECT 为基准）
    NUM_FONT_PX = 168
    NUM_RECT = QRect(66, 110, 392, 186)
    NUM_SHADOW_RECT = QRect(72, 116, 392, 186)
    # 数字斜向高光流动参数（左上 → 右下，缓慢、克制）
    SHEEN_PERIOD_MS = 4800        # 一轮扫过时长
    SHEEN_TICK_MS = 33            # ≈30fps
    SHEEN_ALPHA = 68              # 高光峰值透明度（克制，不抢数字本体）
    SHEEN_HALF = 58               # 亮带半宽（沿 45° 轴，越宽越柔）
    SHEEN_S0 = -60.0              # 亮带中心 x+y 起点
    SHEEN_SPAN = 860.0            # 亮带中心 x+y 行程
    SHEEN_RECT = QRect(58, 100, 408, 208)   # 仅刷新数字所在区域，避免整页重绘
    # 龙凤水平贴边：龙墨迹左缘 / 凤墨迹右缘 = 中线 ± LF_INSET（实测 186 时恰顶住数字）
    LF_INSET = 186
    # 底部双击按钮：分别开关 本月 / 本日 行事历面板
    TAB_W, TAB_H = 105, 26
    TAB_Y = PAGE_H - 40
    TAB_MONTH_RECT = QRect(148, TAB_Y, TAB_W, TAB_H)
    TAB_DAY_RECT = QRect(267, TAB_Y, TAB_W, TAB_H)

    month_toggle_requested = Signal()
    day_toggle_requested = Signal()
    date_pressed_ten_times = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        use_builtin_fonts()      # 内置字体已注册则前置（幂等；未注册时用系统字体）
        self.setFixedSize(self.PAGE_W, self.PAGE_H)
        self.info = get_day_info(date.today())
        self.zodiac_report = None
        self._month_visible = True
        self._day_visible = True
        self._date_press_count = 0
        self._win_drag = None    # 标题行拖动窗口用的偏移
        self.setMouseTracking(True)   # 无按键也接收 mouseMove，用于底部手型光标
        self._build_controls()
        # 页顶时钟：定时刷新当前时分
        self._clock = QTimer(self)
        self._clock.setInterval(15000)
        self._clock.timeout.connect(self.update)
        self._clock.start()
        # 巨大数字斜向高光流动：约 30fps，仅刷新数字区域
        self._sheen_t = 0.0
        self._sheen = QTimer(self)
        self._sheen.setInterval(self.SHEEN_TICK_MS)
        self._sheen.timeout.connect(self._tick_sheen)
        self._sheen.start()

    def _tick_sheen(self):
        """推进高光进度并只重绘数字区域（窗口隐藏时不空转）。"""
        if not self.isVisible():
            return
        self._sheen_t += float(self.SHEEN_TICK_MS) / self.SHEEN_PERIOD_MS
        if self._sheen_t >= 1.0:
            self._sheen_t -= 1.0
        self.update(self.SHEEN_RECT)

    # ---------- 内嵌控件 ----------
    def _build_controls(self):
        self.zodiac_box = QComboBox(self)
        self.zodiac_box.addItem("生肖…", None)
        for s in SHENGXIAO_LIST:
            self.zodiac_box.addItem(s, s)

        def btn(text, tip="", width=0):
            b = QPushButton(text, self)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            if width:
                b.setFixedWidth(width)
            return b

        self.btn_prev = btn("◀", "前一日", 26)
        self.btn_next = btn("▶", "后一日", 26)
        self.btn_import = btn("导入行事历", "行事历导入 / 导出（Excel · CSV · PDF · Word）", 105)
        self.btn_tear = btn("撕页", "撕掉当前页，翻到明天", 40)
        self.btn_about = btn("关于本软件", "关于本软件与开机启动设置", 105)
        self.btn_today = btn("今日", "回到当日", 40)
        self.btn_min = btn("—", "最小化", 26)
        self.btn_close = btn("✕", "关闭", 26)
        self.btn_bazi = btn("八字", "录入个人八字（四柱）以强化当日运势推演", 46)
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.setToolTip("调整窗口透明度")

        # 顶栏一行排布（右端窗控按钮锚定内边框右缘，互不重叠）
        y, h = 26, 24
        x = 110
        self.btn_bazi.setGeometry(x, y, 46, h); x += 50      # 八字：文字完整
        self.zodiac_box.setGeometry(x, y, 64, h); x += 68    # 生肖：容下「生肖…」
        self.btn_prev.setGeometry(x, y, 26, h); x += 29
        self.btn_next.setGeometry(x, y, 26, h); x += 30
        self.btn_tear.setGeometry(x, y, 40, h); x += 43
        self.btn_today.setGeometry(x, y, 40, h)              # 今日止于 370
        self.opacity_slider.setGeometry(373, y, 61, h)       # 透明度滑块 373..434
        self.btn_min.setGeometry(436, y, 24, h)
        self.btn_close.setGeometry(464, y, 24, h)
        # 底部一行：四按钮平均分布（关于本软件 置于左侧）
        self.btn_about.setGeometry(29, self.TAB_Y, 105, self.TAB_H)
        self.btn_import.setGeometry(386, self.TAB_Y, 105, self.TAB_H)
        self._theme_controls()

    def _theme_controls(self):
        p = palette_for(self.info)
        main, dark = p["main"].name(), p["dark"].name()
        style = (
            "QPushButton{background:rgba(255,255,255,0);color:%s;"
            "border:1px solid %s;border-radius:3px;padding:1px 6px;"
            "font-size:12px;font-family:%s;}"
            "QPushButton:hover{background:rgba(0,0,0,0.06);}"
            "QPushButton:pressed{background:rgba(0,0,0,0.14);}"
            % (dark, main, calendar_app_fonts.sans_css()))
        for b in (self.btn_prev, self.btn_next, self.btn_import,
                  self.btn_tear, self.btn_about, self.btn_today, self.btn_min,
                  self.btn_bazi):
            b.setStyleSheet(style)
        self.btn_close.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0);color:%s;"
            "border:1px solid %s;border-radius:3px;padding:1px 6px;"
            "font-size:12px;font-family:%s;}"
            "QPushButton:hover{background:%s;color:#fff;}"
            % (main, main, calendar_app_fonts.sans_css(), main))
        self.zodiac_box.setStyleSheet(
            "QComboBox{background:rgba(255,255,255,0);color:%s;"
            "border:1px solid %s;border-radius:3px;padding:1px 6px;"
            "font-size:12px;font-family:%s;}"
            "QComboBox::drop-down{border:none;width:14px;}"
            "QComboBox QAbstractItemView{background:#faf8f0;color:%s;"
            "border:1px solid %s;selection-background-color:#eeeeee;}"
            % (dark, main, calendar_app_fonts.sans_css(), dark, main))
        self.opacity_slider.setStyleSheet(
            "QSlider{background:rgba(255,255,255,0);}"
            "QSlider::groove:horizontal{border:1px solid %s;height:4px;"
            "border-radius:2px;background:rgba(0,0,0,0.08);}"
            "QSlider::sub-page:horizontal{background:%s;border-radius:2px;}"
            "QSlider::handle:horizontal{width:10px;height:16px;margin:-7px 0;"
            "border-radius:5px;background:%s;}"
            "QSlider::add-page:horizontal{background:rgba(0,0,0,0.08);}"
            % (main, main, dark))

    # ---------- 数据 ----------
    def set_date(self, d: date):
        self.info = get_day_info(d)
        self._theme_controls()
        self.update()

    def set_zodiac_report(self, rep: dict):
        self.zodiac_report = rep
        self.update()

    def set_panels_visible(self, month: bool, day: bool):
        self._month_visible = month
        self._day_visible = day
        self.update()

    # ---------- 点击区：中间日期 10 连击 / 标题行拖动窗口 / 底部按钮双击开关面板 ----------
    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return super().mousePressEvent(ev)
        pos = ev.position()
        # 「农历日历」标题行：按住拖动窗口位置
        if self.TITLE_RECT.contains(int(pos.x()), int(pos.y())):
            w = self.window()
            self._win_drag = ev.globalPosition().toPoint() - w.frameGeometry().topLeft()
            return
        # 巨大日期命中区：累计 10 次触发「祭拜三清」
        if self.CENTER_DATE_RECT.contains(int(pos.x()), int(pos.y())):
            self._date_press_count += 1
            if self._date_press_count >= 10:
                self._date_press_count = 0
                self.date_pressed_ten_times.emit()
            return
        super().mousePressEvent(ev)

    def mouseDoubleClickEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            pos = ev.position()
            if self.TAB_MONTH_RECT.contains(int(pos.x()), int(pos.y())):
                self.month_toggle_requested.emit()
                return
            if self.TAB_DAY_RECT.contains(int(pos.x()), int(pos.y())):
                self.day_toggle_requested.emit()
                return
        super().mouseDoubleClickEvent(ev)

    def mouseMoveEvent(self, ev):
        # 标题行拖动中：跟随鼠标移动窗口
        if self._win_drag is not None and (ev.buttons() & Qt.LeftButton):
            w = self.window()
            w.move(ev.globalPosition().toPoint() - self._win_drag)
            return
        pos = ev.position()
        hand = (self.TAB_MONTH_RECT.contains(int(pos.x()), int(pos.y())) or
                self.TAB_DAY_RECT.contains(int(pos.x()), int(pos.y())) or
                self.CENTER_DATE_RECT.contains(int(pos.x()), int(pos.y())) or
                self.TITLE_RECT.contains(int(pos.x()), int(pos.y())))
        self.setCursor(Qt.PointingHandCursor if hand else Qt.ArrowCursor)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._win_drag = None
        super().mouseReleaseEvent(ev)

    def leaveEvent(self, ev):
        self.unsetCursor()
        super().leaveEvent(ev)

    # ---------- 绘制 ----------
    def paintEvent(self, ev):
        self.P = palette_for(self.info)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        self._paint_paper(p)
        self._paint_stack(p)
        self._paint_border(p)
        self._paint_dragon_phoenix(p)
        self._paint_header(p)
        self._paint_big_day(p)
        self._paint_cloud(p)
        self._paint_middle_band(p)
        self._paint_yiji(p)
        self._paint_fortune(p)
        self._paint_zodiac(p)
        self._paint_hours_colors(p)
        self._paint_advice(p)
        self._paint_zodiac_watermark(p)
        self._paint_footer(p)
        p.end()

    def _paint_paper(self, p):
        # 纸面底纹（纸色 + 顶部微光渐变）已缓存为位图，每帧一次 blit
        p.drawPixmap(0, 0, _paper_pixmap(self.PAGE_W, self.PAGE_H))
        # 页顶标题（自绘，避免子控件样式继承问题）
        p.setFont(_font(14, ZH_FONT, QFont.Black))
        p.setPen(QPen(self.P["dark"]))
        p.drawText(QRect(30, 26, 80, 24), Qt.AlignVCenter | Qt.AlignLeft,
                   VER.APP_NAME)

    def _paint_stack(self, p):
        """底部叠页，模拟一沓待撕的日历纸。"""
        for i in range(1, 5):
            p.setPen(QPen(PAPER_EDGE, 1))
            p.setBrush(QColor("#f3f0e6" if i % 2 else "#eeebe0"))
            p.drawRect(10 + i, self.PAGE_H - 28 - i * 2 - 10,
                       self.PAGE_W - 20 - i * 2, 10 + i * 2)

    def _paint_border(self, p):
        main = self.P["main"]
        p.setPen(QPen(main, 3))
        p.setBrush(Qt.NoBrush)
        p.drawRect(14, 14, self.PAGE_W - 28, self.PAGE_H - 60)
        p.setPen(QPen(main, 1))
        p.drawRect(21, 21, self.PAGE_W - 42, self.PAGE_H - 73)
        p.setBrush(main)
        # 圆点圆心必须恰好落在外框四个顶点上（外框 14,14,~ 起画）：
        # 右缘此前写成 PAGE_W-20，偏离顶点 6px（用户 2026-09-28 反馈）
        for cx, cy in [(14, 14), (self.PAGE_W - 14, 14), (14, self.PAGE_H - 46),
                       (self.PAGE_W - 14, self.PAGE_H - 46)]:
            p.drawEllipse(QPoint(cx, cy), 4, 4)

    def _paint_dragon_phoenix(self, p):
        """日期两侧：左龙右凤剪纸水印（随主题红绿取图，40% 透明度，绘于文字之下）。

        垂直方向与巨大数字框（NUM_RECT）**居中对齐**；水平方向贴边——
        龙墨迹左缘 / 凤墨迹右缘落在中线 ±LF_INSET，恰好顶住大数字两侧，
        与箴 / 谶竖排列之间不再留空带（用户 2026-09-28 反馈「两边不用留白留空」）。
        """
        tone = _tone_of(self.P["main"])
        h = 168
        y = self.NUM_RECT.y() + self.NUM_RECT.height() // 2 - h // 2
        cx = self.PAGE_W // 2
        for name, right in (("龙", False), ("凤", True)):
            path = _lf_asset(name, tone)
            src = _pix_cached(path)
            if src.isNull():
                continue
            w = int(src.width() * h / src.height())
            x = (cx + self.LF_INSET - w) if right else (cx - self.LF_INSET)
            p.save()
            p.setOpacity(0.40)
            p.drawPixmap(x, y, w, h, _pix_scaled(path, w, h))
            p.restore()

    def _paint_cloud(self, p):
        """「X日 · 属X」两侧云纹（随主题红绿取图）。"""
        path = _lf_asset("云纹", _tone_of(self.P["main"]))
        w, h = 156, 15
        pm = _pix_scaled(path, w, h)
        if pm.isNull():
            return
        p.drawPixmap(22, 300, w, h, pm)              # 左
        p.drawPixmap(self.PAGE_W - 22 - w, 300, w, h, pm)   # 右

    def _paint_header(self, p):
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        # 左：英文月份（无框直印）
        p.setPen(QPen(dark))
        month = info["month_en"]
        msize = 26 if len(month) <= 6 else 20
        p.setFont(_font(msize, EN_FONT, QFont.Black, italic=True))
        p.drawText(QRect(34, 52, 196, 46), Qt.AlignVCenter | Qt.AlignLeft, month)
        # 中：年份（无框直印，全软件居中）
        p.setFont(_font(36, NUM_FONT, QFont.Black))
        p.setPen(QPen(main))
        p.drawText(QRect(0, 52, self.PAGE_W, 46), Qt.AlignCenter,
                   str(info["date"].year))
        # 右：公历月大小（无框直印）
        p.setFont(_font(23, ZH_FONT, QFont.Black))
        import calendar as _cal
        days = _cal.monthrange(info["date"].year, info["date"].month)[1]
        p.drawText(QRect(330, 52, 110, 46), Qt.AlignCenter,
                   "%d月%s" % (info["date"].month, "大" if days >= 30 else "小"))
        # 右端：当前时分（实时刷新）
        now = datetime.now()
        p.setFont(_font(20, NUM_FONT, QFont.Black))
        p.setPen(QPen(main))
        p.drawText(QRect(420, 60, 84, 34), Qt.AlignCenter,
                   "%02d:%02d" % (now.hour, now.minute))
        # 副行：左农历干支年 / 右节气或假日
        p.setFont(_font(13, ZH_FONT))
        p.setPen(QPen(dark))
        left = "%s年 · %s" % (info["lunar_year_cn"], info["lunar_year_shengxiao"])
        right = "节气 %s" % info["jieqi"]
        if info["holiday"]:
            right = "法定假日 · %s" % info["holiday"]
        p.drawText(QRect(34, 100, 210, 18), Qt.AlignLeft | Qt.AlignVCenter, left)
        p.drawText(QRect(276, 100, 210, 18), Qt.AlignRight | Qt.AlignVCenter, right)

    def _paint_big_day(self, p):
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        # 左右竖排：箴言（左）/ 谶言（右），无框直印
        # 箴/谶 标题在双列块顶部水平居中；正文两列、自左向右读，字号锁定 18
        wis = info.get("wisdom") or {}
        for cols, tag, text in [((38, 62), "箴", wis.get("zhenyan", "")),
                                ((456, 480), "谶", wis.get("chenyan", ""))]:
            chars = [c for c in text if c not in "，。；、！？— "][:10]
            y0 = 134
            bx = (cols[0] + cols[1]) // 2   # 双列块中心
            p.setFont(_font(24, ZH_FONT, QFont.Black))
            p.setPen(QPen(dark))
            p.drawText(QRect(bx - 14, y0, 28, 30), Qt.AlignCenter, tag)
            p.setFont(_font(18, ZH_WISDOM, QFont.DemiBold))
            p.setPen(QPen(main))
            for i, ch in enumerate(chars):
                col, row = i // 5, i % 5
                p.drawText(QRect(cols[col] - 12, y0 + 34 + row * 22,
                                 24, 22), Qt.AlignCenter, ch)
        # 巨大数字（印影 + 主印）
        p.setFont(_font(self.NUM_FONT_PX, NUM_FONT, QFont.Black))
        p.setPen(QPen(QColor(main.red(), main.green(), main.blue(), 60)))
        p.drawText(self.NUM_SHADOW_RECT, Qt.AlignCenter, str(info["date"].day))
        p.setPen(QPen(main))
        p.drawText(self.NUM_RECT, Qt.AlignCenter, str(info["date"].day))
        # 数字斜向高光流动（左上 → 右下，缓慢克制；绘于主印之上、仅落在字形内）
        self._paint_sheen(p, str(info["date"].day))
        # 数字下：日干支（全软件居中）
        p.setFont(_font(17, ZH_FONT, QFont.Black))
        p.setPen(QPen(dark))
        p.drawText(QRect(0, 296, self.PAGE_W, 24), Qt.AlignCenter,
                   "%s日 · 属%s" % (info["day_ganzhi"], info["day_shengxiao"]))

    def _paint_sheen(self, p, text):
        """巨大数字上的斜向高光：一条 45° 亮带沿字形自左上扫向右下。

        实现取巧处：**用渐变画刷重绘同一段文字** —— 渐变只在字形内部着色，
        天然被字形轮廓裁切，无需手工构造字形路径，也无需逐帧生成遮罩位图。
        亮带沿 (1,1) 方向推进，其等值线垂直于推进方向，故视觉上是斜向流光。
        """
        s_c = self.SHEEN_S0 + self._sheen_t * self.SHEEN_SPAN      # 亮带中心 x+y
        g = QLinearGradient(-100.0, -100.0, 500.0, 500.0)         # 轴沿 45°
        length = 1200.0         # 覆盖 x+y ∈ [-200, 1000]，亮带全程不会被夹断
        for s_off, alpha in ((-260.0, 0), (s_c - self.SHEEN_HALF, 0),
                             (s_c, self.SHEEN_ALPHA),
                             (s_c + self.SHEEN_HALF, 0), (1000.0, 0)):
            u = (s_off + 200.0) / length
            g.setColorAt(min(1.0, max(0.0, u)), QColor(255, 255, 255, alpha))
        p.save()
        p.setFont(_font(self.NUM_FONT_PX, NUM_FONT, QFont.Black))
        p.setPen(QPen(QBrush(g), 1))
        p.drawText(self.NUM_RECT, Qt.AlignCenter, text)
        p.restore()

    def _paint_middle_band(self, p):
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        y, h = 322, 56
        p.setPen(QPen(main, 2))
        p.setBrush(self.P["box_bg"])
        p.drawRect(30, y, 150, h)
        p.setFont(_font(24, ZH_FONT, QFont.Black))
        p.setPen(QPen(dark))
        p.drawText(QRect(30, y + 3, 150, 30), Qt.AlignCenter,
                   "%s日" % info["lunar_day_cn"])
        p.setFont(_font(12, ZH_FONT))
        p.drawText(QRect(30, y + 33, 150, 18), Qt.AlignCenter,
                   "农历%s年%s月%s" % (info["lunar_year_cn"], info["lunar_month_cn"],
                                      info["lunar_month_size"]))
        p.drawRect(186, y, 148, h)
        p.setFont(_font(19, ZH_FONT, QFont.Black))
        jie = info["jieqi"].split("（")[0] if info["jieqi"] else "—"
        p.drawText(QRect(186, y + 3, 148, 28), Qt.AlignCenter, jie)
        p.setFont(_font(12, ZH_FONT))
        p.drawText(QRect(186, y + 33, 148, 18), Qt.AlignCenter,
                   "%s %s · 建除%s日" % (info["tianshen_type"], info["tianshen"],
                                        info["zhixing"]))
        p.drawRect(340, y, 150, h)
        p.setFont(_font(22, ZH_FONT, QFont.Black))
        p.drawText(QRect(340, y + 3, 150, 28), Qt.AlignCenter, info["week_cn"])
        p.setFont(_font(11, EN_FONT, QFont.Bold))
        p.drawText(QRect(340, y + 33, 150, 18), Qt.AlignCenter, info["week_en"])

    @staticmethod
    def _draw_rows(p, rows, rect):
        """把若干行文字在 rect 内**等分排布、逐行居中**，行距与字体解耦。

        不能直接用 drawText 的 "\\n" 换行：Qt 的换行行距取自字体的
        ascent+descent+leading，内置 Noto Serif SC 默认行距约 1.42em
        （14px → 20px），五行需 100px，而中栏可用高仅 86px，
        第 5 行「X命互禄 Y命进禄」会被整行裁掉（v1.8.0 换内置字体后暴露）。
        改为按 rect 高度等分定位后，行距只由 rect 决定，换任何字体都不会缺行。
        """
        n = len(rows)
        if not n:
            return
        step = rect.height() / float(n)
        for i, txt in enumerate(rows):
            slot = QRectF(rect.left(), rect.top() + i * step,
                          rect.width(), step)
            p.drawText(slot, Qt.AlignCenter | Qt.TextDontClip, txt)

    @staticmethod
    def _wrap_px(fm, text, width):
        """按像素宽度手工断行；以「、」为优先断点，标点不落行首。

        Qt 的 TextWordWrap 行距同样取自字体行距、无法收紧，故自行断行后
        逐行定位，行距交由调用方决定。单个条目本身超宽时退化为逐字硬断。
        """
        parts = text.split("、")
        units = [part + ("、" if i < len(parts) - 1 else "")
                 for i, part in enumerate(parts)]
        lines, cur = [], ""
        for unit in units:
            if cur and fm.horizontalAdvance(cur + unit) > width:
                lines.append(cur)
                cur = ""
            if not cur and fm.horizontalAdvance(unit) > width:
                for ch in unit:                     # 单条目超宽：逐字硬断
                    if cur and fm.horizontalAdvance(cur + ch) > width:
                        lines.append(cur)
                        cur = ch
                    else:
                        cur += ch
                continue
            cur += unit
        if cur:
            lines.append(cur)
        return lines

    @staticmethod
    def _draw_para(p, text, rect, max_lines):
        """在 rect 内绘制多行段落：**行距按实际行数自适应**，与字体行距无关。

        v1.8.1：内置 Noto 系字体行距 ≈1.42em（14px → 20px），宜 / 忌文本最多
        需 3 行共 60px，而旧文字区仅 48px，第 3 行会被裁掉（2026-01-06 宜
        「会亲友」实测可见）。改为手工断行 + 自适应行距后 2~3 行均完整显示；
        行数超上限时末行省略号收尾，绝不越界。
        """
        fm = p.fontMetrics()
        lines = CalendarPage._wrap_px(fm, text, rect.width())
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = fm.elidedText(lines[-1] + "…", Qt.ElideRight,
                                      rect.width())
        if not lines:
            return
        step = min(fm.height(), rect.height() / float(len(lines)))
        for i, ln in enumerate(lines):
            p.drawText(QRectF(rect.left(), rect.top() + i * step,
                              rect.width(), step),
                       Qt.AlignLeft | Qt.AlignVCenter | Qt.TextDontClip, ln)

    def _paint_yiji(self, p):
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        y, h = 384, 96
        # 宜框（30..180 与上方「十七日」框对齐）
        p.setPen(QPen(main, 2))
        p.setBrush(self.P["box_bg"])
        p.drawRect(30, y, 150, h)
        p.setBrush(main)
        p.drawEllipse(90, y + 6, 30, 30)          # 圈内水平居中
        p.setFont(_font(18, ZH_FONT, QFont.Black))
        p.setPen(QPen(QColor("#ffffff")))
        p.drawText(QRect(90, y + 6, 30, 30), Qt.AlignCenter, "宜")
        p.setFont(_font(14, ZH_FONT, QFont.DemiBold))
        p.setPen(QPen(dark))
        # 文字区 y+40..y+94（宜/忌圆圈底 y+36 之下、方框底 y+96 之上），
        # 最多 3 行 —— 行距由 _draw_para 按实际行数自适应，不再被字体行距撑破
        self._draw_para(p, "、".join(info["yi"][:6]) or "—",
                        QRect(38, y + 40, 140, 54), 3)
        # 忌框（340..490 与上方「星期日」框对齐）
        p.setBrush(self.P["box_bg"])
        p.drawRect(340, y, 150, h)
        p.setBrush(main)
        p.drawEllipse(400, y + 6, 30, 30)         # 圈内水平居中
        p.setFont(_font(18, ZH_FONT, QFont.Black))
        p.setPen(QPen(QColor("#ffffff")))
        p.drawText(QRect(400, y + 6, 30, 30), Qt.AlignCenter, "忌")
        p.setFont(_font(14, ZH_FONT, QFont.DemiBold))
        p.setPen(QPen(dark))
        self._draw_para(p, "、".join(info["ji"][:6]) or "—",
                        QRect(348, y + 40, 140, 54), 3)
        p.setFont(_font(14, ZH_FONT))
        p.setPen(QPen(dark))
        # 中栏底部：八卦水印（40% 透明，先绘于文字之下）
        bsrc = _pix_cached(IMG_BAGUA)
        if not bsrc.isNull():
            bw = 92
            bh = int(bsrc.height() * bw / bsrc.width())
            p.save()
            p.setOpacity(0.4)
            p.drawPixmap(260 - bw // 2, y + h - bh, bw, bh,
                         _pix_scaled(IMG_BAGUA, bw, bh))
            p.restore()
        rows = ["喜神 %s" % info["pos_xi"], "财神 %s" % info["pos_cai"],
                "福神 %s" % info["pos_fu"], "冲煞 %s" % info["chong"],
                "%s" % info["lu"]]
        # 中栏文字区：左 184 / 右 336（宜框右缘 180 与忌框左缘 340 之间），
        # 高 90（上下各留 3px）——等分 5 行即 18px/行，14px 字宽最宽 134px 可容
        self._draw_rows(p, rows, QRect(184, y + 3, 152, h - 6))

    def _paint_fortune(self, p):
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        y, h = 484, 52
        p.setPen(QPen(main, 2))
        p.setBrush(self.P["stamp_bg"])
        p.drawRect(30, y, 52, h)                       # 吉/平/凶 正方形框
        p.setFont(_font(24, ZH_FONT, QFont.Black))
        p.setPen(QPen(dark))
        p.drawText(QRect(30, y, 52, h), Qt.AlignCenter, info["fortune_grade"])
        p.setFont(_font(22, NUM_FONT, QFont.Black))
        p.setPen(QPen(main))
        p.drawText(QRect(94, y - 2, 84, 28), Qt.AlignLeft | Qt.AlignVCenter,
                   "%d 分" % info["fortune_score"])
        # 本日生肖紧跟分数之后（吉/平/凶框保持方正不动）
        rep = self.zodiac_report
        p.setFont(_font(14, ZH_FONT, QFont.Black))
        p.setPen(QPen(dark))
        if rep:
            ztxt = "本日生肖 %s：%s（%d分）" % (
                rep.get("name") or "", " · ".join(rep["tags"]), rep["score"])
        else:
            ztxt = "在页顶选择你的生肖，查看本日运势 →"
        p.drawText(QRect(182, y + 2, 280, 22), Qt.AlignLeft | Qt.AlignVCenter, ztxt)
        p.setFont(_font(12, ZH_FONT))
        fm = p.fontMetrics()
        tail = "值神%s·%s｜吉神%d 凶煞%d ｜ %s" % (
            info["tianshen_type"], info["tianshen"],
            len(info["jishen"]), len(info["xiongsha"]), info["fortune_tip"])
        p.drawText(QRect(94, y + 27, 396, 22), Qt.AlignLeft | Qt.AlignVCenter,
                   fm.elidedText(tail, Qt.ElideRight, 396))

    def _paint_zodiac(self, p):
        rep = self.zodiac_report
        main = self.P["main"]
        y = 540
        if not rep:
            return    # 未选生肖：提示语已移至分数旁
        p.setPen(QPen(main, 1, Qt.DashLine))
        p.drawLine(30, y - 3, self.PAGE_W - 30, y - 3)
        p.setFont(_font(12, ZH_SONG))
        p.setPen(QPen(INK))
        # 有八字推演时优先展示（标注「八字推演」），否则显示生肖提示
        if rep.get("bazi_text"):
            tip = "八字推演：%s" % rep["bazi_text"]
        else:
            tip = rep["tips"][0] if rep["tips"] else rep["text"]
        fm = p.fontMetrics()
        tip = fm.elidedText(tip, Qt.ElideRight, 460)
        p.drawText(QRect(30, y + 2, 460, 20), Qt.AlignVCenter | Qt.AlignLeft, tip)

    def _paint_hours_colors(self, p):
        """吉时 + 吉凶颜色（穿衣五行）。"""
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        y, h = 574, 68
        # 左框：吉时（与右框沿页面中线 x=260 对称）
        p.setPen(QPen(main, 2))
        p.setBrush(self.P["box_bg"])
        p.drawRect(30, y, 224, h)
        p.setBrush(main)
        p.drawRoundedRect(38, y - 9, 46, 19, 2, 2)
        p.setFont(_font(12, ZH_FONT, QFont.Black))
        p.setPen(QPen(QColor("#ffffff")))
        p.drawText(QRect(38, y - 9, 46, 19), Qt.AlignCenter, "吉时")
        p.setFont(_font(11, ZH_FONT))
        p.setPen(QPen(dark))
        hours = info["lucky_hours"][:6]
        if hours:
            col_w, row_h = 104, 16
            for i, (_, hz, ts, rng) in enumerate(hours):
                col, row = i % 2, i // 2
                txt = "%s %s" % (hz, rng)
                p.drawText(QRect(38 + col * col_w, y + 15 + row * row_h,
                                 col_w, row_h),
                           Qt.AlignLeft | Qt.AlignVCenter, txt)
        else:
            p.drawText(QRect(38, y + 22, 208, 20), Qt.AlignLeft | Qt.AlignVCenter,
                       "今日无黄道吉时")
        # 右框：吉凶颜色（266..490，与左框对称）
        p.setPen(QPen(main, 2))
        p.setBrush(self.P["box_bg"])
        p.drawRect(266, y, 224, h)
        p.setBrush(main)
        p.drawRoundedRect(274, y - 9, 46, 19, 2, 2)
        p.setFont(_font(12, ZH_FONT, QFont.Black))
        p.setPen(QPen(QColor("#ffffff")))
        p.drawText(QRect(274, y - 9, 46, 19), Qt.AlignCenter, "颜色")
        colors = info["lucky_colors"] or {}
        rows = [("大吉", colors.get("大吉", "—"), QFont.Black),
                ("次吉", colors.get("次吉", "—"), QFont.Black),
                ("不宜", colors.get("不宜", "—"), QFont.Normal)]
        for i, (tag, names, weight) in enumerate(rows):
            ry = y + 14 + i * 18
            first = names.split("、")[0] if names else ""
            chip = QColor(COLOR_CHIPS.get(first, "#cccccc"))
            p.setBrush(chip)
            p.setPen(QPen(QColor("#00000040"), 1))
            p.drawEllipse(280, ry + 3, 10, 10)
            p.setPen(QPen(dark))
            p.setFont(_font(12, ZH_FONT, weight))
            p.drawText(QRect(298, ry, 180, 17), Qt.AlignLeft | Qt.AlignVCenter,
                       "%s %s" % (tag, names))

    def _paint_advice(self, p):
        """事业 / 感情 / 出行 / 财务 分项建议。"""
        info = self.info
        main, dark = self.P["main"], self.P["dark"]
        y, cell_h, cell_w, gap = 652, 54, 224, 12
        advice = info["advice"]
        for i, key in enumerate(["事业", "感情", "出行", "财务"]):
            col, row = i % 2, i // 2
            x = 30 + col * (cell_w + gap)
            cy = y + row * (cell_h + 4)
            p.setPen(QPen(main, 1))
            p.setBrush(self.P["box_bg"])
            p.drawRoundedRect(QRectF(x, cy, cell_w, cell_h), 3, 3)
            p.setBrush(main)
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x + 6, cy + 8, 40, 18), 2, 2)
            p.setFont(_font(13, ZH_FONT, QFont.Black))
            p.setPen(QPen(QColor("#ffffff")))
            p.drawText(QRect(x + 6, cy + 8, 40, 18), Qt.AlignCenter, key)
            p.setFont(_font(12, ZH_SONG))
            p.setPen(QPen(dark))
            fm = p.fontMetrics()
            full = advice.get(key, "—")
            # 第一行放标签右侧，放不下折到第二行整行，保证文字完整显示
            w1 = cell_w - 58
            cut = 0
            for k in range(1, len(full) + 1):
                if fm.horizontalAdvance(full[:k]) > w1:
                    break
                cut = k
            line1, rest = full[:cut], full[cut:]
            p.drawText(QRect(x + 52, cy + 8, w1, 19),
                       Qt.AlignLeft | Qt.AlignVCenter, line1)
            if rest:
                line2 = fm.elidedText(rest, Qt.ElideRight, cell_w - 12)
                p.drawText(QRect(x + 6, cy + 31, cell_w - 12, 18),
                           Qt.AlignLeft | Qt.AlignVCenter, line2)

    def _paint_zodiac_watermark(self, p):
        """底部当日生肖剪影水印（随主题红 / 绿取图，透明度 20%）。"""
        sx = self.info.get("day_shengxiao")
        if not sx:
            return
        tone = _tone_of(self.P["main"])
        path = os.path.join(_ZODIAC_DIR, "%s（%s）.png" % (sx, tone))
        src = _pix_cached(path)
        if src.isNull():
            return
        # 等比缩放到高约 210px，居中压在底部区块上作水印
        w, h = int(src.width() * 210.0 / src.height()), 210
        x = (self.PAGE_W - w) // 2
        y = 566 + (212 - h) // 2
        p.save()
        p.setOpacity(0.2)
        p.drawPixmap(x, y, w, h, _pix_scaled(path, w, h))
        p.restore()

    def _paint_footer(self, p):
        p.setFont(_font(10, ZH_FONT))
        p.setPen(QPen(QColor("#7a7a6e")))
        p.drawText(QRect(0, self.PAGE_H - 70, self.PAGE_W, 16),
                   Qt.AlignCenter, "%s ｜ %s" % (VER.COPYRIGHT, VER.LICENSE_NOTE))
        # 底部双击按钮：本月行事历 / 本日行事历（双击开 / 关对应面板）
        main = self.P["main"]
        for rect, text, visible in [
                (self.TAB_MONTH_RECT, "本月行事历", self._month_visible),
                (self.TAB_DAY_RECT, "本日行事历", self._day_visible)]:
            if visible:
                p.setPen(QPen(main, 1))
                p.setBrush(main)
                p.drawRoundedRect(rect, 4, 4)
                p.setPen(QPen(QColor("#ffffff")))
            else:
                p.setPen(QPen(main, 1))
                p.setBrush(self.P["box_bg"])
                p.drawRoundedRect(rect, 4, 4)
                p.setPen(QPen(main))
            arrow = "▴" if visible else "▾"
            p.setFont(_font(12, ZH_FONT, QFont.Black))
            p.drawText(rect, Qt.AlignCenter, "%s %s" % (arrow, text))
        p.setFont(_font(9, ZH_FONT))
        p.setPen(QPen(QColor("#a09a88")))
        p.drawText(QRect(0, self.TAB_Y + self.TAB_H + 2, self.PAGE_W, 12),
                   Qt.AlignCenter, "（双击按钮 打开 / 关闭 对应面板）")
