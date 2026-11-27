"""Local draft editor; no recorder or media backend calls."""
from copy import deepcopy
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QLabel,QPushButton,QCheckBox,QSpinBox,QColorDialog,QInputDialog,QScrollArea,QSizePolicy)
from lolreplay_i18n import t
from lolreplay_widgets import fit_combo
import lolreplay_creative as creative
import lolreplay_dashboard as dashboard

class StudioPreview(QWidget):
    def __init__(self,studio):
        super().__init__(); self.studio=studio; self.setMinimumHeight(180); self.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Expanding)
        self.setAccessibleName(t('Live interface preview'))
    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        state=self.studio.history.current; d=state['design']; layout=state['dashboard']
        bg,surface,border,accent,_=self.studio.window.palette_for(d)
        p.fillRect(self.rect(),QColor(bg)); scale=min(self.width()/400,self.height()/240); p.translate((self.width()-400*scale)/2,(self.height()-240*scale)/2); p.scale(scale,scale)
        radius=8 if d['radius']<0 else d['radius']/2; gap=5 if d['gap']<0 else max(2,d['gap']/2)
        m=7 if d['margin']<0 else max(3,d['margin']/2)
        def tile(x,y,w,h,fill,edge=border,r=radius):
            if w<=0 or h<=0: return
            p.setPen(QPen(QColor(edge),1) if edge else Qt.PenStyle.NoPen); p.setBrush(QColor(fill)); p.drawRoundedRect(QRectF(x,y,w,h),r,r)
        def text(x,y,w,h,value,px=10):
            font=QFont(self.font()); font.setPixelSize(px); font.setFamily(d['font'] if d['font']!='default' else self.font().family()); p.setFont(font); p.setPen(QColor('#f4f4f7'))
            p.drawText(QRectF(x,y,w,h),Qt.AlignmentFlag.AlignCenter,p.fontMetrics().elidedText(value,Qt.TextElideMode.ElideRight,int(w)))
        tile(1,1,398,238,bg)
        x,y,w,h=m,m,400-2*m,240-2*m
        hub=creative.effective_hub(d,layout,0)
        if hub:
            hy=y if d['hub']=='top' else y+h-25; tile(x,hy,w,25,surface)
            if d['hub_brand']: text(x+4,hy,w*.35,25,'lolreplay',12)
            if d['hub_status']: tile(x+w-93,hy+9,7,7,'#73d9aa',None,3)
            tile(x+w-77,hy+5,30,15,bg); tile(x+w-41,hy+5,34,15,accent)
            if d['hub']=='top': y+=25+gap
            h-=25+gap
        side=d['dock'] in ('left','right'); floating=d['dock_mode']!='full'; dw=round(28*d['dock_size']/100); dh=round(24*d['dock_size']/100)
        if side:
            dx=x if d['dock']=='left' else x+w-dw; dy=y+(h*.15 if floating else 0); length=h*(.7 if floating else 1)
            tile(dx,dy,dw,length,surface)
            for i in range(4): tile(dx+4,dy+4+i*(length-8)/4,dw-8,max(3,(length-8)/4-3),accent if i==0 else bg,None,3)
            if d['dock']=='left': x+=dw+gap
            w-=dw+gap
        else:
            length=w*(.56 if floating else 1); dx=x+(w-length)/2; dy=y if d['dock']=='top' else y+h-dh
            tile(dx,dy,length,dh,surface)
            for i in range(4): tile(dx+4+i*(length-8)/4,dy+4,max(3,(length-8)/4-3),dh-8,accent if i==0 else bg,None,3)
            if d['dock']=='top': y+=dh+gap
            h-=dh+gap
        positions=dashboard.positions(layout); rows=max((v[0] for v in positions.values()),default=0)+1
        cell=(w-2*gap)/3; rowh=max(6,min(68,(h-gap*(min(rows,4)-1))/min(rows,4)))
        p.save(); p.setClipRect(QRectF(x,y,w,max(1,h)))
        for key,(row,col,_,span) in positions.items():
            if row>=4: break
            style=d['widget_styles'].get(key,{}); cx=x+col*(cell+gap); cy=y+row*(rowh+gap); cw=span*cell+(span-1)*gap
            tile(cx,cy,cw,rowh,style.get('color',surface),accent if key=='capture' else border,style.get('radius',radius*2)/2)
            text(cx+2,cy,cw-4,rowh,t(dashboard.NAMES[key]),9)
        p.restore(); p.end()

