"""Independent playback routing, clip track selection and on-demand desktop mixer."""
import json
import math
import struct
import time
from PySide6.QtCore import QObject,QProcess,QTimer,Qt
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QComboBox,QScrollArea,QWidget,QSpinBox,QProgressBar,QInputDialog)
from lolreplay_i18n import t
from lolreplay_sound import device_preference,resolve_output,mixer_rows,volume_args,mute_args
try:
    from PySide6.QtMultimedia import QMediaDevices,QMediaMetaData,QAudioFormat,QMediaPlayer
except (ImportError,OSError):
    QMediaDevices=QMediaMetaData=QAudioFormat=QMediaPlayer=None
try:
    from PySide6.QtMultimedia import QAudioBufferOutput
except (ImportError,OSError):
    QAudioBufferOutput=None

def device_id(device):
    return bytes(device.id()).hex()

class PlaybackRouting(QObject):
    def __init__(self,parent,outputs,preference,changed):
        super().__init__(parent)
        self.outputs=[x for x in outputs if x is not None]
        self.preference=device_preference(preference)
        self.changed=changed
        self.media=QMediaDevices(self) if QMediaDevices is not None and self.outputs else None
        if self.media: self.media.audioOutputsChanged.connect(self.refresh)
        self.refresh()

    def devices(self):
        return {device_id(d):d for d in self.media.audioOutputs() if not d.isNull()} if self.media else {}

    def refresh(self):
        devices=self.devices()
        default=self.media.defaultAudioOutput() if self.media else None
        key,missing=resolve_output(self.preference,devices,device_id(default) if default is not None and not default.isNull() else '')
        target=devices.get(key)
        if target is None and default is not None and not default.isNull(): target=default
        if target is not None:
            for output in self.outputs:
                if output.device()!=target: output.setDevice(target)
        desc=target.description() if target is not None else t('No playback device')
        self.changed(desc,missing)

    def choose(self,parent):
        if not self.media: return None
        devices=self.devices()
        ids=['auto',*devices]
        names=[t('System default')]+[d.description()+' ['+key+']' for key,d in devices.items()]
        index=ids.index(self.preference) if self.preference in ids else 0
        selected,ok=QInputDialog.getItem(parent,t('Playback output'),t('Playback output'),names,index,False)
        if not ok: return None
        self.preference=ids[names.index(selected)]
        self.refresh()
        return self.preference

class TrackSelector(QComboBox):
    def __init__(self,player,parent=None):
        super().__init__(parent)
        self.player=player
        self.setAccessibleName(t('Playback audio track'))
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)
        self.currentIndexChanged.connect(self.select_track)
        player.tracksChanged.connect(self.refresh)
        player.activeTracksChanged.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.blockSignals(True)
        self.clear()
        tracks=self.player.audioTracks()
        for i,meta in enumerate(tracks):
            title=meta.stringValue(QMediaMetaData.Key.Title)
            name=t('Audio track {0}',i+1)+(' · '+title if title else '')
            self.addItem(name,i)
        if not tracks: self.addItem(t('No audio track'),-1)
        self.setEnabled(bool(tracks))
        self.setCurrentIndex(self.findData(self.player.activeAudioTrack()))
        if self.currentIndex()<0 and not tracks: self.setCurrentIndex(0)
        self.blockSignals(False)

    def select_track(self,index):
        track=self.itemData(index)
        if type(track) is int and 0<=track<len(self.player.audioTracks()):
            self.player.setActiveAudioTrack(track)

