"""Editor page for lolreplay. Recorder and F8 are not involved."""
from lolreplay_i18n import t, clip_count, LANGUAGES, set_language, language
import shutil
from pathlib import Path
from PySide6.QtCore import Qt, QProcess, QUrl, Signal, QRectF, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import (QWidget,QLabel,QPushButton,QVBoxLayout,QHBoxLayout,QGridLayout,QFrame,QFileDialog,QDoubleSpinBox,QSlider,QProgressBar,QMessageBox,QSizePolicy,QScrollArea,QComboBox,QDialog)
import lolreplay_storage as storage
from lolreplay_export import probe, export_args, temp_for
from lolreplay_icons import decorate
try:
    from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MEDIA=True
except (ImportError,OSError): MEDIA=False


if MEDIA:
    class ClickVideoWidget(QVideoWidget):
        """Click the video surface to toggle playback, without affecting other controls."""
        clicked=Signal()
        def __init__(self,parent=None):
            super().__init__(parent)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(t('Click to play or pause'))
            self.setAccessibleName(t('Video preview: click to play or pause'))
        def mouseReleaseEvent(self,event):
            if event.button()==Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
                self.clicked.emit(); event.accept(); return
            super().mouseReleaseEvent(event)
else:
    ClickVideoWidget=None


def lab(s,name=''):
    w=QLabel(s); w.setTextFormat(Qt.TextFormat.PlainText); w.setObjectName(name); return w

def btn(s,fn,name=''):
    w=QPushButton(s); w.setObjectName(name); w.setCursor(Qt.CursorShape.PointingHandCursor); w.clicked.connect(fn); return w

def clock(t):
    ms=max(0,round(t*1000)); return f'{ms//60000:02d}:{(ms//1000)%60:02d}.{(ms%1000)//100}'

class FullscreenPlayer(QDialog):
    """Temporarily route the existing player to a full-screen video surface."""
    def __init__(self,parent,player,inline,toggle):
        super().__init__(parent)
        self.player=player; self.inline=inline; self.restored=False
        self.setWindowTitle(t('lolreplay · Full screen'))
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName('fullscreenPlayer')
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.video=ClickVideoWidget(self); self.video.clicked.connect(lambda: toggle() if getattr(parent,'prefs',{}).get('video_click',True) else None);
        if not getattr(parent,'prefs',{}).get('video_click',True): self.video.setToolTip(''); self.video.setAccessibleName(t('Video preview'))
        self.video.setStyleSheet('background:#050505;border:none;'); layout.addWidget(self.video,1)
        bar=QFrame(); bar.setObjectName('fullscreenControls'); row=QHBoxLayout(bar); row.setContentsMargins(16,8,16,8)
        self.ink=parent.button_ink() if hasattr(parent,'button_ink') else '#ffffff'; self.play=decorate(btn(t('Play'),toggle,'primary'),'play',self.ink); row.addWidget(self.play)
        self.seek=QSlider(Qt.Orientation.Horizontal); self.seek.setAccessibleName(t('Playback position')); self.seek.setToolTip(t('Seek through the clip')); self.seek.setRange(0,max(0,player.duration())); self.seek.setValue(player.position()); self.seek.sliderMoved.connect(player.setPosition); row.addWidget(self.seek,1)
        self.time=lab('', 'muted'); row.addWidget(self.time); row.addWidget(decorate(btn(t('Exit full screen')+' · Esc',self.reject),'full')); layout.addWidget(bar)
        self.shortcuts=[]
        keymap=parent.keymap; bindings={'Esc':self.reject};
        for name,action in [('exit_fullscreen',self.reject),('fullscreen',self.reject),('play',toggle)]:
            if keymap[name]: bindings[keymap[name]]=action
        for key,action in bindings.items():
            shortcut=QShortcut(QKeySequence.fromString(key,QKeySequence.SequenceFormat.PortableText),self); shortcut.setAutoRepeat(False); shortcut.activated.connect(action); shortcut.setEnabled(key=='Esc' or parent.prefs['keyboard_shortcuts']); self.shortcuts.append(shortcut)
        player.positionChanged.connect(self.update_position); player.durationChanged.connect(self.update_duration); player.playbackStateChanged.connect(self.update_state)
        self.update_position(player.position()); self.update_state(player.playbackState())
        self.finished.connect(self.restore)
        player.setVideoOutput(self.video)
    def update_position(self,pos):
        if not self.seek.isSliderDown(): self.seek.setValue(pos)
        self.time.setText(clock(pos/1000)+' / '+clock(self.player.duration()/1000))
    def update_duration(self,duration):
        self.seek.setRange(0,max(0,duration)); self.update_position(self.player.position())
    def update_state(self,state):
        playing=state==QMediaPlayer.PlaybackState.PlayingState; self.play.setText(t('Pause') if playing else t('Play')); decorate(self.play,'pause' if playing else 'play',self.ink)
    def restore(self,*_):
        if not self.restored:
            self.restored=True
            self.player.setVideoOutput(self.inline)
    def closeEvent(self,event):
        self.restore(); super().closeEvent(event)


