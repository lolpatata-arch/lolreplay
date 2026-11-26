"""Shared responsive widgets. Geometry is in Qt logical pixels (HiDPI aware)."""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QScrollArea, QFrame, QSlider, QStyle, QStyleOptionSlider, QCheckBox, QLabel, QHBoxLayout, QWidget, QSizePolicy, QListWidget


class PageScroll(QScrollArea):
    """Allow a page to shrink below its contents; scroll instead of clipping."""
    def __init__(self, content, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    def minimumSizeHint(self):
        return QSize(120, 100)
    def sizeHint(self):
        return QSize(640, 440)


class SeekSlider(QSlider):
    """Absolute click/drag seeking, with normal keyboard and wheel controls."""
    seekRequested = Signal(int)
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.actionTriggered.connect(self._keyboard_seek)
    def _keyboard_seek(self, _action):
        if not self.isSliderDown(): self.seekRequested.emit(self.sliderPosition())
    def value_at(self, x):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()
        groove = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)
        handle = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)
        span = max(1, groove.width() - handle.width())
        offset = round(x - groove.x() - handle.width()/2)
        return QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), max(0, min(span, offset)), span, opt.upsideDown)
    def _seek(self, event):
        value = self.value_at(event.position().x())
        self.setSliderPosition(value)
        self.seekRequested.emit(value)
        event.accept()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.maximum() > self.minimum():
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.setSliderDown(True)
            self._seek(event)
        else:
            super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if self.isSliderDown() and event.buttons() & Qt.MouseButton.LeftButton:
            self._seek(event)
        else:
            super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSliderDown():
            self._seek(event)
            self.setSliderDown(False)
        else:
            super().mouseReleaseEvent(event)


class ToggleLabel(QLabel):
    """Wrap long translated checkbox labels while keeping the checkbox accessible."""
    def __init__(self, text, checkbox):
        super().__init__(text)
        self.checkbox = checkbox
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setBuddy(checkbox)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.checkbox.click()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


def toggle_row(checkbox, text):
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(checkbox, 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addWidget(ToggleLabel(text, checkbox), 1)
    return row


class ResponsiveClipList(QListWidget):
    """Keep the preferred tile size, but fit a whole tile in narrow viewports."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tile_width=222; self._tile_extra=64
    def set_tile_metrics(self, width, extra):
        self._tile_width=width; self._tile_extra=extra
        self.fit_tiles()
    def fit_tiles(self):
        available=self.viewport().width()-4
        width=min(self._tile_width,max(100,available)) if available>0 else self._tile_width
        size=QSize(width,int((width-12)*9/16)+self._tile_extra)
        if self.gridSize()!=size: self.setGridSize(size)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.fit_tiles()
