"""Pure validation for playback routing and session mixer controls."""
import re

def device_preference(value):
    if value == 'auto': return value
    if isinstance(value,str) and 0<len(value)<=2048 and len(value)%2==0 and re.fullmatch('[0-9a-f]+',value):
        return value
    return 'auto'

def resolve_output(preference, devices, default):
    """Return chosen ID and whether a requested explicit output is missing."""
    preference=device_preference(preference)
    if preference!='auto' and preference in devices:
        return preference,False
    return default,preference!='auto'

def mixer_rows(data):
    """Parse current sink inputs; never expose recorder bridge or invalid IDs."""
    rows=[]
    if not isinstance(data,list): return rows
    for item in data:
        if not isinstance(item,dict): continue
        index=item.get('index')
        if type(index) is not int or not 0<=index<2**32: continue
        props=item.get('properties')
        if not isinstance(props,dict): continue
        name=props.get('application.name') or props.get('node.name') or props.get('media.name') or 'Audio stream'
        if not isinstance(name,str) or name.casefold().startswith('lolreplay_'): continue
        volume=item.get('volume')
        if not isinstance(volume,dict): continue
        levels=[v.get('value') for v in volume.values() if isinstance(v,dict)]
        levels=[v for v in levels if type(v) is int and 0<=v<=2**32-1]
        if not levels: continue
        rows.append((index,name[:160],round(max(levels)*100/65536),item.get('mute') is True))
    return rows[:128]

def volume_args(index,percent):
    if type(index) is not int or not 0<=index<2**32 or type(percent) is not int or not 0<=percent<=100:
        raise ValueError('Invalid mixer volume')
    return ['set-sink-input-volume',str(index),str(percent)+'%']

def mute_args(index,muted):
    if type(index) is not int or not 0<=index<2**32 or type(muted) is not bool:
        raise ValueError('Invalid mixer mute')
    return ['set-sink-input-mute',str(index),'1' if muted else '0']
