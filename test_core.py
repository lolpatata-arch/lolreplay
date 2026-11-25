"""Core regression tests. No real sound devices, compositor or disks required."""
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import lolreplay_audio as audio
import lolreplay_storage as storage
from lolreplay_export import probe,export_args,temp_for

class Tests(unittest.TestCase):
    def test_audio_cleanup_missing_json_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)/'audio.json'; state.write_text(json.dumps({'name':'lolreplay_test','ids':[10,11,12]})); unloaded=[]
            def cmd(*args):
                if args==('pactl','list','short','modules'): return '10\tmodule-null-sink\tsink_name=lolreplay_test rate=48000\n11\tmodule-loopback\tsource=mic sink=lolreplay_test\n12\tmodule-loopback\tsource=other sink=unrelated\n'
                if args[:2]==('pactl','unload-module'): unloaded.append(args[2]); return ''
                raise AssertionError(args)
            with patch.object(audio,'STATE',state),patch.object(audio,'cmd',cmd): audio.cleanup()
            self.assertEqual(unloaded,['11','10']); self.assertFalse(state.exists())
    def test_output(self):
        with patch.object(audio,'cmd',side_effect=lambda *a: '[{"name":"headphones","description":"Headphones"},{"name":"lolreplay_fake"}]' if a[-1]=='sinks' else 'device:headphones.monitor|Headphones'):
            self.assertEqual(audio.output_device('auto'),'default_output'); self.assertEqual(audio.output_device('headphones'),'device:headphones.monitor')
            with self.assertRaises(RuntimeError): audio.output_device('missing')
    def test_replace_and_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); lib=d/'external'; lib.mkdir(); token=storage.register(lib); target=lib/'clip.mp4'; target.write_bytes(b'original'); expected=storage.signature(target); new=d/'new.part'; new.write_bytes(b'edited')
            with self.assertRaises(OSError): storage.replace_clip(new,target,expected,'wrong')
            self.assertEqual(target.read_bytes(),b'original'); self.assertTrue(new.exists())
            target.write_bytes(b'changed')
            with self.assertRaises(OSError): storage.replace_clip(new,target,expected,token)
            self.assertEqual(target.read_bytes(),b'changed'); self.assertTrue(new.exists())
            with patch.object(storage.shutil,'copyfileobj',side_effect=OSError('disk full')):
                with self.assertRaises(OSError): storage.replace_clip(new,target,storage.signature(target),token)
            self.assertEqual(target.read_bytes(),b'changed'); self.assertTrue(new.exists())
            storage.replace_clip(new,target,storage.signature(target),token)
            self.assertEqual(target.read_bytes(),b'edited'); self.assertFalse(new.exists()); self.assertEqual(sorted(p.name for p in lib.iterdir()),[storage.MARKER,'clip.mp4'])
    def test_real_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); orig=d/'clip.mp4'; token=storage.register(d)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=12','-f','lavfi','-i','sine=frequency=440','-t','4','-c:v','libx264','-c:a','aac',str(orig)],check=True)
            before=storage.signature(orig); duration,a,v=probe(orig); self.assertTrue(v); self.assertEqual(a,1)
            temp=temp_for(d/'temp.mp4'); subprocess.run(['ffmpeg',*export_args(orig,temp,1,3,a,75)],check=True,stdout=subprocess.DEVNULL)
            self.assertEqual(storage.signature(orig),before); self.assertAlmostEqual(probe(temp)[0],2,delta=.15)
            storage.replace_clip(temp,orig,before,token); self.assertAlmostEqual(probe(orig)[0],2,delta=.15)
            self.assertEqual(list(d.glob('*.mp4')),[orig])
if __name__=='__main__': unittest.main(verbosity=2)