class CreativeStudio(QDialog):
    def __init__(self,window):
        super().__init__(window); self.window=window; self.setWindowTitle(t('Creative Studio'))
        self.history=creative.History(creative.snapshot(window.creative_design,window.dashboard_layout))
        self.saved=deepcopy(window.creative_profiles); self.controls={}; self.syncing=False
        self.resize(min(820,window.width()),min(720,window.height())); self.setMinimumSize(360,300)
        root=QVBoxLayout(self); root.setContentsMargins(10,10,10,10)
        self.preview=StudioPreview(self); root.addWidget(self.preview,2)
        scroll=QScrollArea(); scroll.setWidgetResizable(True); content=QWidget(); form=QFormLayout(content); form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows); form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow); scroll.setWidget(content); root.addWidget(scroll,3)
        def combo(key,title,choices):
            control=fit_combo(QComboBox())
            for value,name in choices: control.addItem(t(name),value)
            control.currentIndexChanged.connect(lambda _,k=key,c=control:self.change(k,c.currentData())); self.controls[key]=control; form.addRow(t(title),control)
        def toggle(key,title):
            control=QCheckBox(); control.toggled.connect(lambda value,k=key:self.change(k,value)); self.controls[key]=control; form.addRow(t(title),control)
        def number(key,title,lo,hi,suffix=''):
            control=QSpinBox(); control.setRange(lo,hi); control.setSuffix(suffix)
            if lo==-1: control.setSpecialValueText(t('Automatic'))
            control.valueChanged.connect(lambda value,k=key:self.change(k,value)); self.controls[key]=control; form.addRow(t(title),control)
        self.preset=fit_combo(QComboBox()); self.preset.addItem(t('Select preset'),None)
        for name in creative.PRESETS: self.preset.addItem(name,name)
        self.preset.activated.connect(self.choose_preset); form.addRow(t('Interface style'),self.preset)
        combo('dock','Dock position',(('bottom','Bottom'),('top','Top'),('left','Left'),('right','Right')))
        combo('hub','Command bar position',(('top','Top'),('bottom','Bottom')))
        toggle('hub_visible','Show command bar'); toggle('hub_brand','Show branding'); toggle('hub_status','Show recorder status'); toggle('hub_hotkey','Show hotkey')
        combo('dock_mode','Dock style',(('auto','Automatic'),('floating','Floating'),('full','Full width')))
        combo('dock_labels','Dock labels',(('auto','Automatic'),('icons','Icons only'),('text','Text and icons')))
        number('dock_size','Dock size',80,130,'%')
        combo('font','Font family',(('default','Automatic'),('sans-serif','Sans serif'),('serif','Serif'),('monospace','Monospace')))
        combo('weight','Font weight',(('default','Automatic'),('normal','Normal'),('medium','Medium'),('bold','Bold')))
        number('radius','Corner radius',-1,24,' px'); number('gap','Widget spacing',-1,24,' px'); number('margin','Outer margin',-1,24,' px'); number('opacity','Surface opacity',55,100,'%')
        combo('media_layout','Media layout',(('auto','Automatic'),('horizontal','Horizontal'),('vertical','Vertical')))
        self.colors={}
        for key,title in (('bg','Background'),('surface','Panels'),('border','Borders'),('accent','Accent')):
            b=QPushButton(); b.clicked.connect(lambda checked=False,k=key:self.pick_palette(k)); self.colors[key]=b
            row=QHBoxLayout(); row.addWidget(b,1); clear=QPushButton(t('Reset')); clear.clicked.connect(lambda checked=False,k=key:self.set_palette(k,'')); row.addWidget(clear); form.addRow(t(title),row)
        self.widget=fit_combo(QComboBox())
        for key in dashboard.IDS: self.widget.addItem(t(dashboard.NAMES[key]),key)
        self.widget.currentIndexChanged.connect(self.sync_widget); form.addRow(t('Widget appearance'),self.widget)
        self.widget_color=QPushButton(); self.widget_color.clicked.connect(self.pick_widget); form.addRow(t('Background'),self.widget_color)
        self.widget_radius=QSpinBox(); self.widget_radius.setRange(-1,24); self.widget_radius.setSpecialValueText(t('Automatic')); self.widget_radius.valueChanged.connect(self.change_widget_radius); form.addRow(t('Corner radius'),self.widget_radius)
        reset_widget=QPushButton(t('Reset')); reset_widget.clicked.connect(lambda:self.change_widget({})); form.addRow(reset_widget)
        self.profile=fit_combo(QComboBox()); form.addRow(t('Saved designs'),self.profile)
        row=QHBoxLayout()
        for name,fn in (('Load',self.load_profile),('Save design',self.save_profile),('Delete',self.delete_profile)):
            b=QPushButton(t(name)); b.clicked.connect(fn); row.addWidget(b)
        form.addRow(row)
        note=QLabel(t('Preview only. Apply to save. Command controls stay available on other pages or when the capture widget is hidden. Surface opacity blends colors, not desktop blur.')); note.setWordWrap(True); form.addRow(note)
        row=QHBoxLayout(); self.undo_btn=QPushButton(t('Undo')); self.redo_btn=QPushButton(t('Redo'))
        self.undo_btn.clicked.connect(lambda:self.travel(False)); self.redo_btn.clicked.connect(lambda:self.travel(True)); row.addWidget(self.undo_btn); row.addWidget(self.redo_btn)
        reset=QPushButton(t('Reset layout')); reset.clicked.connect(self.reset); row.addWidget(reset); root.addLayout(row)
        row=QHBoxLayout(); cancel=QPushButton(t('Cancel')); cancel.clicked.connect(self.reject); apply=QPushButton(t('Apply')); apply.setObjectName('primary'); apply.clicked.connect(self.apply); row.addWidget(cancel); row.addWidget(apply); root.addLayout(row)
        self.sync_profiles(); self.sync()
    def push(self,design=None,layout=None):
        state=self.history.current; self.history.push(creative.snapshot(state['design'] if design is None else design,state['dashboard'] if layout is None else layout)); self.sync()
    def change(self,key,value):
        if not self.syncing: self.push({**self.history.current['design'],key:value})
    def sync(self):
        self.syncing=True; d=self.history.current['design']
        for key,control in self.controls.items():
            if isinstance(control,QComboBox): control.setCurrentIndex(control.findData(d[key]))
            elif isinstance(control,QCheckBox): control.setChecked(d[key])
            else: control.setValue(d[key])
        for key,b in self.colors.items(): b.setText(d['palette'].get(key,t('Automatic')))
        self.sync_widget(); self.syncing=False; self.undo_btn.setEnabled(bool(self.history.past)); self.redo_btn.setEnabled(bool(self.history.future)); self.preview.update()
    def sync_widget(self,*_):
        style=self.history.current['design']['widget_styles'].get(self.widget.currentData(),{})
        self.widget_color.setText(style.get('color',t('Automatic'))); old=self.widget_radius.blockSignals(True); self.widget_radius.setValue(style.get('radius',-1)); self.widget_radius.blockSignals(old)
    def choose_preset(self,*_):
        name=self.preset.currentData()
        if name in creative.PRESETS: self.push(creative.PRESETS[name])
        self.preset.setCurrentIndex(0)
    def set_palette(self,key,value):
        palette=dict(self.history.current['design']['palette']); palette[key]=value; self.change('palette',palette)
    def pick_palette(self,key):
        d=self.history.current['design']; initial=d['palette'].get(key,self.window.palette_for(d)[creative.COLORS.index(key)])
        c=QColorDialog.getColor(QColor(initial),self,t('Custom palette'))
        if c.isValid() and creative.color(c.name(),key!='accent'): self.set_palette(key,c.name())
    def change_widget(self,style):
        styles=deepcopy(self.history.current['design']['widget_styles']); styles[self.widget.currentData()]=style; self.change('widget_styles',styles)
    def pick_widget(self):
        style=dict(self.history.current['design']['widget_styles'].get(self.widget.currentData(),{}))
        c=QColorDialog.getColor(QColor(style.get('color',self.window.palette_for(self.history.current['design'])[1])),self,t('Background'))
        if c.isValid() and creative.color(c.name(),True): style['color']=c.name(); self.change_widget(style)
    def change_widget_radius(self,value):
        if self.syncing: return
        style=dict(self.history.current['design']['widget_styles'].get(self.widget.currentData(),{}))
        if value<0: style.pop('radius',None)
        else: style['radius']=value
        self.change_widget(style)
    def travel(self,redo):
        self.history.redo() if redo else self.history.undo(); self.sync()
    def reset(self): self.push(creative.DEFAULTS,dashboard.defaults())
    def sync_profiles(self):
        self.profile.clear()
        for name in self.saved: self.profile.addItem(name,name)
    def save_profile(self):
        name,ok=QInputDialog.getText(self,t('Save design'),t('Design name'))
        name=name.strip()
        if ok and 1<=len(name)<=48 and (name in self.saved or len(self.saved)<16):
            self.saved[name]=deepcopy(self.history.current); self.sync_profiles(); self.profile.setCurrentIndex(self.profile.findData(name))
    def load_profile(self):
        name=self.profile.currentData()
        if name in self.saved: self.history.push(self.saved[name]); self.sync()
    def delete_profile(self):
        self.saved.pop(self.profile.currentData(),None); self.sync_profiles()
    def apply(self):
        state=self.history.current
        if self.window.apply_creative(state['design'],state['dashboard'],self.saved): self.accept()
