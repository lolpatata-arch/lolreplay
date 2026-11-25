"""Session-only virtual microphone. No persistent PipeWire configuration."""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

STATE=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'lolreplay-audio.json'

def cmd(*args):
    p=subprocess.run(args,text=True,capture_output=True,timeout=8)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip() or 'Audio command failed')
    return p.stdout.strip()

def devices():
    return [(x['name'],x.get('description',x['name'])) for x in json.loads(cmd('pactl','-f','json','list','sources')) if not x['name'].endswith('.monitor') and not x['name'].startswith('lolreplay_')]

def gsr_device(name):
    for line in cmd('gpu-screen-recorder','--list-audio-devices').splitlines():
        key=line.split('|',1)[0].strip()
        if key in (name,'device:'+name): return key
    raise RuntimeError('Audio source not available in GPU Screen Recorder: '+name)

def outputs():
    return [(x['name'],x.get('description',x['name'])) for x in json.loads(cmd('pactl','-f','json','list','sinks')) if not x['name'].startswith('lolreplay_')]

def output_device(name):
    if name=='auto': return 'default_output'
    if name not in dict(outputs()): raise RuntimeError('Selected output unavailable: '+name)
    return gsr_device(name+'.monitor')

def module_rows():
    # The tab-separated interface provides the numeric ID even when JSON omits index.
    rows=[]
    for line in cmd('pactl','list','short','modules').splitlines():
        fields=line.split('\t')
        if len(fields)<3: fields=line.split(None,2)
        if len(fields)>=3 and fields[0].isdigit(): rows.append((fields[0],fields[1],fields[2]))
    return rows

def cleanup():
    if not STATE.exists(): return
    try:
        data=json.loads(STATE.read_text()); name=data['name']; ids=data.get('ids',[])
        if not isinstance(name,str) or not name.startswith('lolreplay_') or not isinstance(ids,list) or any(type(i) is not int for i in ids): raise ValueError('Invalid audio bridge state')
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
        raise RuntimeError(f'Cannot safely clean audio bridge: {STATE}. No audio modules unloaded. {exc}') from exc
    try: modules=module_rows()
    except Exception: return
    remaining=[]
    for idx in reversed(data.get('ids',[])):
        item=next((x for x in modules if x[0]==str(idx)),None)
        if item and item[1] in ('module-null-sink','module-loopback') and any(arg in item[2].split() for arg in ('sink='+name,'sink_name='+name)):
            try: cmd('pactl','unload-module',str(idx))
            except Exception: remaining.append(idx)
    if remaining:
        data['ids']=list(reversed(remaining)); STATE.write_text(json.dumps(data))
    else: STATE.unlink(missing_ok=True)

def bridge(source):
    cleanup()
    if STATE.exists(): raise RuntimeError('Previous audio bridge could not be cleaned up')
    old_sink=cmd('pactl','get-default-sink'); old_source=cmd('pactl','get-default-source')
    name='lolreplay_'+uuid.uuid4().hex[:12]
    data={'name':name,'ids':[]}; STATE.write_text(json.dumps(data))
    try:
        def load(*args):
            data['ids'].append(int(cmd('pactl','load-module',*args))); STATE.write_text(json.dumps(data))
        load('module-null-sink','sink_name='+name,'sink_properties=device.description=lolreplay_microphone','rate=48000','channels=2')
        if cmd('pactl','get-default-sink')==name: cmd('pactl','set-default-sink',old_sink)
        if cmd('pactl','get-default-source')==name+'.monitor': cmd('pactl','set-default-source',old_source)
        load('module-loopback','source='+source,'sink='+name,'source_dont_move=true','sink_dont_move=true','latency_msec=30')
        for _ in range(10):
            try: return gsr_device(name+'.monitor')
            except RuntimeError: time.sleep(.3)
        raise RuntimeError('Virtual mic not detected by GSR')
    except Exception:
        cleanup(); raise


def proc_identity(pid):
    try:
        fields=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return fields[19] if fields[0] not in ('Z','X') else None
    except (OSError,IndexError): return None

def watch(pid):
    identity=proc_identity(pid)
    if identity is None: raise RuntimeError('Recorder exited before microphone watchdog started')
    name=json.loads(STATE.read_text())['name']
    import sys
    subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'watch',str(pid),identity,name],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)

if __name__=='__main__':
    import sys,fcntl
    if len(sys.argv)==5 and sys.argv[1]=='watch':
        pid,identity,name=int(sys.argv[2]),sys.argv[3],sys.argv[4]
        while proc_identity(pid)==identity: time.sleep(1)
        lock=Path.home()/'.local/state/crimson-clips/engine.lock'
        with lock.open('a') as f:
            fcntl.flock(f,fcntl.LOCK_EX)
            if STATE.exists() and json.loads(STATE.read_text())['name']==name: cleanup()
