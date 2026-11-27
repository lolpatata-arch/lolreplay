"""Bounded paint-only motion; no graphics effects on native video or layout changes."""
import math
import time
import weakref
from PySide6.QtCore import Qt, QObject, QTimer, QRectF, QPointF
from PySide6.QtGui import QPainter,QColor,QPen,QBrush,QRadialGradient,QLinearGradient
from PySide6.QtWidgets import QPushButton,QLabel
import lolreplay_alive as alive

class MotionEngine(QObject):
    def __init__(self,window):
        super().__init__(window); self.window=window; self.effects=weakref.WeakKeyDictionary()
        self.timer=QTimer(self); self.timer.setTimerType(Qt.TimerType.CoarseTimer); self.timer.timeout.connect(self.tick)
    def allowed(self):
        return not getattr(self.window,'closing',False) and alive.allowed(self.window.alive,self.window.foreground(),self.window.active is True)
    def ambient_active(self):
        art=getattr(self.window,'art',None)
        return self.allowed() and self.window.alive['ambient']!='off' and self.window.alive['intensity']>0 and art is not None and art.isVisible()
    def trigger(self,widget,kind):
        if not self.allowed() or not widget.isVisible() or self.window.alive.get(kind)=='off' or not self.window.alive['intensity']: return
        self.effects[widget]=(kind,time.monotonic()); widget.update(); self.sync()
    def clear(self,widget,kind=None):
        entry=self.effects.get(widget)
        if entry and (kind is None or entry[0]==kind):
            self.effects.pop(widget,None); widget.update()
    def sync(self):
        if not self.allowed():
            for widget in list(self.effects):
                try: widget.update()
                except RuntimeError: pass
            self.effects.clear(); self.timer.stop()
            if hasattr(self.window,'art'): self.window.art.update()
            return
        interval=max(16,round(1000/self.window.alive['fps']))
        if self.timer.interval()!=interval: self.timer.setInterval(interval)
        if self.effects or self.ambient_active():
            if not self.timer.isActive(): self.timer.start()
        else: self.timer.stop()
    def tick(self):
        if not self.allowed(): self.sync(); return
        for widget in list(self.effects):
            try:
                entry=self.effects.get(widget)
                if not entry: continue
                if not widget.isVisible() or time.monotonic()-entry[1]>=self.window.alive['duration']/1000: self.effects.pop(widget,None)
                widget.update()
            except RuntimeError: self.effects.pop(widget,None)
        if self.ambient_active(): self.window.art.update()
        self.sync()
    def stop(self):
        self.timer.stop(); self.effects.clear()
    def paint(self,widget,p):
        entry=self.effects.get(widget)
        if not entry or not self.allowed(): return
        kind,start=entry; settings=self.window.alive; style=settings[kind]
        if style=='off': return
        x=alive.easing((time.monotonic()-start)/(settings['duration']/1000),settings['easing'])
        strength=settings['intensity']/100; fade=max(0.,1-x); r=QRectF(widget.rect()).adjusted(2,2,-2,-2)
        if r.width()<=0 or r.height()<=0: return
        color=QColor(self.window.palette_for()[4]); color.setAlpha(round(150*strength*fade))
        p.save(); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setClipRect(r); p.setPen(Qt.PenStyle.NoPen)
        if style=='glow':
            gradient=QRadialGradient(r.center(),max(1,r.width()*.65)); gradient.setColorAt(0,color); clear=QColor(color); clear.setAlpha(0); gradient.setColorAt(1,clear); p.fillRect(r,QBrush(gradient))
        elif style in ('wash','flash','fade'): p.fillRect(r,color)
        elif style in ('underline','slide'):
            p.fillRect(QRectF(r.left(),r.bottom()-3,r.width()*(.2+.8*x),3),color)
        elif style=='sweep':
            p.fillRect(QRectF(r.left()+r.width()*x-r.width()*.2,r.top(),r.width()*.2,r.height()),color)
        elif style=='ripple':
            p.setBrush(color); rad=max(r.width(),r.height())*(.08+.7*x); p.drawEllipse(r.center(),rad,rad)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(color,2 if style=='outline' else 3)); p.drawRoundedRect(r,6,6)
        p.restore()
    def paint_ambient(self,p,r):
        if not self.ambient_active(): return
        settings=self.window.alive; mode=settings['ambient']; phase=time.monotonic()*settings['ambient_speed']/100; strength=settings['intensity']/100
        color=QColor(self.window.palette_for()[4]); color.setAlpha(round(65*strength)); p.save(); p.setPen(Qt.PenStyle.NoPen); p.setBrush(color)
        w,h=r.width(),r.height()
        if mode=='particles':
            for i in range(18):
                x=(i*97+math.sin(phase*.55+i)*25)%max(1,w); y=(i*53-phase*(8+i%4))%max(1,h); p.drawEllipse(QPointF(x,y),2+i%3,2+i%3)
        elif mode=='orbit':
            for i in range(6):
                a=phase*.5+i*math.tau/6; p.drawEllipse(QPointF(w*.75+math.cos(a)*w*.17,h*.5+math.sin(a)*h*.33),3,3)
        elif mode=='scan':
            x=(phase*45)%max(1,w); gradient=QLinearGradient(x-35,0,x+35,0); clear=QColor(color); clear.setAlpha(0); gradient.setColorAt(0,clear); gradient.setColorAt(.5,color); gradient.setColorAt(1,clear); p.fillRect(QRectF(x-35,0,70,h),QBrush(gradient))
        elif mode=='drift':
            center=QPointF(w*(.5+.28*math.sin(phase*.3)),h*(.5+.25*math.cos(phase*.25))); gradient=QRadialGradient(center,max(1,w*.45)); clear=QColor(color); clear.setAlpha(0); gradient.setColorAt(0,color); gradient.setColorAt(1,clear); p.fillRect(r,QBrush(gradient))
        p.restore()

def engine(widget): return getattr(widget.window(),'motion_engine',None)

class MotionButton(QPushButton):
    def enterEvent(self,event):
        super().enterEvent(event); e=engine(self)
        if e: e.trigger(self,'hover')
    def leaveEvent(self,event):
        super().leaveEvent(event); e=engine(self)
        if e: e.clear(self,'hover')
    def mousePressEvent(self,event):
        super().mousePressEvent(event); e=engine(self)
        if e and event.button()==Qt.MouseButton.LeftButton and self.isEnabled(): e.trigger(self,'press')
    def paintEvent(self,event):
        super().paintEvent(event); e=engine(self)
        if e and self in e.effects:
            p=QPainter(self); e.paint(self,p); p.end()

class MotionTitle(QLabel):
    def paintEvent(self,event):
        super().paintEvent(event); e=engine(self)
        if e and self in e.effects:
            p=QPainter(self); e.paint(self,p); p.end()
