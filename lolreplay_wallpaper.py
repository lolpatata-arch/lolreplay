"""Local wallpaper playback. GIF/image frames and silent video are independent of clip playback."""
from pathlib import Path
import time
from PySide6.QtCore import Qt,QObject,QSize,QRect,QUrl,Signal,QByteArray
from PySide6.QtGui import QMovie,QImageReader,QPixmap,QPainter,QColor
from PySide6.QtWidgets import QWidget
import lolreplay_alive as alive
import lolreplay_backgrounds as backgrounds
try:
    from PySide6.QtMultimedia import QMediaPlayer,QVideoSink
except (ImportError,OSError):
    QMediaPlayer=QVideoSink=None

MAX_VIDEO=256*1024*1024
MAX_FRAME_PIXELS=3840*2160
def valid_file(mode,path):
    try:
        file=Path(path).expanduser()
        if not file.is_file(): return False
        if mode=='video': return QMediaPlayer is not None and file.suffix.lower() in alive.VIDEO_EXTENSIONS and 0<file.stat().st_size<=MAX_VIDEO
        return mode=='image' and not backgrounds.load_image(str(file)).isNull()
    except (OSError,ValueError,TypeError): return False

def draw_wallpaper(p,rect,pix,fit,dim,bg):
    p.fillRect(rect,QColor(bg))
    if pix is None or pix.isNull(): return
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    if fit=='fit':
        size=pix.size().scaled(rect.size(),Qt.AspectRatioMode.KeepAspectRatio)
        p.drawPixmap(QRect(rect.x()+(rect.width()-size.width())//2,rect.y()+(rect.height()-size.height())//2,size.width(),size.height()),pix)
    else: backgrounds.cover(p,rect,pix)
    if dim: p.fillRect(rect,QColor(0,0,0,round(255*dim/100)))

class WallpaperSource(QObject):
    changed=Signal()
    failed=Signal()
    def __init__(self,parent):
        super().__init__(parent); self.mode='none'; self.path=''; self.pix=QPixmap(); self.still=QPixmap(); self.movie=None; self.player=None; self.sink=None; self.running=False; self.last_frame=0.; self.fps=24; self.speed=100; self.error=False
    def clear(self):
        self.running=False
        if self.movie:
            movie=self.movie; self.movie=None; movie.stop(); movie.deleteLater()
        if self.player:
            player=self.player; self.player=None; player.stop(); player.setVideoSink(None); player.deleteLater()
        if self.sink: self.sink.deleteLater(); self.sink=None
        self.pix=QPixmap(); self.still=QPixmap(); self.last_frame=0.; self.error=False
    def load(self,mode,path,pix=None):
        self.clear(); self.mode=mode; self.path=path
        if mode=='image':
            self.still=pix if pix is not None else backgrounds.load_image(path); self.pix=self.still
            if not self.still.isNull():
                reader=QImageReader(str(Path(path).expanduser()))
                if reader.supportsAnimation():
                    size=reader.size()
                    if 0<size.width()*size.height()<=MAX_FRAME_PIXELS:
                        self.movie=QMovie(str(Path(path).expanduser()),QByteArray(),self); self.movie.setCacheMode(QMovie.CacheMode.CacheNone)
                        if size.width()>1280 or size.height()>720: self.movie.setScaledSize(size.scaled(QSize(1280,720),Qt.AspectRatioMode.KeepAspectRatio))
                        self.movie.frameChanged.connect(self.movie_frame); self.movie.finished.connect(self.movie_finished); self.movie.error.connect(self.mark_error)
            else: self.error=True
        elif mode=='video':
            if not valid_file(mode,path): self.error=True
        self.changed.emit()
    def mark_error(self,*_):
        if self.error: return
        self.error=True; self.running=False
        if self.movie: self.movie.stop()
        if self.player: self.player.stop()
        self.failed.emit()
    def movie_frame(self,*_):
        if not self.running or not self.movie: return
        now=time.monotonic()
        if now-self.last_frame<1/max(1,self.fps): return
        pix=self.movie.currentPixmap()
        if not pix.isNull(): self.pix=pix; self.last_frame=now; self.changed.emit()
    def movie_finished(self):
        if self.running and self.movie and not self.error: self.movie.start()
    def video_frame(self,frame):
        if not self.running or not frame.isValid(): return
        now=time.monotonic()
        if now-self.last_frame<1/max(1,self.fps): return
        size=frame.size()
        if size.width()*size.height()>MAX_FRAME_PIXELS:
            if self.player: self.player.stop()
            self.mark_error(); return
        image=frame.toImage()
        if not image.isNull():
            if image.width()>1280 or image.height()>720: image=image.scaled(QSize(1280,720),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.FastTransformation)
            self.pix=QPixmap.fromImage(image); self.last_frame=now; self.changed.emit()
    def sync(self,enabled,speed,fps):
        self.fps=fps; self.speed=speed
        enabled=bool(enabled and not self.error)
        if self.movie:
            self.movie.setSpeed(speed)
            if enabled and not self.running:
                self.running=True
                if self.movie.state()==QMovie.MovieState.Paused: self.movie.setPaused(False)
                else: self.movie.start()
            elif not enabled and self.running: self.running=False; self.movie.setPaused(True)
        elif self.mode=='video' and enabled and QMediaPlayer:
            if not self.player:
                self.player=QMediaPlayer(self); self.sink=QVideoSink(self); self.player.setVideoSink(self.sink)
                self.sink.videoFrameChanged.connect(self.video_frame); self.player.errorOccurred.connect(self.mark_error)
                self.player.setLoops(-1); self.player.setSource(QUrl.fromLocalFile(str(Path(self.path).expanduser().absolute())))
            self.player.setPlaybackRate(speed/100)
            if not self.running and not self.error: self.running=True; self.player.play()
        elif self.player and self.running: self.running=False; self.player.pause()
        if not enabled and not self.still.isNull() and self.pix.isNull(): self.pix=self.still; self.changed.emit()
    def stop(self):
        self.clear()

class WallpaperRoot(QWidget):
    def __init__(self,window):
        super().__init__(); self.window=window
    def paintEvent(self,event):
        p=QPainter(self); window=self.window; settings=window.alive
        source=window.app_wallpaper
        bg=window.palette_for()[0]
        if window.app_background['mode']=='none': bg=QColor(bg).darker(125).name()
        draw_wallpaper(p,self.rect(),source.pix,settings['wallpaper_fit'],settings['wallpaper_dim'],bg); p.end()
