"""Validated local dashboard layout, independent of Qt and the recorder."""
from collections import Counter
from datetime import datetime, timedelta

IDS=('hero','capture','session','gallery','favorites','storage','latest','today','week','size','games','top_game','longest','quality','audio','mic','buffer','duration','quick_save','hotkey')
WIDTHS={key:1 for key in IDS}
WIDTHS.update(hero=2,session=3,gallery=3,latest=2,week=2)
GROUPS={
    'Capture':('hero','capture','session','quality','audio','mic','buffer','duration','quick_save','hotkey'),
    'Media library':('gallery','favorites','latest','today','week','size','games','top_game','longest'),
    'System':('storage',),
}
NAMES=dict(zip(IDS,('Replay background','Capture controls','CAPTURE SESSION','Recent clips','Favorites','Storage','Latest capture','Clips today','Seven-day activity','Library size','Recorded games','Most recorded game','Longest indexed clip','Capture quality','Audio routing','Microphone','Replay buffer','Clip length','Quick save','Global replay shortcut')))
MOBILE_ORDER=('capture','hero')+IDS[2:]
HEIGHTS=('compact','normal','large')


def defaults():
    return {'order':list(IDS),'custom_order':False,'widgets':{key:{'visible':key in IDS[:4],'width':WIDTHS[key],'height':'normal'} for key in IDS}}


def validated(raw):
    result=defaults()
    if not isinstance(raw,dict): return result
    order=raw.get('order')
    if isinstance(order,list):
        clean=[]
        for key in order:
            if isinstance(key,str) and key in IDS and key not in clean: clean.append(key)
        result['order']=clean+[key for key in IDS if key not in clean]
    result['custom_order']=result['order']!=list(IDS) or raw.get('custom_order') is True
    entries=raw.get('widgets')
    if isinstance(entries,dict):
        for key,entry in entries.items():
            if key not in IDS or not isinstance(entry,dict): continue
            target=result['widgets'][key]
            if type(entry.get('visible')) is bool: target['visible']=entry['visible']
            if type(entry.get('width')) is int and entry['width'] in (1,2,3): target['width']=entry['width']
            if entry.get('height') in HEIGHTS: target['height']=entry['height']
    return result


def change(raw,key,**updates):
    value=validated(raw)
    if key in IDS: value['widgets'][key].update(updates)
    return validated(value)


def move(raw,key,target,stacked=False):
    value=validated(raw); order=value['order']
    if key not in IDS or target not in IDS or key==target: return value
    if stacked and not value['custom_order']: order[:]=list(MOBILE_ORDER)
    value['custom_order']=True
    position=order.index(target); order.remove(key); order.insert(position,key)
    return value


def step(raw,key,direction,stacked=False):
    value=validated(raw); visible=list(positions(value,stacked))
    if key not in visible or direction not in (-1,1): return value
    target=visible.index(key)+direction
    return move(value,key,visible[target],stacked) if 0<=target<len(visible) else value


def positions(raw,stacked=False):
    value=validated(raw); order=value['order']
    if stacked and not value['custom_order']: order=list(MOBILE_ORDER)
    row=col=0; result={}
    for key in order:
        item=value['widgets'][key]
        if not item['visible']: continue
        width=1 if stacked else item['width']
        columns=1 if stacked else 3
        if col+width>columns: row+=1; col=0
        result[key]=(row,col,1,width)
        col+=width
        if col==columns: row+=1; col=0
    return result


def library_summary(files, metadata, durations, today=None):
    """Existing snapshot only; no filesystem reads. Calendar dates are local."""
    today=today or datetime.now().date()
    days=[today-timedelta(days=offset) for offset in range(6,-1,-1)]
    counts=Counter(); games=Counter(); longest=None; longest_duration=-1
    for key in files:
        path,mtime,size=key
        try: counts[datetime.fromtimestamp(mtime/1_000_000_000).date()]+=1
        except (ValueError,OverflowError,OSError): pass
        game=metadata(path)[1]
        if game: games[game]+=1
        duration=durations.get(key)
        if isinstance(duration,(int,float)) and duration>longest_duration:
            longest=key; longest_duration=duration
    top=sorted(games,key=lambda game:(-games[game],game.casefold(),game))
    return {'days':tuple(days),'counts':tuple(counts[day] for day in days),'games':len(games),
            'top_game':top[0] if top else '', 'top_count':games[top[0]] if top else 0,
            'longest':longest,'longest_duration':longest_duration if longest is not None else None}
