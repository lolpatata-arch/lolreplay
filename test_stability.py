import fcntl
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import lolreplay_audio as audio
import lolreplay_storage as storage

ROOT=Path(__file__).resolve().parent
loader=importlib.machinery.SourceFileLoader('engine09',str(ROOT/'crimson-clips'))
spec=importlib.util.spec_from_loader(loader.name,loader)
engine=importlib.util.module_from_spec(spec); loader.exec_module(engine)

class StabilityTests(unittest.TestCase):
    def test_bad_config(self):
        for bad in ([],{'fps':None},{'bitrate_kbps':'abc'},{'microphone':'yes'},{'buffer_seconds':30,'save_seconds':60},{'library_id':[]},{'niri_capture':'bad'},{'rate_control':'bad'}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): storage.validate_config(bad)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'; p.write_text('{broken')
            with patch.object(storage,'CONFIG',p),self.assertRaises(OSError): storage.read_config()
            self.assertEqual(p.read_text(),'{broken')
    def test_encoder_retry(self):
        error='Driver does not support CBR RC mode (supported modes: CQP).'
        for mode, log_error, expected, succeeds in (
            ('auto', error, ['cbr','qp'], True),
            ('auto', 'Permission denied', ['cbr'], False),
            ('cbr', error, ['cbr'], False),
            ('cqp', '', ['qp'], True),
            ('auto', '', ['cbr'], True),
        ):
            with self.subTest(mode=mode,log_error=log_error), tempfile.TemporaryDirectory() as d:
                base=Path(d); log=base/'recorder.log'; log.write_text(error+'\n')
                calls=[]
                def launch(args,**kw):
                    rate=args[args.index('-bm')+1]; calls.append(rate)
                    failure=log_error if rate=='cbr' else ''
                    if failure: kw['stdout'].write(failure+'\n'); kw['stdout'].flush()
                    process=Mock(); process.poll.return_value=1 if failure else None; process.returncode=1 if failure else None
                    return process
                # Initial status is stopped; failed attempts stay stopped; successful attempt confirms active.
                def running(): return bool(calls and (calls[-1]=='qp' or not log_error))
                cfg={**engine.DEFAULT,'rate_control':mode}
                with patch.object(engine,'LOG',log),patch.object(engine,'SOCKET',base/'socket'),patch.object(engine,'is_running',side_effect=running),patch.object(engine,'output_check',return_value=base),patch.object(engine.shutil,'which',return_value='/fake'),patch.object(engine.compositor,'capture',return_value='screen'),patch.object(engine.audio,'cleanup'),patch.object(engine.audio,'output_device',return_value='default_output'),patch.object(engine.subprocess,'Popen',side_effect=launch),patch.object(engine.time,'sleep'):
                    if succeeds: self.assertEqual(engine.start(cfg),0)
                    else:
                        with self.assertRaisesRegex(RuntimeError,'grabador terminó'): engine.start(cfg)
                self.assertEqual(calls,expected)
    def test_ipc_unknown(self):
        with patch.object(engine.shutil,'which',return_value='/bin/gsr-cli'),patch.object(engine.subprocess,'run',side_effect=subprocess.TimeoutExpired('gsr-cli',4)):
            with self.assertRaisesRegex(RuntimeError,'timeout'): engine.is_running()
        with patch.object(engine.shutil,'which',return_value='/bin/gsr-cli'),patch.object(engine.subprocess,'run',return_value=subprocess.CompletedProcess([],2,'','IPC failed')):
            with self.assertRaisesRegex(RuntimeError,'IPC failed'): engine.is_running()
    def test_status_and_stop_with_invalid_config(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d); fake=h/'fake'; fake.mkdir(); x=fake/'gsr-cli'; x.write_text('#!/bin/sh\nexit "${FAKE_RUNNING:-1}"\n'); x.chmod(0o755)
            cfg=h/'.config/crimson-clips/config.json'; cfg.parent.mkdir(parents=True); cfg.write_text('{broken')
            env={**os.environ,'HOME':d,'XDG_RUNTIME_DIR':d,'PATH':str(fake)+':'+os.environ['PATH']}
            def call(*args,**extra): return subprocess.run([sys.executable,str(ROOT/'crimson-clips'),*args],env={**env,**extra},capture_output=True,text=True,timeout=9)
            self.assertEqual(call('status').returncode,1)
            self.assertEqual(call('status',FAKE_RUNNING='2').returncode,2)
            self.assertEqual(call('stop').returncode,0)
            self.assertNotEqual(call('duration','90').returncode,0)
            self.assertEqual(cfg.read_text(),'{broken')
            lock=h/'.local/state/crimson-clips/engine.lock'
            with lock.open('a') as f:
                fcntl.flock(f,fcntl.LOCK_EX)
                p=call('duration','30'); self.assertEqual(p.returncode,1); self.assertIn('operación',p.stderr)
    def test_corrupt_audio_state(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'audio.json'; p.write_text('{bad')
            with patch.object(audio,'STATE',p),patch.object(audio,'cmd') as cmd:
                with self.assertRaisesRegex(RuntimeError,'No audio modules unloaded'): audio.cleanup()
                cmd.assert_not_called()
            self.assertEqual(p.read_text(),'{bad')
    def test_publish_failures_and_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); lib=p/'disk'; lib.mkdir(); token=storage.register(lib); src=p/'saved.mp4'; src.write_bytes(b'replay'); dest=lib/'saved.mp4'
            with patch.object(storage.shutil,'copyfileobj',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): storage.publish(src,dest,token)
            self.assertTrue(src.exists()); self.assertFalse(dest.exists())
            dest.write_bytes(b'existing')
            with self.assertRaises(OSError): storage.publish(src,dest,token)
            self.assertEqual(dest.read_bytes(),b'existing'); self.assertEqual(src.read_bytes(),b'replay')
            with self.assertRaises(OSError): storage.publish(src,lib/'new.mp4','wrong')
            self.assertTrue(src.exists()); self.assertEqual(len(list(lib.glob('*.part'))),0)
            storage.publish(src,lib/'new.mp4',token); self.assertFalse(src.exists()); self.assertEqual((lib/'new.mp4').read_bytes(),b'replay')
    def test_source_changes_mid_transfer(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); lib=p/'disk'; lib.mkdir(); token=storage.register(lib); src=p/'saved.mp4'; src.write_bytes(b'old'); target=lib/'saved.mp4'; copy=storage.shutil.copyfileobj
            def mutate(a,b,*args): copy(a,b,*args); src.write_bytes(b'changed')
            with patch.object(storage.shutil,'copyfileobj',side_effect=mutate),self.assertRaisesRegex(OSError,'Source changed'): storage.publish(src,target,token)
            self.assertEqual(src.read_bytes(),b'changed'); self.assertFalse(target.exists())
if __name__=='__main__': unittest.main()