def show_fullscreen(owner,player,inline,toggle):
    dialog=FullscreenPlayer(owner.window(),player,inline,toggle)
    dialog.showFullScreen()
    return dialog

class Timeline(QWidget):
    changed=Signal(float,float); seek=Signal(float)
    def __init__(self):
        super().__init__(); self.total=0.; self.start=0.; self.end=0.; self.pos=0.; self.drag=None; self.setMinimumHeight(78); self.setMouseTracking(True)
    def to_x(self,t): return 12+(self.width()-24)*t/max(self.total,.001)
    def value(self,x): return min(self.total,max(0.,(x-12)*self.total/max(1,self.width()-24)))
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(self.palette().mid().color()); p.drawRoundedRect(QRectF(12,25,max(1,self.width()-24),26),3,3)
        a,b=self.to_x(self.start),self.to_x(self.end)
        if self.total:
            accent=self.palette().highlight().color() if not hasattr(self,'accent') else QColor(self.accent)
            p.setBrush(accent.darker(210)); p.drawRoundedRect(QRectF(a,25,max(1,b-a),26),3,3)
            p.setPen(QPen(QColor('#a6a6b2'),1));
            for i in range(21):
                x=round(12+(self.width()-24)*i/20); p.drawLine(x,21 if i%5 else 17,x,24)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(accent)
            for x in (a,b):
                p.drawRoundedRect(QRectF(x-4,22,8,32),2,2)
                p.setPen(QPen(accent.lighter(165),1)); p.drawLine(round(x),30,round(x),45); p.setPen(Qt.PenStyle.NoPen)
            p.setPen(QPen(QColor('#eeeeee'),1.5)); x=round(self.to_x(self.pos)); p.drawLine(x,12,x,58)
            p.setBrush(QColor('#eeeeee')); p.drawRoundedRect(QRectF(x-3,9,6,6),1,1)
        p.setPen(QColor('#a6a6b2')); p.drawText(12,73,'00:00'); t=clock(self.total); p.drawText(self.width()-12-p.fontMetrics().horizontalAdvance(t),73,t)
        p.end()
    def mousePressEvent(self,e):
        if not self.total or not self.isEnabled(): return
        x=e.position().x(); a,b=self.to_x(self.start),self.to_x(self.end)
        if min(abs(x-a),abs(x-b))<=12: self.drag='start' if abs(x-a)<=abs(x-b) else 'end'
        else: self.drag='seek'
        self.drag_to(x)
    def mouseMoveEvent(self,e):
        if self.drag: self.drag_to(e.position().x())
    def mouseReleaseEvent(self,e):
        if self.drag: self.drag_to(e.position().x()); self.drag=None
    def drag_to(self,x):
        v=self.value(x); minimum=min(.1,self.total)
        if self.drag=='start': self.changed.emit(min(v,self.end-minimum),self.end)
        elif self.drag=='end': self.changed.emit(self.start,max(v,self.start+minimum))
        else: self.seek.emit(v)

