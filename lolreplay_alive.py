"""ALIVE configuration; independent of capture, playback and creative profiles."""
DEFAULTS={'enabled':True,'hover':'glow','press':'ripple','navigation':'slide','save':'pulse','ambient':'off',
          'duration':220,'intensity':35,'easing':'out','fps':30,'ambient_speed':100,
          'wallpaper_motion':True,'wallpaper_speed':100,'wallpaper_fps':24,'wallpaper_dim':55,
          'wallpaper_fit':'fill','panel_opacity':100,'pause_recording':False}
CHOICES={'hover':('off','glow','wash','underline'),'press':('off','ripple','flash','outline'),
         'navigation':('off','slide','fade','sweep'),'save':('off','pulse','outline'),
         'ambient':('off','orbit','particles','scan','drift'),'easing':('linear','out','inout'),
         'fps':(15,24,30,60),'wallpaper_fps':(12,24,30),'wallpaper_fit':('fill','fit')}
RANGES={'duration':(80,800),'intensity':(0,100),'ambient_speed':(25,200),'wallpaper_speed':(25,200),'wallpaper_dim':(0,85),'panel_opacity':(55,100)}
BOOLS=('enabled','wallpaper_motion','pause_recording')
VIDEO_EXTENSIONS=('.mp4','.webm','.mkv','.mov','.m4v')
IMAGE_EXTENSIONS=('.png','.jpg','.jpeg','.bmp','.gif','.webp','.apng')
def validated(raw):
    out=DEFAULTS.copy()
    if not isinstance(raw,dict): return out
    for key,choices in CHOICES.items():
        value=raw.get(key)
        if any(type(value) is type(choice) and value==choice for choice in choices): out[key]=value
    for key,(lo,hi) in RANGES.items():
        value=raw.get(key)
        if type(value) is int and lo<=value<=hi: out[key]=value
    for key in BOOLS:
        if type(raw.get(key)) is bool: out[key]=raw[key]
    return out

def wallpaper(raw):
    if not isinstance(raw,dict): raw={}
    mode=raw.get('mode'); path=raw.get('path')
    if mode not in ('image','video') or not isinstance(path,str) or not path or '\x00' in path or len(path)>4096: return {'mode':'none','path':''}
    return {'mode':mode,'path':path}

def easing(value,curve):
    x=max(0.,min(1.,value))
    if curve=='out': return 1-(1-x)**3
    if curve=='inout': return x*x*(3-2*x)
    return x

def allowed(values,foreground,recording):
    return bool(values['enabled'] and foreground and not (values['pause_recording'] and recording))
