"""Static shell-inspired visual tokens; no compositor blur or animation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Design:
    radius: int
    floating: bool
    sheen: bool

STYLES={'shell':Design(16,True,True),'glass':Design(20,True,True),'minimal':Design(8,False,False),'classic':Design(5,False,False)}

def profile(values):
    base=STYLES.get(values.get('visual_style'),STYLES['shell'])
    radius={'auto':base.radius,'sharp':3,'rounded':12,'pill':22}.get(values.get('corner_style'),base.radius)
    return Design(radius,base.floating,base.sheen and values.get('accent_glow',True))

def spacing(values,compact):
    if compact: return 8,12,8
    return {'tight':(10,20,10),'balanced':(15,28,14),'airy':(20,34,16)}.get(values.get('visual_density'),(15,28,14))

def chrome(values,bg,surface,border,accent,bright,ink,raised,deep):
    d=profile(values); r=d.radius; small=max(3,min(12,r//2))
    glass=values.get('visual_style')=='glass'
    side=(f'qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {raised},stop:1 {deep})' if d.sheen else surface)
    card=(f'qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {raised if glass else surface},stop:1 {deep})' if d.sheen else surface)
    return f"""
    QFrame#sidebar {{background:{side};border:1px solid {border};border-radius:{r}px;}}
    QFrame#topbar {{background:{card};border:1px solid {border};border-radius:{r}px;}}
    QFrame#rail,QFrame#playerPane {{background:{card};border:1px solid {border};border-radius:{r}px;}}
    QFrame#rail QLabel,QFrame#playerPane QLabel {{background:transparent;}}
    QFrame#panel,QFrame#collectionStrip {{background:{card};border:1px solid {border};border-radius:{r}px;}}
    QFrame#themeTile {{background:{surface};border:1px solid {border};border-radius:{small}px;}}
    QFrame#feature {{background:transparent;border:0;}}
    QLabel#heading {{font-size:36px;font-weight:700;}}
    QLabel#hero {{font-size:25px;font-weight:700;}}
    QLabel#key {{background:{deep};border:1px solid {border};border-radius:{small}px;}}
    QPushButton,QComboBox,QLineEdit,QAbstractSpinBox {{border-radius:{small}px;}}
    QPushButton#primary:!disabled {{background:{accent};border-radius:{small}px;font-weight:700;color:{ink};}}
    QPushButton#primary:disabled {{background:{surface};border:1px solid {border};color:#777783;}}
    QPushButton#nav {{border-radius:{small}px;border-left:3px solid transparent;}}
    QPushButton#nav:checked {{background:{raised};border-left:3px solid {accent};}}
    QPushButton#duration:checked {{background:{raised};border:1px solid {accent};color:{bright};}}
    QListWidget#settingsNavigation {{background:{surface};border:1px solid {border};border-radius:{r}px;}}
    QListWidget#settingsNavigation::item:selected {{background:{raised};border-left:3px solid {accent};}}
    QLabel#wallpaperPreview,QPlainTextEdit {{background:{deep};border:1px solid {border};border-radius:{small}px;}}
    QProgressBar,QProgressBar::chunk {{border-radius:3px;}}
    QMenu {{border-radius:{small}px;}}
    """
