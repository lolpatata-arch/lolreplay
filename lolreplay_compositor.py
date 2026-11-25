"""Session detection and opt-in native Niri key binding."""
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def detect(env=None):
    env=os.environ if env is None else env
    desktop=re.split(r'[:;]',env.get('XDG_CURRENT_DESKTOP','').lower())
    if env.get('NIRI_SOCKET') and not env.get('HYPRLAND_INSTANCE_SIGNATURE'): return 'niri'
    if env.get('HYPRLAND_INSTANCE_SIGNATURE') and not env.get('NIRI_SOCKET'): return 'hyprland'
    if 'niri' in desktop: return 'niri'
    if 'hyprland' in desktop: return 'hyprland'
    return 'unknown'


def capture(cfg, env=None):
    if detect(env)=='niri':
        mode=cfg.get('niri_capture','portal')
        if mode not in ('portal','screen'): raise RuntimeError('Invalid Niri capture mode')
        return mode
    # Keep the original capture configuration, including on unknown sessions.
    return str(cfg.get('capture','screen'))


def binding_line(executable):
    return 'F8 repeat=false hotkey-overlay-title="lolreplay: Save clip" { spawn '+json.dumps(str(executable),ensure_ascii=False)+' "save"; }'


def candidate(text, executable):
    line=binding_line(executable)
    if line in text: return text
    # Conservative: refuse ambiguous / included configurations instead of
    # accidentally overriding keys in another file or a commented block.
    if re.search(r'(?im)^\s*(?:/-\s*)?include\b',text):
        raise ValueError('Config uses includes. Add the printed binding to your active binds block manually.')
    if re.search(r'(?im)^\s*(?:"F8"|F8)\s*(?=[{\s])',text):
        raise ValueError('F8 already exists; refusing to overwrite it.')
    if '/*' in text:
        raise ValueError('Config contains block comments; add the printed binding manually.')
    matches=list(re.finditer(r'(?m)^binds\s*\{[ \t]*(?://[^\n]*)?\n',text))
    if len(matches)!=1:
        raise ValueError('Cannot identify one top-level binds block; add the printed binding manually.')
    pos=matches[0].end()
    return text[:pos]+'    '+line+'\n'+text[pos:]


def install_niri_bind(executable, path=None):
    if detect()!='niri': raise ValueError('Run this from a Niri session. Hyprland config is untouched.')
    if not shutil.which('niri'): raise ValueError('niri executable not found')
    conf=Path(path or os.environ.get('NIRI_CONFIG') or (Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'niri/config.kdl')).expanduser().absolute()
    if conf.is_symlink() or not conf.is_file(): raise ValueError('Config not a regular user file; specify your actual config with --config or add the binding manually.')
    old=conf.read_text(); new=candidate(old,executable)
    if new==old: return 'F8 already configured: '+str(conf)
    def validate(p):
        result=subprocess.run(['niri','--config',str(p),'validate'],capture_output=True,text=True,timeout=15)
        if result.returncode: raise ValueError('Niri rejected config: '+(result.stderr or result.stdout).strip())
    validate(conf)
    fd,tmp=tempfile.mkstemp(prefix='.lolreplay-',suffix='.kdl',dir=conf.parent)
    try:
        with os.fdopen(fd,'w') as f: f.write(new)
        path_tmp=Path(tmp); path_tmp.chmod(conf.stat().st_mode & 0o777)
        validate(path_tmp)
        if conf.read_text()!=old: raise ValueError('Config changed during validation; retry.')
        backup=conf.with_name(conf.name+'.bak-lolreplay-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copy2(conf,backup)
        path_tmp.replace(conf)
        return 'F8 configured. Backup: '+str(backup)
    finally:
        Path(tmp).unlink(missing_ok=True)
