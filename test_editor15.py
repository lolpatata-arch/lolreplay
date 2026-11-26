import unittest
import subprocess
import tempfile
import shutil
from pathlib import Path
from lolreplay_export import export_args, filmstrip_args, probe

class Editor15Tests(unittest.TestCase):
    def test_options(self):
        args=export_args('a','b',1,5,2,track_volumes=[100,25],speed=2,aspect='vertical',quality='high')
        self.assertEqual(args[args.index('-t')+1],'2.000')
        self.assertIn('setpts=PTS/2',args[args.index('-vf')+1])
        self.assertIn('pad=1080:1920',args[args.index('-vf')+1])
        self.assertIn('atempo=2',args[args.index('-filter_complex')+1])
        self.assertEqual(args[args.index('-crf')+1],'16')
        for kw in ({'speed':0},{'aspect':'bad'},{'quality':'bad'}):
            with self.assertRaises(ValueError): export_args('a','b',0,1,1,**kw)
    def test_strip_args(self):
        args=filmstrip_args('clip.mp4',30)
        self.assertIn('tile=6x1',args[args.index('-vf')+1])
        with self.assertRaises(ValueError): filmstrip_args('a',0)
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_real_speed_and_filmstrip(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'source.mp4'; target=Path(d)/'copy.mp4'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=24','-f','lavfi','-i','sine=frequency=440','-t','3','-c:v','libx264','-c:a','aac',str(source)],check=True)
            strip=subprocess.run(['ffmpeg',*filmstrip_args(source,3)],capture_output=True,check=True).stdout
            self.assertTrue(strip.startswith(b'\x89PNG'))
            subprocess.run(['ffmpeg',*export_args(source,target,0,2,1,speed=2)],stdout=subprocess.DEVNULL,check=True)
            duration,tracks,video=probe(target)
            self.assertAlmostEqual(duration,1,delta=.2)
            self.assertEqual(tracks,1); self.assertTrue(video); self.assertTrue(source.exists())

if __name__=='__main__': unittest.main()
