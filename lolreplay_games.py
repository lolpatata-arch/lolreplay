"""Local game detection: retain only names and sample times, not window titles."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from collections import Counter
from lolreplay_compositor import detect
from lolreplay_audio import proc_identity

INTERVAL=2
STATE=Path(os.environ.get('XDG_RUNTIME_DIR',f'/run/user/{os.getuid()}'))/'lolreplay-games.json'
KNOWN={'730':'Counter-Strike 2','440':'Team Fortress 2','570':'Dota 2','105600':'Terraria','322170':'Geometry Dash','367520':'Hollow Knight','250900':'The Binding of Isaac: Rebirth','620':'Portal 2','1687950':'Persona 5 Royal','1966720':'Lethal Company','2379780':'Balatro','774801':'Crab Champions'}
CLASSES={'cs2':'Counter-Strike 2','rythia':'Rythia','io.github.rythia.rythia':'Rythia','geometrydash':'Geometry Dash','geometrydash.exe':'Geometry Dash','hollow_knight':'Hollow Knight','hollow_knight.exe':'Hollow Knight','balatro':'Balatro','balatro.exe':'Balatro','isaac-ng':'The Binding of Isaac: Rebirth','isaac-ng.exe':'The Binding of Isaac: Rebirth','osu!':'osu!','osu!.exe':'osu!','org.vinegarhq.sober':'Roblox','sober':'Roblox'}
IGNORE={'steam','steamwebhelper','firefox','chromium','discord','vesktop','spotify','lolreplay','crimson-clips','org.prismlauncher.prismlauncher','prismlauncher'}
NON_GAMES={'0','769','228980','250820','1070560','1391110','1493710','1628350','1887720'}


def steam_names(home=None):
    home=Path.home() if home is None else Path(home)
    roots=[home/'.steam/steam',home/'.local/share/Steam',home/'.var/app/com.valvesoftware.Steam/data/Steam']
    for root in list(roots):
        try:
            text=(root/'steamapps/libraryfolders.vdf').read_text(errors='replace')
            for raw in re.findall(r'(?m)^\s*"path"\s*"((?:\\.|[^"\\])*)"',text):
                path=Path(raw.replace('\\\\','\\').replace('\\"','"'))
                if path.is_absolute() and path not in roots: roots.append(path)
        except OSError: pass
    names=dict(KNOWN)
    for root in roots:
        for manifest in (root/'steamapps').glob('appmanifest_*.acf'):
            app=re.fullmatch(r'appmanifest_(\d+)\.acf',manifest.name)
            if not app: continue
            try: text=manifest.read_text(errors='replace')
            except OSError: continue
            match=re.search(r'(?m)^\s*"name"\s*"((?:\\.|[^"\\])*)"',text)
            if match:
                name=' '.join(''.join(c for c in match[1].replace('\\"','"') if c.isprintable()).split())[:120]
                if name and not re.match(r'(?i)^(proton\b|steam linux runtime\b|steamworks\b|steamvr\b|steam client\b)',name):
                    names[app[1]]=name
    return names


def steam_id(pid):
    visited=set()
    for _ in range(6):
        if type(pid) is not int or pid<=1 or pid in visited: break
        visited.add(pid)
        try:
            for item in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0'):
                if item.startswith((b'SteamAppId=',b'SteamGameId=')):
                    value=item.split(b'=',1)[1].decode('ascii',errors='ignore')
                    if re.fullmatch(r'[1-9]\d{0,9}',value) and value not in NON_GAMES and int(value)<=4294967295: return value
        except OSError: pass
        try: pid=int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[1])
        except (OSError,ValueError,IndexError): break
    return ''


def identify(window,names):
    if not isinstance(window,dict): return ''
    classes=[str(window.get(k) or '').casefold() for k in ('class','initialClass','app_id')]
    if any(c in IGNORE for c in classes): return ''
    for c in classes:
        match=re.fullmatch(r'steam_app_(\d+)',c)
        if match and match[1] not in NON_GAMES: return names.get(match[1],'')
    for c in classes:
        if c in CLASSES: return CLASSES[c]
        if re.fullmatch(r'minecraft(?:[ ._-].*)?',c): return 'Minecraft'
    app=steam_id(window.get('pid'))
    return names.get(app,'') if app not in NON_GAMES else ''


def focused_window():
    args={'hyprland':['hyprctl','-j','activewindow'],'niri':['niri','msg','--json','focused-window']}.get(detect())
    if not args: return {}
    try:
        value=json.loads(subprocess.run(args,capture_output=True,text=True,timeout=1,check=True).stdout)
        return value if isinstance(value,dict) else {}
    except (OSError,ValueError,subprocess.SubprocessError): return {}


def choose_game(samples,seconds,now):
    recent=[(stamp,game) for stamp,game in samples if now-seconds-INTERVAL<=stamp<=now and game]
    if not recent: return ''
    counts=Counter(game for _,game in recent)
    return max(counts,key=lambda name:(counts[name],max(stamp for stamp,game in recent if game==name)))


def recent_game(seconds):
    now=time.time()
    try:
        data=json.loads(STATE.read_text())
        pid=data['pid']; identity=data['identity']; samples=data['samples']
        if type(pid) is not int or not identity or proc_identity(pid)!=identity: return ''
        if not samples or not 0<=now-samples[-1][0]<=INTERVAL*3: return ''
        return choose_game(samples,seconds,now)
    except (OSError,ValueError,TypeError,KeyError,IndexError): return ''


def watch(pid):
    identity=proc_identity(pid)
    if not identity: return
    subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'watch',str(pid),identity],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)


def monitor(pid,identity):
    names={}; refreshed=0.; samples=[]
    tmp=STATE.with_name(STATE.name+f'.{os.getpid()}.tmp')
    try:
        while proc_identity(pid)==identity:
            now=time.time()
            if now-refreshed>=60:
                names=steam_names(); refreshed=now
            game=identify(focused_window(),names)
            samples=[s for s in samples if s[0]>=now-1200-INTERVAL]
            samples.append((now,game))
            try:
                tmp.write_text(json.dumps({'pid':pid,'identity':identity,'samples':samples}))
                tmp.chmod(0o600); tmp.replace(STATE)
            except OSError: pass
            time.sleep(INTERVAL)
    finally: tmp.unlink(missing_ok=True)


if __name__=='__main__':
    if len(sys.argv)==4 and sys.argv[1]=='watch': monitor(int(sys.argv[2]),sys.argv[3])
