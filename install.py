#!/usr/bin/env python3
"""Install lolreplay frontend and compatible recorder; preserve compositor configuration."""
import argparse
import fcntl
import hashlib
import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import subprocess
import tempfile

HOME=Path.home()
HERE=Path(__file__).resolve().parent
BIN=HOME/'.local/bin'
DATA=Path(os.environ.get('XDG_DATA_HOME', str(HOME/'.local/share')))
CONF=Path(os.environ.get('XDG_CONFIG_HOME', str(HOME/'.config')))
LOG=HOME/'.local/state/crimson-clips/f8.log'
BEGIN='-- BEGIN CRIMSON CLIPS F8'
END='-- END CRIMSON CLIPS F8'
PROGRAM_FILES=('lolreplay','lolreplay-ui','lolreplay_editor.py','lolreplay_widgets.py','lolreplay_icons.py','lolreplay_i18n.py','lolreplay_preferences.py','lolreplay_shortcuts.py','lolreplay_export.py','lolreplay_storage.py','lolreplay_drives.py','lolreplay_audio.py','lolreplay_compositor.py','lolreplay_performance.py','crimson-clips','lolreplay_updater.py','lolreplay_update_ui.py')

def stamp(): return datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
def write(path, content, mode=None, backup=True):
    path=path.expanduser(); path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_text()==content: return
    if path.exists() and backup:
        b=path.with_name(path.name+'.bak-'+stamp()); shutil.copy2(path,b); print('Backup:',b)
    oldmode=path.stat().st_mode & 0o777 if path.exists() else 0o644
    temp=path.with_name(path.name+'.tmp-'+stamp()); temp.write_text(content); temp.chmod(mode if mode is not None else oldmode); temp.replace(path)

def install(expected=None):
    lockpath=HOME/'.local/state/crimson-clips/engine.lock'
    lockpath.parent.mkdir(parents=True,exist_ok=True)
    with lockpath.open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ValueError('A recorder operation is running. Retry after it finishes.')
        if expected is not None:
            installed=subprocess.run([str(BIN/'lolreplay'),'--version'],capture_output=True,text=True,timeout=10)
            if installed.returncode or installed.stdout.strip()!='lolreplay '+expected:
                raise ValueError('Installed version changed; check for updates again.')
        preflight()
        transactional_install()

def preflight():
    for executable in ('gpu-screen-recorder','gsr-cli','ffmpeg','ffprobe','pactl'):
        if not shutil.which(executable): raise ValueError('Missing dependency: '+executable)
    old=BIN/'crimson-clips'
    if old.is_file():
        status=subprocess.run([str(old),'status'],capture_output=True,timeout=10)
        if status.returncode!=1: raise ValueError('Stop replay first; cannot confirm recorder is stopped.')

def transactional_install():
    # Snapshot only installer-owned paths, never recordings or user preferences.
    raw=(HERE/'lolreplay.png').read_bytes()
    icons=DATA/'icons/hicolor'
    icon_dir=icons/'512x512/apps'
    digest=hashlib.sha256(raw).hexdigest()[:12]
    paths=[BIN/n for n in PROGRAM_FILES]+[icon_dir/n for n in (f'lolreplay-{digest}.png','lolreplay.png','crimson-clips.png')]+[icons/'scalable/apps'/n for n in ('lolreplay.svg','crimson-clips.svg')]+[DATA/'applications/crimson-clips.desktop']
    with tempfile.TemporaryDirectory(prefix='lolreplay-install-') as backup:
        saved={}
        for i,path in enumerate(paths):
            if path.is_symlink() or path.exists():
                if not path.is_symlink() and not path.is_file(): raise ValueError('Unexpected install path: '+str(path))
                copy=Path(backup)/str(i); shutil.copy2(path,copy,follow_symlinks=False); saved[path]=copy
        try:
            install_locked()
        except BaseException:
            for path in paths:
                if path in saved:
                    path.parent.mkdir(parents=True,exist_ok=True)
                    copy=saved[path]; tmp=path.with_name(path.name+'.rollback-'+stamp()); shutil.copy2(copy,tmp,follow_symlinks=False); tmp.replace(path)
                elif path.is_file() or path.is_symlink(): path.unlink()
            raise

