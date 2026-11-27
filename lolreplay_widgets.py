"""Shared responsive widgets. Geometry is in Qt logical pixels (HiDPI aware)."""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QScrollArea, QFrame, QSlider, QStyle, QStyleOptionSlider, QCheckBox, QLabel, QHBoxLayout, QWidget, QSizePolicy, QListWidget, QStackedWidget, QComboBox, QPushButton, QMenu

from lolreplay_i18n import t
from lolreplay_preferences import OPTIONS


class PlaybackSpeedButton(QPushButton):
    """Small, live rate selector shared by inline and fullscreen previews."""
    def __init__(self, player, change_speed, parent=None):
        super().__init__(parent)
        self.player=player
        self.change_speed=change_speed
        self.setObjectName('playbackSpeed')
        self.setSizePolicy(QSizePolicy.Policy.Fixed,QSizePolicy.Policy.Fixed)
        self.setAccessibleName(t('Playback speed'))
        menu=QMenu(self)
        self.rate_actions={}
        for percent in sorted(OPTIONS['playback_speed']):
            action=menu.addAction(self.rate_text(percent))
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False,value=percent:self.select_rate(value))
            self.rate_actions[percent]=action
        self.setMenu(menu)
        menu.aboutToShow.connect(self.sync_rate)
        player.playbackRateChanged.connect(self.sync_rate)
        self.sync_rate()

    @staticmethod
    def rate_text(percent):
        return f'{percent/100:g}×'

    def select_rate(self, percent):
        self.change_speed(percent)
        self.sync_rate()

    def sync_rate(self, *_):
        percent=round(self.player.playbackRate()*100)
        text=self.rate_text(percent)
        self.setText(text)
        self.setToolTip(t('Playback speed')+' · '+text)
        for value,action in self.rate_actions.items():
            action.setChecked(value==percent)


class PageScroll(QScrollArea):
    """Allow a page to shrink below its contents; scroll instead of clipping."""
    def __init__(self, content, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidget(content)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    def minimumSizeHint(self):
        return QSize(100, 64)
    def sizeHint(self):
        return QSize(640, 440)


class PageStack(QStackedWidget):
    """Hidden pages must not set the minimum size of the active workspace.

    Pages own their scrolling/splitters; the stack consumes the available space.
    """
    def minimumSizeHint(self):
        return QSize(0, 0)

    def sizeHint(self):
        return QSize(640, 440)


def fit_combo(combo, length=8):
    """Long filenames/translations must not impose their full width on a page."""
    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    combo.setMinimumContentsLength(length)
    combo.setMinimumWidth(100)
    combo.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    return combo


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
