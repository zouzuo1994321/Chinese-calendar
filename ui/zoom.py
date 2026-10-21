# -*- coding: utf-8 -*-
"""整窗等比例缩放（v1.9.27）：场景缩放宿主 + 左右下角小三角手柄。

为什么必须用 QGraphicsView，而不是「把控件尺寸乘系数」：
  UI 是「520×841 的自绘页（paintEvent 里全是绝对坐标）+ 两个 QSS 面板
  （按钮 / 编辑框的字号与高度写在 styleSheet 的 px 里）」的固定像素组合。
  手动按系数改尺寸只会让自绘页的坐标系与 QSS 的 px 互相脱节：
  自绘页会画出框外，QSS 控件却纹丝不动 —— 布局必崩。
  场景变换（QGraphicsView + QGraphicsProxyWidget）是唯一能「整棵控件树一起
  缩放、布局代码一行不改」的方式：事件坐标由视图自动反变换，命中测试、
  悬停提示、光标、输入法都走原路径，所以功能零影响。

分工：
  ZoomView   —— 无边框 / 无滚动条的场景宿主，负责把「场景没接住的左键按下」
                交回窗口拖动（与原 MainWindow.mousePressEvent 同一套状态）。
  ScaleGrip  —— 角落三角手柄：默认透明，鼠标移入淡入；按住拖动 = 等比缩放。
"""
from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QFrame, QGraphicsView, QWidget

BOARD_BG = "#f3f0e6"          # 与叠页纸色一致（去掉深色外框）
GRIP_INK = "#6e6857"          # 三角墨色（纸面上的中性墨，红/绿主题都压得住）


class ZoomView(QGraphicsView):
    """场景宿主：整窗按 MainWindow._scale 做等比变换。"""

    def __init__(self, window):
        super().__init__(window)
        self._win = window
        self.setObjectName("zoomView")
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setDragMode(QGraphicsView.NoDrag)
        # 缩放锚点 / 视口锚点都设 NoAnchor：窗口尺寸由 MainWindow 精确算好，
        # 视图只负责「左上角对齐 + 不做任何自动补偿」，否则缩放时布局会自己漂。
        self.setResizeAnchor(QGraphicsView.NoAnchor)
        self.setTransformationAnchor(QGraphicsView.NoAnchor)
        # 分数倍缩放时局部重绘会留 1px 接缝，整窗重绘最稳（页面本来就整页重绘，代价相同）
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing |
                            QPainter.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor(BOARD_BG))
        self.setFocusPolicy(Qt.NoFocus)      # 焦点留给面板里的编辑器
        self.setMouseTracking(True)
        # 视口是独立控件：视图开了 tracking 不等于视口开了 —— 页面的悬停提示
        # （今日卦象 / 四张建议卡）全靠无按键的 mouseMove，必须两处都开。
        self.viewport().setMouseTracking(True)
        self.viewport().setAttribute(Qt.WA_Hover, True)

    # 场景没接住的左键按下 → 交回窗口自己拖动（保持无边框窗口原有手感）
    def mousePressEvent(self, ev):
        super().mousePressEvent(ev)
        if (ev.button() == Qt.LeftButton and self.scene() is not None
                and self.scene().mouseGrabberItem() is None):
            self._win._begin_window_drag(ev.globalPosition().toPoint())
            ev.accept()

    def mouseMoveEvent(self, ev):
        if (ev.buttons() & Qt.LeftButton) and self._win._is_window_dragging():
            self._win._continue_window_drag(ev.globalPosition().toPoint())
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        super().mouseReleaseEvent(ev)
        if self._win._is_window_dragging():
            self._win._end_window_drag()


class ScaleGrip(QWidget):
    """角落小三角缩放手柄。

    corner="br" → 右下角（拖动时锚定左上角）
    corner="bl" → 左下角（拖动时锚定右上角）
    """

    SIZE = 22          # 命中区（比三角形略大，方便鼠标扫到）
    LEG = 13           # 三角形直角边长

    def __init__(self, window, corner):
        super().__init__(window)
        self._win = window
        self.corner = corner
        self._alpha = 0.0
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.SizeBDiagCursor if corner == "bl"
                       else Qt.SizeFDiagCursor)
        self.setToolTip("")
        self._fade = QVariantAnimation(self)
        self._fade.setDuration(140)
        self._fade.setEasingCurve(QEasingCurve.OutCubic)
        self._fade.valueChanged.connect(self._on_fade)

    # ---------- 淡入淡出（鼠标移过去才显示） ----------
    def _on_fade(self, v):
        self._alpha = float(v)
        self.update()

    def _fade_to(self, target):
        self._fade.stop()
        self._fade.setStartValue(self._alpha)
        self._fade.setEndValue(float(target))
        self._fade.start()

    def enterEvent(self, ev):
        self.setToolTip("按住拖动：等比缩放（当前 %d%%）" % self._win.scale_percent())
        self._fade_to(1.0)
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        if not self._win._is_scaling():
            self._fade_to(0.0)
        super().leaveEvent(ev)

    # ---------- 绘制：贴角的小直角三角形 ----------
    def paintEvent(self, ev):
        if self._alpha <= 0.01:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        ink = QColor(GRIP_INK)
        ink.setAlphaF(min(0.9, 0.32 + 0.58 * self._alpha))
        p.setPen(Qt.NoPen)
        p.setBrush(ink)
        s, n = self.SIZE, self.LEG
        path = QPainterPath()
        if self.corner == "br":
            path.moveTo(s, s - n)
            path.lineTo(s, s)
            path.lineTo(s - n, s)
        else:
            path.moveTo(0, s - n)
            path.lineTo(0, s)
            path.lineTo(n, s)
        path.closeSubpath()
        p.drawPath(path)
        p.end()

    # ---------- 拖拽 = 等比缩放 ----------
    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self._win._begin_scale_drag(self.corner,
                                        ev.globalPosition().toPoint())
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.LeftButton:
            self._win._continue_scale_drag(ev.globalPosition().toPoint())
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._win._end_scale_drag()
        super().mouseReleaseEvent(ev)


__all__ = ["ZoomView", "ScaleGrip", "BOARD_BG", "GRIP_INK"]
