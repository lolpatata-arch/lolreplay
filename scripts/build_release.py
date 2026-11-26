#!/usr/bin/env python3
"""Build a flat, versioned ZIP compatible with lolreplay's updater since 1.2.0."""
import hashlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import install
import lolreplay_updater as updater

def build(version, destination):
    if not re.fullmatch(r'(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})\.(0|[1-9]\d{0,5})',version):
        raise ValueError('Expected X.Y.Z')
    if version != updater.VERSION or subprocess.check_output([sys.executable,str(ROOT/'lolreplay'),'--version'],text=True).strip()!=f'lolreplay {version}':
        raise ValueError('Version does not match the source')
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT,text=True).strip():
        raise ValueError('Tracked files must match committed source')
    files=list(dict.fromkeys([*install.PROGRAM_FILES,'install.py','lolreplay.png','README.md','CHANGELOG.md','LICENSE']))
    destination=Path(destination).resolve()
    destination.mkdir(parents=True,exist_ok=True)
    tag='v'+version; name=f'lolreplay-{tag}.zip'
    with tempfile.TemporaryDirectory(dir=destination) as temp:
        archive=Path(temp)/name
        subprocess.run(['git','archive','--format=zip',f'--prefix=lolreplay-{version}/',f'--output={archive}','HEAD','--',*files],cwd=ROOT,check=True)
        data=archive.read_bytes()
        digest='sha256:'+hashlib.sha256(data).hexdigest()
        asset={'name':name,'browser_download_url':f'https://github.com/{updater.REPO}/releases/download/{tag}/{name}','state':'uploaded','size':len(data),'digest':digest}
        listing=updater.releases([{'tag_name':tag,'draft':False,'prerelease':False,'assets':[asset]}],current='1.2.0')
        if len(listing)!=1: raise ValueError('Archive is not eligible for the 1.2.0 upgrade path')
        with tempfile.TemporaryDirectory() as extraction:
            source=updater.extract(data,listing[0],Path(extraction))
            if set(p.name for p in source.iterdir())!=set(files):
                raise ValueError('Package manifest mismatch')
            for path in files:
                if not (source/path).is_file(): raise ValueError('Missing '+path)
        archive.replace(destination/name)
    print(destination/name)
    print(digest)

if __name__=='__main__':
    if len(sys.argv)!=3: sys.exit('Usage: build_release.py X.Y.Z OUTPUT_DIR')
    build(sys.argv[1],sys.argv[2])
