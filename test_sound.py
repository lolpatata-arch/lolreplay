"""Sound Control model and source contracts."""
import ast
from pathlib import Path
import unittest
from lolreplay_sound import device_preference,resolve_output,mixer_rows,volume_args,mute_args
ROOT=Path(__file__).resolve().parent

class SoundTests(unittest.TestCase):
    def test_default_and_fallback(self):
        self.assertEqual(resolve_output('auto',{'aa','bb'},'bb'),('bb',False))
        self.assertEqual(resolve_output('aa',{'aa','bb'},'bb'),('aa',False))
        self.assertEqual(resolve_output('aa',{'bb'},'bb'),('bb',True))
        self.assertEqual(resolve_output('aa',set(),''),('',True))
        self.assertEqual(resolve_output('aa',{'aa','bb'},'bb'),('aa',False))
        for invalid in (None,True,'bad','',{},'auto;cmd'):
            self.assertEqual(device_preference(invalid),'auto')

    def test_mixer_validation(self):
        def stream(index,name,volume=32768,mute=False):
            return {'index':index,'properties':{'application.name':name},'volume':{'left':{'value':volume}},'mute':mute}
        self.assertEqual(mixer_rows([stream(7,'Spotify'),stream(8,'Game',65536,True),stream(9,'lolreplay_bridge'),stream(-1,'bad'),stream(True,'bad'),None]),[(7,'Spotify',50,False),(8,'Game',100,True)])
        self.assertEqual(mixer_rows({}),[])
        self.assertEqual(volume_args(7,35),['set-sink-input-volume','7','35%'])
        self.assertEqual(mute_args(7,False),['set-sink-input-mute','7','0'])
        for idx,level in [(True,20),(-1,20),(1,101),(1,'20'),(1,-1)]:
            with self.assertRaises(ValueError): volume_args(idx,level)
        with self.assertRaises(ValueError): mute_args(1,1)

    def test_source_integration(self):
        for filename in ('lolreplay_sound.py','lolreplay_sound_ui.py','lolreplay-ui'):
            ast.parse((ROOT/filename).read_text())
        ui=(ROOT/'lolreplay-ui').read_text()
        self.assertIn("preferences.get('playback_output','auto')",ui)
        self.assertIn('TrackSelector(self.player)',ui)
        self.assertIn('PlaybackMeter(self.player)',ui)
        self.assertIn('DesktopMixer(self)',ui)
        self.assertIn("self.run('audio-mode',mode,*names)",ui)
        import install
        for filename in ('lolreplay_sound.py','lolreplay_sound_ui.py'):
            self.assertIn(filename,install.PROGRAM_FILES)

if __name__=='__main__': unittest.main()
