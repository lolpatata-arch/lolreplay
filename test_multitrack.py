import unittest
import lolreplay_audio as audio
import lolreplay_storage as storage
from lolreplay_export import export_args

class MultitrackTests(unittest.TestCase):
    def test_capture_args(self):
        self.assertEqual(audio.track_args('mixed','out','mic'),['-a','out|mic'])
        self.assertEqual(audio.track_args('separate','out','mic'),['-a','out','-a','mic'])
        self.assertEqual(audio.track_args('separate','out'),['-a','out'])
        self.assertEqual(audio.track_args('apps',None,'mic',['cs2','Discord']),['-a','app:cs2','-a','app:Discord','-a','mic'])
    def test_invalid_apps(self):
        for names in ([],['Discord','discord'],['x|app:y'],[''],['x;y']):
            with self.assertRaises(ValueError): audio.track_args('apps',None,None,names)
        with self.assertRaises(ValueError): storage.validate_config({'audio_mode':'apps'})
    def test_independent_gains(self):
        args=export_args('source.mp4','output.mp4',0,5,3,100,track_volumes=[100,0,25])
        graph=args[args.index('-filter_complex')+1]
        for i,gain in enumerate(('1.000','0.000','0.250')):
            self.assertIn(f'[0:a:{i}]aresample=48000,aformat=channel_layouts=stereo,volume={gain}',graph)
        with self.assertRaises(ValueError): export_args('a','b',0,5,2,track_volumes=[100])

if __name__=='__main__': unittest.main()
