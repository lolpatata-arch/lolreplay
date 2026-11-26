"""Static local replay backgrounds. No timers, network requests or video playback."""
from pathlib import Path
import math
from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import QImageReader, QPixmap, QPainter, QColor, QLinearGradient, QRadialGradient, QPen, QBrush

STYLES=('crimson','amoled','midnight','grid','horizon')
MODES=('logo',*STYLES,'last_clip','image')
LABELS={'logo':'Classic logo','crimson':'Crimson Glow','amoled':'AMOLED Minimal','midnight':'Midnight Orbit','grid':'Cyber Grid','horizon':'Crimson Horizon','last_clip':'Latest clip','image':'Custom image'}
MAX_PIXELS=64_000_000
MAX_FILE=32*1024*1024
CANVAS=QSize(1280,720)

def validated(raw):
    raw=raw if isinstance(raw,dict) else {}
    mode=raw.get('mode')
    path=raw.get('path','')
    if not isinstance(path,str) or '\x00' in path or len(path)>4096: path=''
    return {'mode':mode if isinstance(mode,str) and mode in MODES else 'logo','path':path}

def load_image(path):
    """Decode a single still image once, with bounded dimensions and file size."""
    if not path: return QPixmap()
    try:
        file=Path(path).expanduser()
        if not file.is_file() or file.stat().st_size>MAX_FILE: return QPixmap()
        reader=QImageReader(str(file)); reader.setAutoTransform(True)
        size=reader.size()
        if size.width()<=0 or size.height()<=0 or size.width()*size.height()>MAX_PIXELS: return QPixmap()
        if size.width()>1920 or size.height()>1080:
            reader.setScaledSize(size.scaled(QSize(1920,1080),Qt.AspectRatioMode.KeepAspectRatio))
        return QPixmap.fromImage(reader.read())
    except (OSError,ValueError,RuntimeError): return QPixmap()

def cover(painter,rect,pix):
    if pix.isNull() or rect.width()<=0 or rect.height()<=0: return
    w,h=pix.width(),pix.height()
    aspect=rect.width()/rect.height()
    sw=min(w,h*aspect); sh=min(h,w/aspect)
    painter.drawPixmap(QRectF(rect),pix,QRectF((w-sw)/2,(h-sh)/2,sw,sh))

def preset(mode,logo):
    """Render a fixed-size wallpaper from the existing application emblem."""
    if mode not in STYLES: raise ValueError('Unknown background style')
    image=QPixmap(CANVAS); image.fill(QColor('#050507'))
    p=QPainter(image); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    w,h=CANVAS.width(),CANVAS.height(); rect=QRectF(0,0,w,h); cx,cy=w/2,h/2
    colors={'crimson':('#080409','#360913','#ff304d'),'amoled':('#000000','#000000','#ad152d'),'midnight':('#050813','#101e42','#6b8aff'),'grid':('#06090b','#102126','#42d5bf'),'horizon':('#080408','#36101c','#ff4d64')}
    base,edge,accent=map(QColor,colors[mode])
    grad=QLinearGradient(0,0,w,h); grad.setColorAt(0,base); grad.setColorAt(1,edge); p.fillRect(rect,QBrush(grad))
    if mode!='amoled':
        glow=QRadialGradient(cx,cy if mode!='horizon' else h*.69,520)
        color=QColor(accent); color.setAlpha(68); glow.setColorAt(0,color); color.setAlpha(0); glow.setColorAt(1,color); p.fillRect(rect,QBrush(glow))
    p.setBrush(Qt.BrushStyle.NoBrush)
    line=QColor(accent); line.setAlpha(55); p.setPen(QPen(line,1.2))
    if mode=='crimson':
        for radius in (175,215,260,325):
            p.drawEllipse(QPointF(cx,cy),radius,radius)
        for i in range(60):
            a=i*math.tau/60
            p.drawLine(QPointF(cx+310*math.cos(a),cy+310*math.sin(a)),QPointF(cx+322*math.cos(a),cy+322*math.sin(a)))
    elif mode=='midnight':
        p.save(); p.translate(cx,cy); p.rotate(-22)
        for r in (180,240,310,420): p.drawEllipse(QRectF(-r,-r*.55,r*2,r*1.1))
        p.restore()
        for i in range(48):
            x=(i*193+71)%w; y=(i*127+31)%h
            p.drawPoint(QPointF(x,y))
    elif mode=='grid':
        for x in range(0,w,48): p.drawLine(x,0,x,h)
        for y in range(0,h,48): p.drawLine(0,y,w,y)
        p.setPen(QPen(accent,2))
        for x,y,sx,sy in ((420,140,1,1),(860,140,-1,1),(420,580,1,-1),(860,580,-1,-1)):
            p.drawLine(x,y,x+sx*55,y); p.drawLine(x,y,x,y+sy*55)
    elif mode=='horizon':
        for i in range(10):
            y=round(h*.65+(i*i)*2.7); p.drawLine(0,y,w,y)
        for x in range(-w,w*2,130): p.drawLine(QPointF(cx,h*.57),QPointF(x,h))
        p.setPen(QPen(accent,2)); p.drawLine(0,round(h*.65),w,round(h*.65))
        cy=h*.40
    else:
        p.drawLine(int(cx-130),int(cy+140),int(cx+130),int(cy+140))
    size=210 if mode=='amoled' else 280
    emblem=logo.pixmap(QSize(size,size))
    p.drawPixmap(round(cx-emblem.width()/2),round(cy-emblem.height()/2),emblem)
    p.end()
    return image
