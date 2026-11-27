"""Validated local dashboard layout, independent of Qt and the recorder."""
IDS=('hero','capture','session','gallery','favorites','storage')
WIDTHS={'hero':2,'capture':1,'session':3,'gallery':3,'favorites':1,'storage':1}
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
    if stacked and not value['custom_order']: order[:]=['capture','hero','session','gallery','favorites','storage']
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
    if stacked and not value['custom_order']: order=['capture','hero','session','gallery','favorites','storage']
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
