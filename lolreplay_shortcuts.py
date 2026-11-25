"""Portable shortcut preferences and conservative compositor configuration."""
import re, json, os, shlex, subprocess, tempfile, shutil, datetime
from pathlib import Path
import lolreplay_compositor as compositor

DEFAULTS={'replay':'Ctrl+1','clips':'Ctrl+2','editor':'Ctrl+3','settings':'Ctrl+4','search':'Ctrl+F','rename':'F2','play':'Space','fullscreen':'F11','back':'Left','forward':'Right','exit_fullscreen':'Esc','mark_in':'','mark_out':'','export':'','mute':'','refresh':'','start':'','stop':''}
LABELS={'replay':'Replay','clips':'Clips','editor':'Editor','settings':'Settings','search':'Search clips','rename':'Rename…','play':'Play / pause','fullscreen':'Full screen','back':'Seek backward','forward':'Seek forward','exit_fullscreen':'Exit full screen','mark_in':'Set in at playhead','mark_out':'Set out at playhead','export':'Save changes','mute':'Mute','refresh':'Refresh','start':'Start replay','stop':'Stop'}
DEFAULTS.update(dict.fromkeys(('edit_clip','external','copy_path','trash','folder','reset_trim','add_music','remove_music','cancel_export'),''))
LABELS.update({'edit_clip':'Edit clip','external':'Open externally','copy_path':'Copy file path','trash':'Move to trash…','folder':'Open folder','reset_trim':'Reset trim','add_music':'Add music…','remove_music':'Remove music','cancel_export':'Cancel export'})
MODS=('Ctrl','Alt','Shift','Meta')
KEYS={'Space','Left','Right','Up','Down','Esc','Tab','Backspace','Delete','Insert','Home','End','PgUp','PgDown','Return','Enter','Pause','Print'}

def normalize(value,global_key=False):
    if not isinstance(value,str): raise ValueError('Invalid shortcut')
    if not value: return ''
    parts=value.split('+'); mods=parts[:-1]; key=parts[-1]
    if any(m not in MODS for m in mods) or len(set(mods))!=len(mods) or not (key in KEYS or re.fullmatch(r'[A-Z0-9]|F(?:[1-9]|[12][0-9]|3[0-5])',key)):
        raise ValueError('Choose a single key or a combination with Ctrl, Alt, Shift or Meta.')
    if global_key and key in ('Esc','Tab','Return','Enter','Backspace','Delete','Space','Left','Right','Up','Down') and not mods:
        raise ValueError('Use modifiers for this global key to avoid intercepting ordinary typing.')
    if global_key and re.fullmatch(r'[A-Z0-9]',key) and not mods: raise ValueError('Use modifiers for global letters or digits.')
    return '+'.join([m for m in MODS if m in mods]+[key])

def validate(mapping,global_key='F8'):
    seen={global_key} if global_key else set(); result={}
    for action,default in DEFAULTS.items():
        key=normalize(mapping.get(action,default))
        # Escape is an unconditional safety exit in fullscreen.
        if key=='Esc' and action!='exit_fullscreen': raise ValueError('Escape is reserved for leaving full screen.')
        if key and key in seen: raise ValueError('Shortcut already in use: '+key)
        if key: seen.add(key)
        result[action]=key
    return result

def load(data):
    try:
        g=normalize(data.get('replay_hotkey','F8'),True)
        return validate(data.get('shortcuts',{}),g),g
    except (ValueError,AttributeError,TypeError): return DEFAULTS.copy(),'F8'

def compositor_key(key,session):
    key=normalize(key,True)
    if not key: return ''
    *mods, k=key.split('+')
    native={'Space':'space','Esc':'Escape','PgUp':'Prior','PgDown':'Next','Enter':'KP_Enter','Print':'Print'}.get(k,k)
    if session=='hyprland': return ' + '.join([{'Ctrl':'CTRL','Alt':'ALT','Shift':'SHIFT','Meta':'SUPER'}[m] for m in mods]+[native])
    return '+'.join([('Super' if m=='Meta' else m) for m in mods]+[native])

def snippet(key,session,exe):
    k=compositor_key(key,session)
    if not k: return ''
    if session=='niri': return k+' repeat=false hotkey-overlay-title="lolreplay: Save clip" { spawn '+json.dumps(str(exe),ensure_ascii=False)+' "save"; }'
    if session=='hyprland': return 'hl.bind('+json.dumps(k)+', hl.dsp.exec_cmd('+json.dumps(shlex.quote(str(exe))+' save',ensure_ascii=False)+'))'
    raise ValueError('Unsupported compositor')

BEGIN='-- BEGIN CRIMSON CLIPS F8'; END='-- END CRIMSON CLIPS F8'

