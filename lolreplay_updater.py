#!/usr/bin/env python3
"""Opt-in updates from the official public GitHub releases. No telemetry or background checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import urllib.request
from urllib.parse import urlsplit
import zipfile

VERSION = '1.2.0'
REPO = 'lolpatata-arch/lolreplay'
API = f'https://api.github.com/repos/{REPO}/releases'
MAX_ZIP = 32 * 1024 * 1024
MAX_API = 4 * 1024 * 1024
HOSTS = {'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}

class UpdateError(Exception): pass

def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'v?(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})',value):
        raise UpdateError('Invalid release version')
    return tuple(int(x) for x in value.lstrip('v').split('.'))

def trusted(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):
        raise UpdateError('Unexpected download host')
    return url

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return super().redirect_request(req,fp,code,msg,headers,trusted(newurl))

def fetch(url,limit):
    req=urllib.request.Request(trusted(url),headers={'User-Agent':'lolreplay-updater/'+VERSION,'Accept':'application/vnd.github+json' if url.startswith(API) else 'application/octet-stream'})
    with urllib.request.build_opener(Redirect()).open(req,timeout=15) as response:
        trusted(response.geturl()); data=response.read(limit+1)
    if len(data)>limit: raise UpdateError('Download exceeds size limit')
    return data

def releases(payload,experimental=False,current=VERSION):
    if not isinstance(payload,list): raise UpdateError('Invalid releases response')
    found={}
    for item in payload:
        if not isinstance(item,dict) or item.get('draft') is not False or type(item.get('prerelease')) is not bool: continue
        if item['prerelease'] and not experimental: continue
        tag=item.get('tag_name')
        try: number=version(tag)
        except UpdateError: continue
        if number<=version(current) or not tag.startswith('v'): continue
        name=f'lolreplay-{tag}.zip'; expected=f'https://github.com/{REPO}/releases/download/{tag}/{name}'
        assets=item.get('assets',[])
        if not isinstance(assets,list): continue
        for asset in assets:
            if not isinstance(asset,dict) or asset.get('name')!=name or asset.get('browser_download_url')!=expected or asset.get('state')!='uploaded': continue
            digest=asset.get('digest'); size=asset.get('size')
            if not isinstance(digest,str) or not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest) or type(size) is not int or not 0<size<=MAX_ZIP: continue
            notes=item.get('body'); notes=notes[:16000] if isinstance(notes,str) else ''
            found[tag]={'tag':tag,'prerelease':item['prerelease'],'notes':notes,'size':size,'digest':digest.lower(),'url':expected}
            break
    return sorted(found.values(),key=lambda r:version(r['tag']),reverse=True)

def available(experimental=False):
    return releases(json.loads(fetch(API+'?per_page=100',MAX_API)),experimental)

def extract(data,release,dest):
    if len(data)!=release['size'] or 'sha256:'+hashlib.sha256(data).hexdigest()!=release['digest']:
        raise UpdateError('Download integrity check failed')
    import io
    root='lolreplay-'+release['tag'][1:]; seen=set(); total=0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        entries=z.infolist()
        if len(entries)>200: raise UpdateError('Too many archive entries')
        for entry in entries:
            p=PurePosixPath(entry.filename); parts=p.parts
            if not parts or parts[0]!=root or p.is_absolute() or '..' in parts or '\\' in entry.filename or len(parts)>2 or (len(parts)==1 and not entry.is_dir()): raise UpdateError('Unexpected archive path')
            if entry.filename in seen or stat.S_IFMT(entry.external_attr>>16) not in (0,stat.S_IFREG,stat.S_IFDIR): raise UpdateError('Unsafe archive entry')
            seen.add(entry.filename); total+=entry.file_size
            if total>MAX_ZIP*2: raise UpdateError('Expanded archive too large')
            if entry.is_dir(): continue
            if not re.fullmatch(r'[A-Za-z0-9_.-]+',parts[-1]) or parts[-1] in ('.','..','.git'): raise UpdateError('Unexpected file name')
            out=dest.joinpath(*parts); out.parent.mkdir(parents=True,exist_ok=True)
            with out.open('xb') as f: f.write(z.read(entry))
    source=dest/root
    for name in ('install.py','lolreplay','lolreplay-ui','crimson-clips','lolreplay.png','lolreplay_updater.py'):
        if not (source/name).is_file(): raise UpdateError('Incomplete release package')
    # Verify the public wrapper declares the selected version, without executing it.
    if f"print('lolreplay {release['tag'][1:]}')" not in (source/'lolreplay').read_text(): raise UpdateError('Release version mismatch')
    return source

def stopped():
    binary=Path.home()/'.local/bin/crimson-clips'
    if not binary.is_file(): raise UpdateError('Install lolreplay normally first')
    result=subprocess.run([str(binary),'status'],capture_output=True,timeout=10)
    if result.returncode!=1: raise UpdateError('Stop replay first; save any wanted clips. Recorder status must be known.')

def install_release(tag,experimental=False,digest=None):
    stopped()
    selected=next((r for r in available(experimental) if r['tag']==tag),None)
    if not selected or (digest is not None and selected['digest']!=digest): raise UpdateError('Release changed or is unavailable. Check again.')
    with tempfile.TemporaryDirectory(prefix='lolreplay-update-') as temp:
        source=extract(fetch(selected['url'],MAX_ZIP),selected,Path(temp))
        check=subprocess.run([sys.executable,str(source/'install.py'),'--check'],cwd=source,capture_output=True,text=True,timeout=30)
        if check.returncode: raise UpdateError('Prerequisite check failed:\n'+check.stdout+check.stderr)
        stopped()
        # Target installer provides the engine lock and transactional file rollback.
        result=subprocess.run([sys.executable,str(source/'install.py'),'--update','--from-version',VERSION],cwd=source,capture_output=True,text=True)
        if result.returncode: raise UpdateError('Installation failed:\n'+result.stdout+result.stderr)
        print('Installed '+tag+'. Restart lolreplay.\n'+result.stdout)

def main(argv=None):
    p=argparse.ArgumentParser(description='Manually check and install official lolreplay releases.')
    p.add_argument('tag',nargs='?'); p.add_argument('--experimental',action='store_true'); p.add_argument('--json',action='store_true'); p.add_argument('--yes',action='store_true'); p.add_argument('--digest')
    a=p.parse_args(argv)
    try:
        if not a.tag:
            items=available(a.experimental)
            if a.json: print(json.dumps(items,ensure_ascii=False))
            else:
                print('Installed: v'+VERSION)
                if not items: print('No eligible newer releases.')
                for r in items: print(r['tag'], '(preview)' if r['prerelease'] else '(stable)', '\n'+r['notes'])
                print('Choose a version explicitly: lolreplay update vX.Y.Z')
            return 0
        version(a.tag)
        if not a.yes:
            selected=next((r for r in available(a.experimental) if r['tag']==a.tag),None)
            if not selected: raise UpdateError('Release unavailable. Check again.')
            print('Installed: v'+VERSION+' → '+a.tag+ (' (preview)' if selected['prerelease'] else ' (stable)')+'\n'+selected['notes'])
            if input('Install this version? [y/N] ').strip().lower()!='y': return 0
            a.digest=selected['digest']
        if not a.digest: raise UpdateError('Confirmed release digest required with --yes')
        install_release(a.tag,a.experimental,a.digest)
        return 0
    except (UpdateError,OSError,ValueError,EOFError,zipfile.BadZipFile,subprocess.SubprocessError) as e:
        print('Update error: '+str(e),file=sys.stderr); return 1

if __name__=='__main__': sys.exit(main())
