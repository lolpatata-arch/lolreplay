"""Creative Studio: bounded, local, declarative shell designs."""
import re
from copy import deepcopy
import lolreplay_dashboard as dashboard

DEFAULTS={
    'dock':'bottom','hub':'top','hub_visible':True,'hub_brand':True,'hub_status':True,'hub_hotkey':True,
    'dock_mode':'auto','dock_labels':'auto','dock_size':100,'font':'default','weight':'default',
    'radius':-1,'gap':-1,'margin':-1,'opacity':100,'media_layout':'auto',
    'palette':{},'widget_styles':{},
}
CHOICES={'dock':('bottom','top','left','right'),'hub':('top','bottom'),'dock_mode':('auto','floating','full'),
         'dock_labels':('auto','icons','text'),'font':('default','sans-serif','serif','monospace'),
         'weight':('default','normal','medium','bold'),'media_layout':('auto','horizontal','vertical')}
RANGES={'dock_size':(80,130),'radius':(-1,24),'gap':(-1,24),'margin':(-1,24),'opacity':(55,100)}
BOOLS=('hub_visible','hub_brand','hub_status','hub_hotkey')
COLORS=('bg','surface','border','accent')

def color(value,dark=False):
    if not isinstance(value,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',value): return ''
    if dark and max(int(value[i:i+2],16) for i in (1,3,5))>120: return ''
    return value.lower()

def validated(raw):
    out=deepcopy(DEFAULTS)
    if not isinstance(raw,dict): return out
    for key,choices in CHOICES.items():
        if raw.get(key) in choices: out[key]=raw[key]
    for key,(lo,hi) in RANGES.items():
        value=raw.get(key)
        if type(value) is int and lo<=value<=hi: out[key]=value
    for key in BOOLS:
        if type(raw.get(key)) is bool: out[key]=raw[key]
    palette=raw.get('palette')
    if isinstance(palette,dict):
        out['palette']={key:c for key in COLORS if (c:=color(palette.get(key),key!='accent'))}
    styles=raw.get('widget_styles')
    if isinstance(styles,dict):
        for key,style in styles.items():
            if key not in dashboard.IDS or not isinstance(style,dict): continue
            entry={}
            if c:=color(style.get('color'),True): entry['color']=c
            if type(style.get('radius')) is int and 0<=style['radius']<=24: entry['radius']=style['radius']
            if entry: out['widget_styles'][key]=entry
    return out

PRESETS={
    'OVERDRIVE':{},
    'SHADOW':{'dock':'left','dock_labels':'icons','dock_mode':'floating','radius':16,'gap':8,'margin':10,'palette':{'bg':'#080809','surface':'#151419','accent':'#d7193c'}},
    'MINIMAL':{'dock':'top','hub':'bottom','dock_mode':'full','radius':4,'gap':6,'margin':8,'palette':{'bg':'#101010','surface':'#202020','accent':'#bbbbbb'}},
    'CRYSTAL':{'dock':'right','dock_mode':'floating','radius':20,'gap':14,'opacity':75,'palette':{'bg':'#101827','surface':'#27344a','accent':'#7899ee'}},
}

def snapshot(design,layout):
    return {'design':validated(design),'dashboard':dashboard.validated(layout)}

def profiles(raw):
    out={}
    if isinstance(raw,dict):
        for name,entry in raw.items():
            if len(out)>=16: break
            if not isinstance(name,str) or not 1<=len(name.strip())<=48 or not isinstance(entry,dict): continue
            out[name.strip()]=snapshot(entry.get('design'),entry.get('dashboard'))
    return out

def merge_ui(data,design,layout,saved):
    return {**(data if isinstance(data,dict) else {}),'creative_design':validated(design),
            'dashboard_layout':dashboard.validated(layout),'creative_profiles':profiles(saved)}

def effective_hub(design,layout,page):
    # Other pages always retain quick controls; Replay can hide the hub if capture exists.
    return design['hub_visible'] or page!=0 or not layout['widgets']['capture']['visible']

def mix(fg,bg,percent):
    return '#'+''.join(f'{round((int(fg[i:i+2],16)*percent+int(bg[i:i+2],16)*(100-percent))/100):02x}' for i in (1,3,5))

class History:
    def __init__(self,value): self.current=deepcopy(value); self.past=[]; self.future=[]
    def push(self,value):
        if value!=self.current:
            self.past.append(deepcopy(self.current)); self.past=self.past[-64:]; self.current=deepcopy(value); self.future=[]
    def undo(self):
        if self.past: self.future.append(deepcopy(self.current)); self.current=self.past.pop()
    def redo(self):
        if self.future: self.past.append(deepcopy(self.current)); self.current=self.future.pop()
