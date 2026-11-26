"""Small original line icons, rendered locally at 2x resolution; no font or network dependency."""
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor, QPixmap, QIcon


def icon(name, color='#c5c5cc', active=None):
    def draw(c):
        pix=QPixmap(40,40); pix.fill(Qt.GlobalColor.transparent)
        p=QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.scale(2,2)
        p.setPen(QPen(QColor(c),1.55,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        def path(*points):
            q=QPainterPath(); q.moveTo(*points[0]); [q.lineTo(*v) for v in points[1:]]; p.drawPath(q)
        def rect(x,y,w,h,r=1.6): p.drawRoundedRect(QRectF(x,y,w,h),r,r)
        def circle(x,y,r): p.drawEllipse(QRectF(x-r,y-r,r*2,r*2))
        if name=='replay':
            p.drawArc(QRectF(3,3,14,14),35*16,285*16); path((12,3),(17,3),(17,8)); path((9,6.5),(9,10),(12,12))
        elif name=='clips':
            rect(3,5,14,12); path((3,9),(17,9)); path((6,5),(8,9)); path((12,5),(14,9)); path((9,11),(12,13),(9,15),(9,11))
        elif name=='edit':
            circle(5,14,2.5); circle(15,14,2.5); path((6.8,12.2),(14,3)); path((13.2,12.2),(6,3))
        elif name=='settings':
            for y,x in ((5,7),(10,13),(15,9)):
                path((3,y),(x-2,y)); path((x+2,y),(17,y)); circle(x,y,2)
        elif name=='play': path((7,4),(16,10),(7,16),(7,4))
        elif name=='pause': path((7,4),(7,16)); path((13,4),(13,16))
        elif name=='stop': rect(5,5,10,10,1)
        elif name=='save': path((4,4),(16,4),(16,16),(4,16),(4,4)); path((7,4),(7,9),(13,9),(13,4)); path((7,16),(7,12),(13,12),(13,16))
        elif name=='folder': path((2.5,6),(7,6),(9,8),(17.5,8),(16,16),(3,16),(2.5,6)); path((3,6),(3,4),(8,4),(10,6),(16,6),(16,8))
        elif name=='refresh': p.drawArc(QRectF(3,3,14,14),45*16,285*16); path((12,3),(17,3),(17,8))
        elif name=='full':
            for x,y,dx,dy in ((3,3,1,1),(17,3,-1,1),(3,17,1,-1),(17,17,-1,-1)): path((x+5*dx,y),(x,y),(x,y+5*dy))
        elif name=='arrow': path((3,10),(16,10),(11,5)); path((16,10),(11,15))
        elif name=='down': path((6,8),(10,12),(14,8))
        elif name=='music': path((7,14),(7,5),(16,3),(16,12)); circle(4.7,14,2.3); circle(13.7,12,2.3)
        elif name=='trash': path((4,6),(16,6)); path((6,6),(7,17),(13,17),(14,6)); path((8,6),(8,3),(12,3),(12,6)); path((9,9),(9,14)); path((11,9),(11,14))
        elif name=='rename': path((4,13),(13,4),(16,7),(7,16),(4,16),(4,13)); path((11,6),(14,9))
        elif name=='image':
            rect(3,3,14,14); circle(7,7,1.5); path((4,14),(9,10),(12,13),(14,11),(16,13))
        elif name=='external': path((10,3),(17,3),(17,10)); path((17,3),(9,11)); path((8,5),(3,5),(3,17),(15,17),(15,12))
        else: circle(10,10,5)
        p.end(); pix.setDevicePixelRatio(2); return pix
    result=QIcon(); result.addPixmap(draw(color),QIcon.Mode.Normal,QIcon.State.Off)
    result.addPixmap(draw(active or color),QIcon.Mode.Normal,QIcon.State.On)
    result.addPixmap(draw('#606068'),QIcon.Mode.Disabled,QIcon.State.Off)
    result.addPixmap(draw('#606068'),QIcon.Mode.Disabled,QIcon.State.On)
    return result


def decorate(button, name, color='#c5c5cc', active=None):
    button.setIcon(icon(name,color,active)); button.setIconSize(QSize(18,18)); button.setProperty('lrIcon',name)
    return button
