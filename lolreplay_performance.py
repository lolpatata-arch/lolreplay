"""Capture quality settings and lightweight thumbnail process arguments."""
import shutil

PROFILES = {'light': (30, 6000), 'balanced': (60, 12000), 'high': (60, 20000)}

def set_profile(cfg, name):
    fps, bitrate = PROFILES[name]
    return {**cfg, 'fps': fps, 'bitrate_kbps': bitrate}

def set_buffer(cfg, seconds):
    if not 30 <= seconds <= 1200:
        raise ValueError('Buffer must be between 30 and 1200 seconds')
    return {**cfg, 'buffer_seconds': seconds,
            'save_seconds': min(seconds, max(2, int(cfg.get('save_seconds', 30))))}

def video_payload_mb(bitrate, seconds):
    return int(bitrate) * int(seconds) / 8000

def thumbnail_command(path):
    args = ['ffmpeg', '-nostdin', '-loglevel', 'error', '-threads', '1',
            '-filter_threads', '1', '-ss', '0.5', '-i', str(path), '-frames:v', '1',
            '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2',
            '-threads', '1', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1']
    if shutil.which('nice'):
        return ['nice', '-n', '10', *args]
    return args


def rate_attempts(mode):
    return {'auto': ('cbr', 'cqp'), 'cbr': ('cbr',), 'cqp': ('cqp',)}[mode]


def rate_args(cfg, rate):
    if rate == 'cbr': return ['-bm', 'cbr', '-q', str(cfg['bitrate_kbps'])]
    if rate == 'cqp':
        quality = 'medium' if cfg['bitrate_kbps'] <= 6000 else 'high' if cfg['bitrate_kbps'] <= 12000 else 'very_high'
        return ['-bm', 'qp', '-q', quality]
    raise ValueError('Unknown rate control')


def cbr_rejected(log):
    return any('driver does not support cbr rc mode' in line.lower() and 'cqp' in line.lower() for line in log.splitlines())
