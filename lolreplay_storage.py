"""Guard a selected library against an unmounted or replaced disk."""
import ctypes
import json
import os
from pathlib import Path
import shutil
import tempfile
import uuid

HOME=Path.home()
CONFIG=HOME/'.config/crimson-clips/config.json'
STAGING=HOME/'.local/state/crimson-clips/recovery'
MARKER='.lolreplay-library-id'

def validate_config(cfg):
    """Reject invalid persisted values without silently resetting user settings."""
    if not isinstance(cfg,dict): raise ValueError('Configuration must be a JSON object')
    for key,low,high in [('buffer_seconds',30,1200),('save_seconds',2,1200),('fps',1,240),('bitrate_kbps',100,200000)]:
        if key in cfg and (type(cfg[key]) is not int or not low<=cfg[key]<=high):
            raise ValueError(f'Invalid configuration: {key} ({low}–{high})')
    if cfg.get('save_seconds',30)>cfg.get('buffer_seconds',1200): raise ValueError('Clip duration exceeds replay buffer')
    for key in ('output_dir','capture','microphone_source','audio_output'):
        if key in cfg and (not isinstance(cfg[key],str) or not cfg[key].strip() or '\x00' in cfg[key]): raise ValueError('Invalid configuration: '+key)
    if 'microphone' in cfg and type(cfg['microphone']) is not bool: raise ValueError('Invalid microphone setting')
    if cfg.get('niri_capture','portal') not in ('portal','screen'): raise ValueError('Invalid Niri capture mode')
    if cfg.get('rate_control','auto') not in ('auto','cbr','cqp'): raise ValueError('Invalid rate control')
    token=cfg.get('library_id')
    if token is not None and (not isinstance(token,str) or len(token)!=32 or any(c not in '0123456789abcdef' for c in token)): raise ValueError('Invalid library ID; repair the configuration before use')
    return cfg

def read_config():
    try: return validate_config(json.loads(CONFIG.read_text())) if CONFIG.exists() else {}
    except (ValueError,UnicodeError) as exc: raise OSError(f'Invalid configuration ({CONFIG}): {exc}') from exc

def staging():
    STAGING.mkdir(parents=True,exist_ok=True,mode=0o700)
    return STAGING

def register(path):
    path=Path(path).resolve(strict=True)
    if not path.is_dir(): raise ValueError('Not a directory')
    if path==staging() or staging() in path.parents: raise ValueError('Choose a folder outside recovery storage')
    marker=path/MARKER
    try:
        with marker.open('x') as f: f.write(uuid.uuid4().hex+'\n')
    except FileExistsError: pass
    token=marker.read_text().strip()
    if len(token)!=32 or any(c not in '0123456789abcdef' for c in token): raise ValueError('Invalid library marker')
    return token

def check(path,token=None):
    path=Path(path)
    if not path.is_dir(): raise OSError(f'Library unavailable: {path}')
    if token:
        try: valid=(path/MARKER).read_text().strip()==token
        except OSError: valid=False
        if not valid: raise OSError(f'Library disk disconnected or changed: {path}')
    if not os.access(path,os.W_OK|os.X_OK): raise OSError(f'Library not writable: {path}')
    return path

def config_check(path):
    cfg=read_config()
    configured=Path(cfg.get('output_dir',HOME/'Videos/CrimsonClips')).expanduser()
    if Path(path)!=configured: raise OSError('Library changed; select the clip again')
    return check(path,cfg.get('library_id'))

def publish(source,target,token=None):
    """Copy to a hidden temporary file, then publish atomically without overwriting.
    A directory FD pins the destination even if its mount path is replaced."""
    source=Path(source); target=Path(target)
    check(target.parent,token)
    fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
    temp='.lolreplay-transfer-'+uuid.uuid4().hex+'.part'
    created=False
    try:
        if token:
            with os.fdopen(os.open(MARKER,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd),'r') as f:
                if f.read().strip()!=token: raise OSError('Library changed')
        initial=signature(source)
        if initial[2]<=0: raise ValueError('Empty clip')
        out=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644,dir_fd=fd); created=True
        with os.fdopen(out,'wb') as dst,source.open('rb') as src:
            shutil.copyfileobj(src,dst,1024*1024); dst.flush(); os.fsync(dst.fileno())
        if signature(source)!=initial: raise OSError('Source changed during transfer')
        check(target.parent,token)
        if os.stat(target.parent).st_dev!=os.fstat(fd).st_dev or os.stat(target.parent).st_ino!=os.fstat(fd).st_ino: raise OSError('Destination changed')
        libc=ctypes.CDLL(None,use_errno=True)
        rename=libc.renameat2; rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]; rename.restype=ctypes.c_int
        if rename(fd,os.fsencode(temp),fd,os.fsencode(target.name),1):
            err=ctypes.get_errno(); raise OSError(err,os.strerror(err),str(target))
        created=False
        try: os.fsync(fd)
        except OSError: pass
        check(target.parent,token)
    finally:
        if created:
            try: os.unlink(temp,dir_fd=fd)
            except OSError: pass
        os.close(fd)
    source.unlink()


def signature(path,dir_fd=None):
    import stat
    s=os.stat(path,dir_fd=dir_fd,follow_symlinks=False)
    if not stat.S_ISREG(s.st_mode): raise ValueError('Expected a regular clip file')
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def replace_clip(source,target,expected,token=None):
    """Commit a completed export on the original filesystem, checking identity first."""
    source=Path(source); target=Path(target)
    if source==target: raise ValueError('Export must be a different file')
    check(target.parent,token)
    fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
    temp='.lolreplay-replace-'+uuid.uuid4().hex+'.part'; created=False
    try:
        def verify():
            check(target.parent,token)
            if token:
                with os.fdopen(os.open(MARKER,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd),'r') as f:
                    if f.read().strip()!=token: raise OSError('Library changed')
            s=os.stat(target.parent); pinned=os.fstat(fd)
            if (s.st_dev,s.st_ino)!=(pinned.st_dev,pinned.st_ino): raise OSError('Destination changed')
            if signature(target.name,fd)!=expected: raise OSError('Original clip changed; refusing to overwrite')
        verify()
        initial=signature(source)
        if initial[2]<=0: raise ValueError('Empty export')
        mode=os.stat(target.name,dir_fd=fd,follow_symlinks=False).st_mode & 0o777
        out=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode,dir_fd=fd); created=True
        with os.fdopen(out,'wb') as dst,source.open('rb') as src:
            shutil.copyfileobj(src,dst,1024*1024); dst.flush(); os.fsync(dst.fileno())
        if signature(source)!=initial: raise OSError('Export changed during transfer')
        verify()
        os.replace(temp,target.name,src_dir_fd=fd,dst_dir_fd=fd); created=False
        try: os.fsync(fd)
        except OSError: pass
        check(target.parent,token)
    finally:
        if created:
            try: os.unlink(temp,dir_fd=fd)
            except OSError: pass
        os.close(fd)
    source.unlink()