class Editor(QWidget):
    def __init__(self,window):
        super().__init__(); self.window=window; self.source=None; self.music=None; self.total=0.; self.tracks=0; self.temp=None; self.target=None; self.cancelled=False; self.buf=''; self.err=''; self.previewing=False; self.player=None
        self.proc=QProcess(self); self.proc.readyReadStandardOutput.connect(self.progress_read); self.proc.readyReadStandardError.connect(self.error_read); self.proc.finished.connect(self.finished); self.proc.errorOccurred.connect(self.process_error)
        main=QVBoxLayout(self); main.setContentsMargins(0,0,0,0); main.setSpacing(12)
        top=QHBoxLayout(); top.addWidget(lab(t('Clip'),'section')); self.choose=QComboBox(); self.choose.setAccessibleName(t('Clip to edit')); self.choose.setToolTip(t('Choose a saved clip from your library')); self.choose.setMinimumHeight(48); self.choose.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed); self.choose.setIconSize(QSize(64,36)); self.choose.setMaxVisibleItems(10); self.choose.currentIndexChanged.connect(self.choose_clip); top.addWidget(self.choose,1); self.count=lab(clip_count(0),'muted'); top.addWidget(self.count); main.addLayout(top)
        self.title=lab(t('No clip selected'),'muted'); self.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred); main.addWidget(self.title)
        area=QHBoxLayout(); area.setSpacing(16); left=QFrame(); left.setObjectName('feature'); l=QVBoxLayout(left); l.setContentsMargins(0,0,0,0); l.setSpacing(9)
        if MEDIA:
            self.video=ClickVideoWidget(); self.video.clicked.connect(lambda:self.play_selection() if self.window.prefs['video_click'] else None); self.video.setMinimumHeight(165); self.video.setStyleSheet('background:#050505'); l.addWidget(self.video,1)
            self.player=QMediaPlayer(self); self.audio=QAudioOutput(self); self.audio.setVolume(.45); self.player.setAudioOutput(self.audio); self.player.setVideoOutput(self.video); self.player.positionChanged.connect(self.position); self.player.playbackStateChanged.connect(self.play_state); self.player.errorOccurred.connect(lambda e,m:self.note.setText(t('Preview: ')+m))
        else: l.addWidget(lab(t('Preview unavailable. Export is still supported.'),'muted'),1)
        row=QHBoxLayout(); self.play=decorate(btn(t('Play selection'),self.play_selection,'primary'),'play','#ffffff'); row.addWidget(self.play); self.position_label=lab('00:00.0 / 00:00.0','muted'); row.addWidget(self.position_label); row.addStretch();
        if MEDIA:
            self.full_btn=decorate(btn(t('Full screen'),self.fullscreen_preview),'full'); row.addWidget(self.full_btn)
        l.addLayout(row)
        self.timeline=Timeline(); self.timeline.setAccessibleName(t('Trim timeline')); self.timeline.setToolTip(t('Drag the handles to trim; click to seek')); self.timeline.changed.connect(self.set_range); self.timeline.seek.connect(self.seek); l.addWidget(self.timeline)
        grid=QGridLayout(); self.start=QDoubleSpinBox(); self.end=QDoubleSpinBox()
        for w in (self.start,self.end): w.setDecimals(3); w.setSingleStep(.1); w.setRange(0,0); w.setSuffix(' s'); w.setKeyboardTracking(False)
        self.start.setAccessibleName(t('Trim start in seconds')); self.end.setAccessibleName(t('Trim end in seconds')); self.start.valueChanged.connect(lambda x:self.set_range(x,self.end.value(),'start')); self.end.valueChanged.connect(lambda x:self.set_range(self.start.value(),x,'end'))
        grid.addWidget(lab(t('IN'),'eyebrow'),0,0); grid.addWidget(lab(t('OUT'),'eyebrow'),0,1); grid.addWidget(self.start,1,0); grid.addWidget(self.end,1,1)
        self.markin=btn(t('Set in at playhead'),lambda:self.set_range(self.timeline.pos,self.end.value(),'start')); self.markout=btn(t('Set out at playhead'),lambda:self.set_range(self.start.value(),self.timeline.pos,'end')); grid.addWidget(self.markin,2,0); grid.addWidget(self.markout,2,1); l.addLayout(grid)
        row=QHBoxLayout(); self.selection=lab(t('Selected: {0}','00:00.0'),'section'); row.addWidget(self.selection); row.addStretch(); self.reset=btn(t('Reset trim'),lambda:self.set_range(0,self.total)); row.addWidget(self.reset); l.addLayout(row); area.addWidget(left,1)
        rail=QFrame(); rail.setObjectName('rail'); rail.setFixedWidth(325 if language() in ('de_DE','fr_FR','ru_RU','pl_PL','es_ES','it_IT') else 275); r=QVBoxLayout(rail); r.setContentsMargins(15,8,0,8); r.setSpacing(9); r.addWidget(lab(t('AUDIO'),'eyebrow')); r.addWidget(lab(t('Original audio'),'section')); self.vol=self.slider(r,100); self.vol.setAccessibleName(t('Original audio volume')); r.addSpacing(8); r.addWidget(lab(t('Local music'),'section')); self.music_name=lab(t('No music selected'),'muted'); self.music_name.setWordWrap(True); r.addWidget(self.music_name); self.music_btn=decorate(btn(t('Add music…'),self.choose_music),'music'); r.addWidget(self.music_btn); self.clear_music=btn(t('Remove music'),self.remove_music,'quiet'); r.addWidget(self.clear_music); self.musicvol=self.slider(r,25); self.musicvol.setAccessibleName(t('Music volume')); note=lab(t('Music loops to fit the selection. Preview plays original audio only.'),'muted'); note.setWordWrap(True); r.addWidget(note); r.addStretch(); r.addWidget(lab(t('EXPORT'),'eyebrow')); r.addWidget(lab('MP4 · H.264 / AAC','section')); hint=lab(t('Replaces the original only after a successful export.'),'muted'); hint.setWordWrap(True); r.addWidget(hint); self.export=decorate(btn(t('Save changes'),self.begin_export,'primary'),'save','#ffffff'); r.addWidget(self.export); self.progress=QProgressBar(); self.progress.setObjectName('exportProgress'); self.progress.setAccessibleName(t('Export progress')); self.progress.setRange(0,100); self.progress.setValue(0); r.addWidget(self.progress); self.cancel=btn(t('Cancel export'),self.cancel_export); r.addWidget(self.cancel); area.addWidget(rail); main.addLayout(area,1)
        self.note=lab(window.hotkey_text('Save a clip with F8 to start editing.'),'muted'); self.note.setWordWrap(True); main.addWidget(self.note); self.controls()
    def slider(self,layout,value):
        row=QHBoxLayout(); s=QSlider(Qt.Orientation.Horizontal); s.setRange(0,100); s.setValue(value); n=lab(f'{value}%','muted'); s.valueChanged.connect(lambda v:n.setText(f'{v}%')); row.addWidget(s,1); row.addWidget(n); layout.addLayout(row); return s
    def busy(self): return self.temp is not None
    def controls(self):
        ready=bool(self.source and self.total>0); busy=self.busy()
        for w in (self.timeline,self.start,self.end,self.reset,self.vol,self.music_btn): w.setEnabled(ready and not busy)
        self.play.setEnabled(ready and self.player is not None and not busy); self.markin.setEnabled(self.play.isEnabled()); self.markout.setEnabled(self.play.isEnabled()); self.musicvol.setEnabled(ready and bool(self.music) and not busy); self.clear_music.setEnabled(bool(self.music) and not busy); self.choose.setEnabled(not busy and self.choose.count()>1); self.export.setEnabled(ready and not busy and shutil.which('ffmpeg') is not None); self.cancel.setEnabled(busy)
        if MEDIA: self.full_btn.setEnabled(ready and not busy)
    def fullscreen_preview(self):
        if self.player and self.source and not self.busy():
            show_fullscreen(self,self.player,self.video,self.play_selection)
    def update_clips(self,files,thumbs):
        # Reuse the library scan; do not reset an edit when new clips arrive.
        self.choose.blockSignals(True)
        self.choose.clear()
        self.choose.addItem(t('Select a saved clip…'),None)
        selected=0
        for key in files:
            path,_,size=key
            if size<=0: continue
            pix=thumbs.get(key)
            self.choose.addItem(QIcon(pix) if pix is not None else self.window.logo,Path(path).name,path)
            if self.source and Path(path).resolve()==self.source: selected=self.choose.count()-1
        self.choose.setCurrentIndex(selected)
        self.choose.blockSignals(False)
        n=self.choose.count()-1; self.count.setText(clip_count(n))
        self.controls()
    def update_thumbnail(self,path,pix):
        i=self.choose.findData(path)
        if i>=0: self.choose.setItemIcon(i,QIcon(pix))
    def choose_clip(self,index):
        if index<=0:
            if self.source: self.sync_selection()
            return
        if not self.load(self.choose.itemData(index)): self.sync_selection()
    def sync_selection(self):
        index=0
        if self.source:
            for i in range(1,self.choose.count()):
                if Path(self.choose.itemData(i)).resolve()==self.source:
                    index=i; break
        self.choose.blockSignals(True); self.choose.setCurrentIndex(index); self.choose.blockSignals(False)
    def select_latest(self):
        if not self.source and not self.busy() and self.choose.count()>1:
            self.choose.setCurrentIndex(1)
    def load(self,path):
        if self.busy(): self.note.setText(t('Finish or cancel the current export first.')); return False
        try:
            p=Path(path).resolve(strict=True)
            if p==self.source and storage.signature(p)==self.source_signature: self.sync_selection(); return True
            identity=storage.signature(p)
            d,a,v=probe(p)
            if storage.signature(p)!=identity: raise ValueError('Clip changed while opening')
            if not v or d<=0: raise ValueError(t('No readable video or duration'))
        except Exception as e: self.note.setText(t('Cannot open clip: ')+str(e)); return False
        self.source=p; self.source_signature=identity; self.sync_selection(); self.total=d; self.tracks=a; self.title.setText(p.name); self.timeline.total=d; self.timeline.pos=0.; self.previewing=False
        for w in (self.start,self.end):
            w.blockSignals(True); w.setRange(0,d); w.blockSignals(False)
        self.set_range(0,d); self.position(0); self.progress.setValue(0)
        if self.player: self.player.stop(); self.player.setSource(QUrl.fromLocalFile(str(p)))
        self.note.setText(clock(d)+' · '+t('{0} audio track(s) · drag the handles to trim.',a)); self.controls(); return True
    def set_range(self,a,b,which=None):
        minimum=min(.1,self.total); a=max(0,min(a,self.total)); b=max(0,min(b,self.total))
        if b-a<minimum:
            if which=='start': a=max(0,b-minimum)
            else: b=min(self.total,a+minimum); a=min(a,b-minimum)
        for w,x in ((self.start,a),(self.end,b)):
            w.blockSignals(True); w.setValue(x); w.blockSignals(False)
        self.timeline.start=a; self.timeline.end=b; self.timeline.update(); self.selection.setText(t('Selected: {0}',clock(b-a)))
    def seek(self,t):
        self.previewing=False
        if self.player: self.player.setPosition(round(t*1000))
        self.position(round(t*1000))
    def position(self,ms):
        t=ms/1000; self.timeline.pos=t; self.timeline.update(); self.position_label.setText(clock(t)+' / '+clock(self.total))
        if self.previewing and t>=self.end.value() and self.player: self.previewing=False; self.player.pause()
    def play_selection(self):
        if not self.player or not self.source or self.busy(): return
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState: self.player.pause(); return
        self.previewing=True
        if not self.start.value()<=self.player.position()/1000<self.end.value(): self.player.setPosition(round(self.start.value()*1000))
        self.player.play()
    def play_state(self,state):
        playing=state==QMediaPlayer.PlaybackState.PlayingState; self.play.setText(t('Pause') if playing else t('Play selection')); decorate(self.play,'pause' if playing else 'play',self.window.button_ink())
    def pause(self):
        if self.player: self.player.pause()
    def release(self):
        if self.player: self.player.stop(); self.player.setSource(QUrl())
        self.source=None; self.total=0.; self.timeline.total=0.; self.timeline.update(); self.title.setText(t('No clip selected')); self.sync_selection(); self.controls()
    def choose_music(self):
        p,_=QFileDialog.getOpenFileName(self,t('Choose local music'),str(Path.home()),'Audio (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.opus);;All files (*)')
        if not p: return
        try:
            d,a,_=probe(p)
            if not a or d<=0: raise ValueError(t('No audio stream'))
        except Exception as e: self.note.setText(t('Music: ')+str(e)); return
        self.music=Path(p); self.music_name.setText(self.music.name); self.controls()
    def remove_music(self): self.music=None; self.music_name.setText(t('No music selected')); self.controls()
    def begin_export(self):
        if not self.source or self.busy(): return
        a,b=self.start.value(),self.end.value()
        try:
            storage.config_check(self.window.out)
            self.library_id=storage.read_config().get("library_id")
            target=self.source
            if target.suffix.lower() != ".mp4": raise ValueError(t("In-place editing currently supports MP4 clips only"))
            if b-a<.09: raise ValueError(t('Invalid destination or trim range'))
            if self.source.parent!=self.window.out.resolve(): raise ValueError(t("Select a clip from the current library"))
            if not self.source.is_file() or (self.music and not self.music.is_file()): raise ValueError(t('A source file is missing'))
            if QMessageBox.question(self,t("Replace original?"),t('Save changes to {0}? The previous version will be replaced, not kept as a separate clip.',target.name),QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes: return
            self.expected=self.source_signature
            if storage.signature(target)!=self.expected: raise ValueError(t('Clip changed since opening; select it again'))
            self.temp=temp_for(storage.staging()/target.name); self.target=target
            args=export_args(self.source,self.temp,a,b,self.tracks,self.vol.value(),self.music,self.musicvol.value()); self.export_length=b-a
        except Exception as e:
            self.cleanup(); self.note.setText(t('Export: ')+str(e)); return
        self.pause(); self.cancelled=False; self.buf=''; self.err=''; self.progress.setValue(0); self.controls(); self.note.setText(t('Exporting… original file is safe.')); self.proc.start('ffmpeg',args)
    def progress_read(self):
        self.buf+=bytes(self.proc.readAllStandardOutput()).decode(errors='replace'); lines=self.buf.split('\n'); self.buf=lines.pop()
        for line in lines:
            if line.startswith('out_time_us='):
                try: self.progress.setValue(max(0,min(99,int(int(line.split('=',1)[1])/1e6/self.export_length*100))))
                except ValueError: pass
    def error_read(self): self.err=(self.err+bytes(self.proc.readAllStandardError()).decode(errors='replace'))[-4000:]
    def cancel_export(self):
        if self.busy(): self.cancelled=True; self.proc.kill()
    def cleanup(self):
        if self.temp:
            try: self.temp.unlink(missing_ok=True)
            except OSError: pass
        self.temp=None; self.target=None; self.controls()
    def finished(self,code,status):
        self.error_read()
        if not self.busy(): return
        validated=False
        try:
            if self.cancelled: self.note.setText(t('Export cancelled. Original unchanged.')); self.progress.setValue(0)
            elif code!=0 or status!=QProcess.ExitStatus.NormalExit: self.note.setText(t('Export failed: ')+(self.err.strip() or 'FFmpeg stopped')); self.progress.setValue(0)
            else:
                duration,_,video=probe(self.temp)
                if not video or duration<=0 or abs(duration-self.export_length)>max(.5,self.export_length*.02): raise ValueError('Export duration or video validation failed')
                validated=True
                target=self.target
                if self.player: self.player.stop(); self.player.setSource(QUrl())
                if self.window.player and self.window.preview_path==str(target):
                    self.window.player.stop(); self.window.player.setSource(QUrl()); self.window.preview_path=None
                storage.config_check(target.parent)
                storage.replace_clip(self.temp,target,self.expected,self.library_id)
                self.cleanup(); self.release(); self.remove_music(); self.vol.setValue(100); self.musicvol.setValue(25)
                self.window.refresh_library(force=True); self.load(str(target)); self.progress.setValue(100); self.note.setText(t('Changes saved: ')+target.name)
        except Exception as e:
            if validated and self.temp and self.temp.exists():
                recovered=self.temp.with_suffix('.mp4')
                try: self.temp.rename(recovered)
                except OSError: recovered=self.temp
                self.temp=None  # Never delete a validated recovery file even if rename failed.
                self.note.setText(t('Export retained locally: ')+str(recovered)+' · '+str(e))
            else: self.note.setText(t('Could not finish export: ')+str(e))
            self.progress.setValue(0)
        finally: self.cleanup()
    def process_error(self,error):
        if error==QProcess.ProcessError.FailedToStart: self.note.setText(t('Cannot start FFmpeg: ')+self.proc.errorString()); self.cleanup()
