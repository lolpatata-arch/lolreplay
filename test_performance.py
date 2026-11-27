import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import lolreplay_performance as perf

class PerformanceTests(unittest.TestCase):
    def test_profiles(self):
        original={'fps':60,'bitrate_kbps':12000,'buffer_seconds':1200,'save_seconds':90,'microphone':True}
        light=perf.set_profile(original,'light')
        self.assertEqual((light['fps'],light['bitrate_kbps']),(30,6000))
        self.assertEqual(original['fps'],60)
        self.assertTrue(light['microphone'])
        self.assertEqual(light['save_seconds'],90)
        self.assertEqual(perf.set_profile(light,'balanced'),original)
    def test_buffer(self):
        cfg={'save_seconds':1200,'buffer_seconds':1200,'microphone':True}
        self.assertEqual(perf.set_buffer(cfg,120)['save_seconds'],120)
        self.assertEqual(perf.set_buffer({'save_seconds':30},300)['save_seconds'],30)
        for n in (0,29,1201):
            with self.assertRaises(ValueError): perf.set_buffer(cfg,n)
        self.assertEqual(perf.video_payload_mb(12000,1200),1800)
    def test_rate_control(self):
        cfg={'bitrate_kbps':12000}
        self.assertEqual(perf.rate_attempts('auto'),('cbr','cqp'))
        self.assertEqual(perf.rate_attempts('cbr'),('cbr',))
        self.assertEqual(perf.rate_attempts('cqp'),('cqp',))
        self.assertEqual(perf.rate_args(cfg,'cbr'),['-bm','cbr','-q','12000'])
        self.assertEqual(perf.rate_args(cfg,'cqp'),['-bm','qp','-q','high'])
        self.assertTrue(perf.cbr_rejected('Driver does not support CBR RC mode (supported modes: CQP).'))
        self.assertFalse(perf.cbr_rejected('Permission denied'))
        self.assertFalse(perf.cbr_rejected('Driver does not support CBR RC mode (supported modes: VBR).'))
    def test_thumbnail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test clip.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=12','-t','2','-c:v','libx264',str(p)],check=True)
            result=subprocess.run(perf.thumbnail_command(p),capture_output=True,check=True)
            self.assertTrue(result.stdout.startswith(b'\x89PNG\r\n\x1a\n'))
    def test_cli_guard_and_install(self):
        root=Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as d:
            home=Path(d); fake=home/'fake'; fake.mkdir(); gsr=fake/'gsr-cli'; gsr.write_text('#!/bin/sh\nexit "${FAKE_RUNNING:-1}"\n'); gsr.chmod(0o755)
            for name in ('gpu-screen-recorder','pactl'):
                x=fake/name; x.write_text('#!/bin/sh\nexit 0\n'); x.chmod(0o755)
            env={**os.environ,'HOME':str(home),'XDG_DATA_HOME':str(home/'.local/share'),'XDG_CONFIG_HOME':str(home/'.config'),'PATH':str(fake)+':'+os.environ['PATH']}
            def call(*args,active=False):
                return subprocess.run([sys.executable,str(root/'crimson-clips'),*args],env={**env,'FAKE_RUNNING':'0' if active else '1'},capture_output=True,text=True)
            self.assertEqual(call('profile','light').returncode,0)
            cfg=home/'.config/crimson-clips/config.json'; before=cfg.read_bytes()
            self.assertNotEqual(call('profile','balanced',active=True).returncode,0)
            self.assertNotEqual(call('buffer','300',active=True).returncode,0)
            self.assertEqual(cfg.read_bytes(),before)
            self.assertEqual(call('duration','90').returncode,0)
            self.assertEqual(call('buffer','60').returncode,0)
            self.assertEqual(json.loads(cfg.read_text())['save_seconds'],60)
            before=cfg.read_bytes()
            legacy=home/'.local/share/icons/hicolor/scalable/apps/lolreplay.svg'; legacy.parent.mkdir(parents=True); legacy.write_text("old icon")
            for _ in range(2):
                p=subprocess.run([sys.executable,str(root/'install.py')],env=env,capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(cfg.read_bytes(),before)
            self.assertTrue((home/'Videos/CrimsonClips').is_dir())
            self.assertTrue((home/'.local/bin/lolreplay_performance.py').is_file())
            self.assertTrue((home/'.local/bin/lolreplay_icons.py').is_file())
            self.assertTrue((home/'.local/bin/lolreplay_widgets.py').is_file())
            icon_path=home/'.local/share/icons/hicolor/512x512/apps/lolreplay.png'
            self.assertEqual(icon_path.read_bytes(),(root/'lolreplay.png').read_bytes())
            raw=icon_path.read_bytes(); digest=hashlib.sha256(raw).hexdigest()[:12]
            fresh=icon_path.with_name(f'lolreplay-{digest}.png')
            self.assertEqual(fresh.read_bytes(),raw)
            self.assertEqual(icon_path.with_name('crimson-clips.png').read_bytes(),raw)
            self.assertIn('Icon='+str(fresh),(home/'.local/share/applications/crimson-clips.desktop').read_text())
            self.assertFalse(legacy.exists())
            self.assertEqual(len(list(legacy.parent.glob('lolreplay.svg.bak-*'))),1)
            p=subprocess.run([sys.executable,str(home/'.local/bin/lolreplay'),'--version'],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertEqual(p.stdout.strip(),'lolreplay 2.3.0')

if __name__=='__main__': unittest.main()