class PlaybackMeter(QProgressBar):
    """Optional decoded sample peak; no capture tap or polling process."""
    def __init__(self,player,parent=None):
        super().__init__(parent)
        self.setRange(0,100); self.setValue(0); self.setTextVisible(False)
        self.setAccessibleName(t('Playback signal peak'))
        self.setToolTip(t('Decoded audio peak before playback volume'))
        self.setMaximumHeight(8)
        self.player=player; self.last=0.; self.buffer=None
        if QAudioBufferOutput is not None and hasattr(player,'setAudioBufferOutput'):
            self.buffer=QAudioBufferOutput(self)
            self.buffer.audioBufferReceived.connect(self.sample)
            player.setAudioBufferOutput(self.buffer)
            player.playbackStateChanged.connect(self.reset)
            player.sourceChanged.connect(lambda _:self.setValue(0))
        else:
            self.hide()

    def reset(self,state):
        if state!=QMediaPlayer.PlaybackState.PlayingState: self.setValue(0)

    def sample(self,buffer):
        if not self.isVisible() or self.player.playbackState()!=QMediaPlayer.PlaybackState.PlayingState: return
        now=time.monotonic()
        if now-self.last<.1: return
        self.last=now
        if not buffer.isValid(): self.setValue(0); return
        try:
            formats={QAudioFormat.SampleFormat.UInt8:('B',128),QAudioFormat.SampleFormat.Int16:('h',32768),
                     QAudioFormat.SampleFormat.Int32:('i',2147483648),QAudioFormat.SampleFormat.Float:('f',1)}
            code,scale=formats[buffer.format().sampleFormat()]
            data=bytes(buffer.constData())
            size=struct.calcsize(code); count=len(data)//size
            step=max(1,count//512)
            peak=0.
            for i in range(0,count,step):
                v=struct.unpack_from('='+code,data,i*size)[0]
                if code=='B': v-=128
                if math.isfinite(v): peak=max(peak,abs(v)/scale)
            self.setValue(min(100,round(peak*100)))
        except (KeyError,TypeError,ValueError,BufferError,struct.error,AttributeError,OverflowError):
            self.setValue(0)

class DesktopMixer(QDialog):
    """Explicit desktop-volume edits; refresh on demand, never while gaming."""
    def __init__(self,parent):
        super().__init__(parent)
        self.setWindowTitle(t('Application mixer')); self.resize(520,460)
        root=QVBoxLayout(self)
        note=QLabel(t('Changes desktop playback volumes, not isolated clip-track gains. Only currently active audio streams are listed.'))
        note.setWordWrap(True); root.addWidget(note)
        self.status=QLabel(''); self.status.setWordWrap(True); root.addWidget(self.status)
        self.refresh_btn=QPushButton(t('Refresh')); self.refresh_btn.clicked.connect(self.refresh); root.addWidget(self.refresh_btn)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); self.body=QWidget(); self.rows=QVBoxLayout(self.body); scroll.setWidget(self.body); root.addWidget(scroll,1)
        close=QPushButton(t('Close')); close.clicked.connect(self.reject); root.addWidget(close)
        self.proc=QProcess(self); self.proc.finished.connect(self.finished_command); self.proc.errorOccurred.connect(self.failed)
        self.timeout=QTimer(self); self.timeout.setSingleShot(True); self.timeout.timeout.connect(self.proc.kill)
        self.operation=''; self.ending=False
        self.refresh()

    def command(self,args,operation):
        if self.ending or self.proc.state()!=QProcess.ProcessState.NotRunning: return
        self.operation=operation; self.body.setEnabled(False); self.refresh_btn.setEnabled(False)
        self.proc.start('pactl',args); self.timeout.start(4000)

    def refresh(self):
        self.command(['-f','json','list','sink-inputs'],'list')

    def failed(self,*_):
        if self.ending: return
        if self.proc.state()==QProcess.ProcessState.NotRunning:
            self.timeout.stop(); self.status.setText(self.proc.errorString()); self.body.setEnabled(True); self.refresh_btn.setEnabled(True)

    def finished_command(self,code,status):
        self.timeout.stop()
        if self.ending: return
        self.body.setEnabled(True); self.refresh_btn.setEnabled(True)
        if code!=0 or status!=QProcess.ExitStatus.NormalExit:
            self.status.setText(bytes(self.proc.readAllStandardError()).decode(errors='replace')[:300] or t('Audio command failed')); return
        if self.operation!='list': self.refresh(); return
        try: rows=mixer_rows(json.loads(bytes(self.proc.readAllStandardOutput())))
        except (ValueError,TypeError): self.status.setText(t('Could not read audio streams')); return
        while self.rows.count():
            item=self.rows.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        for index,name,volume,muted in rows:
            widget=QWidget(); line=QVBoxLayout(widget); line.setContentsMargins(0,4,0,4)
            label=QLabel(name+' · '+str(index)); label.setTextFormat(Qt.TextFormat.PlainText); label.setWordWrap(True); line.addWidget(label)
            controls=QHBoxLayout(); level=QSpinBox(); level.setRange(0,100); level.setSuffix('%'); level.setValue(min(volume,100))
            level.setAccessibleName(name+' '+t('Volume')); controls.addWidget(level)
            apply=QPushButton(t('Apply')); apply.clicked.connect(lambda checked=False,i=index,v=level:self.command(volume_args(i,v.value()),'change')); controls.addWidget(apply)
            mute=QPushButton(t('Unmute') if muted else t('Mute')); mute.clicked.connect(lambda checked=False,i=index,m=muted:self.command(mute_args(i,not m),'change')); controls.addWidget(mute)
            line.addLayout(controls); self.rows.addWidget(widget)
        self.rows.addStretch()
        self.status.setText(t('No active audio streams') if not rows else t('Refresh to see new or closed streams'))

    def done(self,result):
        self.ending=True; self.timeout.stop()
        if self.proc.state()!=QProcess.ProcessState.NotRunning: self.proc.kill(); self.proc.waitForFinished(200)
        super().done(result)
