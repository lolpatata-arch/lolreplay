"""Non-destructive MP4 export helpers, independent of Qt."""
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path


def probe_details(path):
    result = subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)], capture_output=True, text=True, timeout=8, check=True)
    data=json.loads(result.stdout)
    streams=data.get('streams',[])
    duration=float(data.get('format',{}).get('duration',0))
    if not math.isfinite(duration): raise ValueError('Invalid media duration')
    titles=[str(s.get('tags',{}).get('title') or '') for s in streams if s.get('codec_type')=='audio']
    return duration,titles,any(s.get('codec_type')=='video' for s in streams)


def probe(path):
    duration,titles,video=probe_details(path)
    return duration,len(titles),video


SPEEDS=(0.5,0.75,1.0,1.25,1.5,2.0)
ASPECTS={'original':None,'vertical':(1080,1920),'square':(1080,1080)}
QUALITY={'small':25,'balanced':20,'high':16}


def filmstrip_args(source,duration):
    if not math.isfinite(duration) or duration<=0: raise ValueError('Invalid media duration')
    # Six representative, aspect-preserving frames. Never decode at full resolution into RAM.
    rate=6/duration
    vf=f'fps={rate:.12f},scale=160:90:force_original_aspect_ratio=decrease,pad=160:90:(ow-iw)/2:(oh-ih)/2,tile=6x1'
    return ['-nostdin','-v','error','-threads','1','-filter_threads','1','-i',str(source),'-an','-sn','-dn','-vf',vf,'-frames:v','1','-threads','1','-f','image2pipe','-vcodec','png','pipe:1']


def export_args(source, temp, start, end, tracks, volume=100, music=None, music_volume=25, track_volumes=None, *, speed=1.0, aspect='original', quality='balanced'):

    if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end): raise ValueError('Invalid trim range')
    if not 0 <= volume <= 100 or not 0 <= music_volume <= 100: raise ValueError('Invalid volume')
    if track_volumes is not None and (len(track_volumes)!=tracks or any(type(v) is not int or not 0<=v<=100 for v in track_volumes)): raise ValueError('Invalid track volumes')
    if speed not in SPEEDS or aspect not in ASPECTS or quality not in QUALITY: raise ValueError('Invalid export settings')
    length=(end-start)/speed
    args=['-hide_banner','-nostdin','-loglevel','error','-progress','pipe:1','-nostats','-y','-ss',f'{start:.3f}','-i',str(source)]
    if music: args += ['-stream_loop','-1','-i',str(music)]
    filters=[]; inputs=[]
    for i in range(tracks):
        gain=volume/100*(track_volumes[i]/100 if track_volumes is not None else 1)
        tempo=f',atempo={speed:g}' if speed!=1 else ''
        filters.append(f'[0:a:{i}]aresample=48000,aformat=channel_layouts=stereo,volume={gain:.3f}{tempo}[a{i}]'); inputs.append(f'[a{i}]')
    if music:
        filters.append(f'[1:a:0]aresample=48000,aformat=channel_layouts=stereo,volume={music_volume/100:.3f}[music]'); inputs.append('[music]')
    if len(inputs)>1:
        filters.append(''.join(inputs)+f'amix=inputs={len(inputs)}:duration=longest:normalize=0,alimiter=limit=0.95:level=false[aout]'); audio='[aout]'
    else: audio=inputs[0] if inputs else None
    if filters: args += ['-filter_complex',';'.join(filters)]
    args += ['-map','0:v:0']
    if audio: args += ['-map',audio,'-c:a','aac','-b:a','192k']
    else: args += ['-an']
    vf=[]
    if speed!=1: vf.append(f'setpts=PTS/{speed:g}')
    if ASPECTS[aspect]:
        w,h=ASPECTS[aspect]
        vf.extend([f'scale={w}:{h}:force_original_aspect_ratio=decrease:force_divisible_by=2',f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2','setsar=1'])
    else: vf.append('pad=ceil(iw/2)*2:ceil(ih/2)*2')
    args += ['-t',f'{length:.3f}','-vf',','.join(vf),'-c:v','libx264','-preset','veryfast','-crf',str(QUALITY[quality]),'-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-f','mp4',str(temp)]
    return args


def temp_for(destination):
    fd,name=tempfile.mkstemp(prefix='.lolreplay-export-',suffix='.part',dir=Path(destination).parent)
    os.close(fd)
    return Path(name)


def publish(temp,destination):
    # The output is exposed only once complete; link refuses to replace an existing file.
    # Local Linux filesystem required for this initial editor version.
    if not temp.is_file() or temp.stat().st_size==0: raise ValueError('Empty export')
    os.link(temp,destination)
    temp.unlink()


def next_export_path(directory, source):
    """Select a fresh name in the configured library. publish still rejects races."""
    directory=Path(directory).resolve(strict=True)
    if not directory.is_dir(): raise ValueError('Clip library is unavailable')
    stem=Path(source).stem+'-edit'
    for i in range(1,10001):
        target=directory/(stem+('' if i==1 else f'-{i}')+'.mp4')
        if not os.path.lexists(target): return target
    raise ValueError('Too many edited copies; rename a clip in Library')