def install_locked():
    # Create only the default local directory; never recreate an absent custom drive.
    from lolreplay_storage import read_config
    try: cfg=read_config()
    except OSError: cfg=None  # Preserve damaged settings; diagnostics can report them.
    default=HOME/'Videos/CrimsonClips'
    if cfg is not None and not cfg.get('library_id') and Path(cfg.get('output_dir',str(default))).expanduser()==default:
        default.mkdir(parents=True,exist_ok=True)
    # Preserve original executable and config; install the updated compatible engine.
    for name in PROGRAM_FILES:
        write(BIN/name,(HERE/name).read_text(),0o755)
    raw=(HERE/'lolreplay.png').read_bytes()
    icon_root=DATA/'icons/hicolor'
    icon_dir=icon_root/'512x512/apps'
    icon_dir.mkdir(parents=True,exist_ok=True)
    # A fresh path invalidates caches keyed by the old filename.
    digest=hashlib.sha256(raw).hexdigest()[:12]
    icon=icon_dir/f'lolreplay-{digest}.png'
    for target in (icon,icon_dir/'lolreplay.png',icon_dir/'crimson-clips.png'):
        if not target.exists() or target.read_bytes()!=raw:
            if target.exists(): shutil.copy2(target,target.with_name(target.name+'.bak-'+stamp()))
            temp=target.with_name(target.name+'.tmp-'+stamp()); temp.write_bytes(raw); temp.chmod(0o644); temp.replace(target)
    # Retire old app-specific SVGs, preserving a backup; themed lookup now uses the PNG aliases.
    for name in ('lolreplay.svg','crimson-clips.svg'):
        legacy=icon_root/'scalable/apps'/name
        if legacy.is_file() or legacy.is_symlink():
            backup=legacy.with_name(legacy.name+'.bak-'+stamp()); legacy.rename(backup); print('Backup:',backup)
    icon_entry=str(icon)
    # Keep the original desktop entry ID for existing dock pins, but update the visible name.
    exe=str(BIN/'lolreplay').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')
    write(DATA/'applications/crimson-clips.desktop',f'[Desktop Entry]\nType=Application\nName=lolreplay\nComment=Local instant replay\nExec="{exe}"\nIcon={icon_entry}\nTerminal=false\nCategories=AudioVideo;Video;\nStartupNotify=true\n')
    for executable,args in (('update-desktop-database',[str(DATA/'applications')]),('gtk-update-icon-cache',['-f','-t',str(icon_root)])):
        if shutil.which(executable):
            try: subprocess.run([executable,*args],capture_output=True,timeout=5,check=False)
            except (OSError,subprocess.SubprocessError): pass
    print('lolreplay 1.2.0 installed. Hyprland and experimental Niri support; existing clips, settings and bindings unchanged.')

def check():
    import lolreplay_compositor as compositor
    print('Linux:', sys.platform, '| Python:', sys.version.split()[0])
    print('Compositor:', compositor.detect(), '| Session:', os.environ.get('XDG_SESSION_TYPE','unknown'))
    missing=[]
    if not sys.platform.startswith('linux') or sys.version_info < (3,10): missing.append('Linux / Python 3.10+')
    for name in ('gpu-screen-recorder','gsr-cli','ffmpeg','ffprobe','pactl','lsblk','udisksctl','notify-send'):
        path=shutil.which(name); optional=name in ('lsblk','udisksctl','notify-send')
        print(name+':',path or ('missing (optional)' if optional else 'MISSING'))
        if not path and not optional: missing.append(name)
    try:
        from PySide6 import QtCore, QtWidgets, QtMultimedia, QtMultimediaWidgets
        print('PySide6 / Qt Multimedia: import OK; Qt', QtCore.qVersion())
    except (ImportError,OSError) as exc:
        print('PySide6 / Qt Multimedia: MISSING or broken:',exc); missing.append('PySide6 / Qt Multimedia')
    if compositor.detect() not in ('hyprland','niri'): print('Warning: compositor not in supported targets.')
    print('Prerequisite check only: GPU, Wayland plugins, audio, encoders and F8 require live testing.')
    return 1 if missing else 0

def main():
    parser=argparse.ArgumentParser(description='Install lolreplay or check prerequisites without modifying files.')
    parser.add_argument('--check',action='store_true'); parser.add_argument('--update',action='store_true'); parser.add_argument('--from-version'); args=parser.parse_args()
    if args.update and not args.from_version: parser.error('--update requires --from-version')
    if args.check: return check()
    try: install(args.from_version if args.update else None)
    except (OSError,ValueError,subprocess.SubprocessError) as e: print('ERROR:',e,file=sys.stderr); return 1
    return 0
if __name__=='__main__': sys.exit(main())
