"""Discover filesystems without modifying the block devices."""
import json
import os
from pathlib import Path
import subprocess

SYSTEM_MOUNTS = ('/', '/home', '/boot', '/efi', '/usr', '/var', '/etc', '/opt', '/srv', '/tmp', '/nix', '/root')
DATA_FS = {'ext2','ext3','ext4','btrfs','xfs','f2fs','ntfs','ntfs3','exfat','vfat','fat','msdos','udf','hfsplus','zfs_member','bcachefs'}

def parse(data):
    result=[]
    def walk(nodes, external=False):
        for node in nodes:
            removable=external or str(node.get('rm')).lower() in ('1','true') or str(node.get('hotplug')).lower() in ('1','true') or node.get('tran') in ('usb','ieee1394','mmc')
            name=node.get('path') or node.get('name') or ''
            fs=(node.get('fstype') or '').lower()
            mounts=node.get('mountpoints') or []
            if isinstance(mounts,str): mounts=[mounts]
            mounts=[m for m in mounts if isinstance(m,str) and m.startswith('/')]
            system=any(m in SYSTEM_MOUNTS or m.startswith(('/boot/','/efi/','/usr/','/var/','/etc/','/nix/','/run/credentials/')) for m in mounts)
            if name.startswith('/dev/') and node.get('type') not in ('loop','rom') and fs in DATA_FS and not system and (removable or mounts or node.get('type') in ('part','disk','crypt','lvm')):
                result.append(dict(device=name, uuid=node.get('uuid') or '', label=node.get('label') or Path(name).name, size=node.get('size') or '?', fs=fs, mounts=mounts, external=removable))
            walk(node.get('children') or [],removable)
    walk(data.get('blockdevices') or [])
    unique={d['device']:d for d in result}
    return sorted(unique.values(),key=lambda d:(not d['external'],not bool(d['mounts']),d['label'].casefold(),d['device']))

def discover():
    cp=subprocess.run(['lsblk','--json','--paths','--output','NAME,TYPE,FSTYPE,LABEL,UUID,SIZE,RM,HOTPLUG,TRAN,MOUNTPOINTS'],capture_output=True,text=True,timeout=5,check=True)
    return parse(json.loads(cp.stdout))

def describe(d):
    state=', '.join(d['mounts']) if d['mounts'] else 'Not mounted'
    return f"{d['label']} · {d['size']} · {d['fs']} · {d['device']} · {state}"

def current(d):
    for x in discover():
        if x['device']==d['device'] and x['uuid']==d['uuid']: return x
    raise OSError('Drive disconnected or changed. Refresh and select it again.')

def folder_on_drive(d,path):
    folder=Path(path).resolve(strict=True)
    for mount in current(d)['mounts']:
        try: root=Path(mount).resolve(strict=True)
        except OSError: continue
        if (folder==root or root in folder.parents) and folder.stat().st_dev==root.stat().st_dev:
            if not folder.is_dir() or not os.access(folder,os.W_OK|os.X_OK): raise OSError('Folder is not writable. Choose a writable directory on the drive.')
            return folder
    raise OSError('The chosen folder is not on the selected mounted drive.')