def hypr_candidate(text,old_key,new_key,exe):
    if text.count(BEGIN)!=1 or text.count(END)!=1: raise ValueError('Cannot identify the original lolreplay binding. Use manual setup.')
    start=text.index(BEGIN); end=text.index(END,start)+len(END)
    block=text[start:end]; old_native=compositor_key(old_key,'hyprland')
    lines=[x.strip() for x in block.splitlines()[1:-1] if x.strip() and not x.lstrip().startswith('--')]
    expected=snippet(old_key,'hyprland',exe)
    # Accept only the original installer-generated block or our own exact binding.
    if lines!=([expected] if expected else []):
        legacy_cmd=shlex.quote(str(Path(exe).with_name('crimson-clips')))+' save > '+shlex.quote(str(Path.home()/'.local/state/crimson-clips/f8.log'))+' 2>&1'
        legacy=['hl.unbind("F8")','hl.bind("F8", hl.dsp.exec_cmd('+json.dumps(legacy_cmd,ensure_ascii=False)+'))']
        if old_native!='F8' or lines!=legacy: raise ValueError('Original block was modified. Use manual setup.')
    body=snippet(new_key,'hyprland',exe)
    return text[:start]+BEGIN+'\n'+(body+'\n' if body else '')+END+text[end:]

def niri_candidate(text,old_key,new_key,exe):
    if re.search(r'(?im)^\s*(?:/-\s*)?include\b',text) or '/*' in text: raise ValueError('Complex Niri configuration. Use manual setup.')
    old=snippet(old_key,'niri',exe); new=snippet(new_key,'niri',exe)
    if old:
        pattern=r'(?m)^([ \t]*)'+re.escape(old)+r'[ \t]*$'
        matches=list(re.finditer(pattern,text))
        if len(matches)!=1: raise ValueError('Cannot identify the original lolreplay binding. Use manual setup.')
        m=matches[0]; return text[:m.start()]+(m.group(1)+new if new else '')+text[m.end():]
    matches=list(re.finditer(r'(?m)^binds\s*\{[ \t]*(?://[^\n]*)?\n',text))
    if len(matches)!=1: raise ValueError('Cannot identify the Niri binds block. Use manual setup.')
    p=matches[0].end(); return text[:p]+'    '+new+'\n'+text[p:] if new else text

def apply_global(old_key,new_key,exe,session=None,path=None):
    session=session or compositor.detect(); old_key=normalize(old_key,True); new_key=normalize(new_key,True)
    if old_key==new_key: return ''
    root=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
    if session=='hyprland':
        conf=Path(path or root/'hypr/hyprland.lua')
        change=hypr_candidate
    elif session=='niri':
        conf=Path(path or os.environ.get('NIRI_CONFIG') or root/'niri/config.kdl'); change=niri_candidate
    else: raise ValueError('Unsupported compositor. Configure the global binding manually.')
    if conf.is_symlink() or not conf.is_file(): raise ValueError('Configuration is not a regular file. Use manual setup.')
    text=conf.read_text(); new=change(text,old_key,new_key,exe)
    if session=='hyprland' and new_key:
        check=subprocess.run(['hyprctl','binds','-j'],capture_output=True,text=True,timeout=5,check=True)
        rows=json.loads(check.stdout); *mods,k=new_key.split('+'); k={'Space':'space','Esc':'Escape','PgUp':'Prior','PgDown':'Next','Enter':'KP_Enter'}.get(k,k)
        mask=sum({'Ctrl':4,'Alt':8,'Shift':1,'Meta':64}[m] for m in mods)
        if not isinstance(rows,list): raise ValueError('Cannot verify active Hyprland bindings.')
        for row in rows:
            if not isinstance(row,dict) or 'modmask' not in row or 'key' not in row: raise ValueError('Cannot verify active Hyprland bindings.')
            if row['modmask']==mask and str(row['key']).casefold()==k.casefold(): raise ValueError('Global shortcut already in use.')
            if row['modmask']==mask and not row['key'] and row.get('keycode'): raise ValueError('Cannot verify a keycode binding; use manual setup.')
    fd,tmp=tempfile.mkstemp(prefix='.lolreplay-',suffix=conf.suffix,dir=conf.parent)
    try:
        with os.fdopen(fd,'w') as f: f.write(new)
        staged=Path(tmp); staged.chmod(conf.stat().st_mode&0o777)
        if session=='niri':
            for p in (conf,staged):
                result=subprocess.run(['niri','--config',str(p),'validate'],capture_output=True,text=True,timeout=10)
                if result.returncode: raise ValueError('Niri rejected configuration: '+(result.stderr or result.stdout).strip())
        if conf.read_text()!=text: raise ValueError('Configuration changed; retry.')
        backup=conf.with_name(conf.name+'.bak-lolreplay-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')); shutil.copy2(conf,backup); staged.replace(conf)
        return str(backup)
    finally: Path(tmp).unlink(missing_ok=True)
