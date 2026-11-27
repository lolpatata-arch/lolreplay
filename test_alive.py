"""ALIVE configuration and animation curve tests."""
import unittest
import lolreplay_alive as a

class AliveTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(a.validated(None),a.DEFAULTS)
        value=a.validated({'enabled':False,'fps':True,'duration':900,'intensity':-1,'hover':'invalid','wallpaper_speed':125,'ambient':'orbit'})
        self.assertFalse(value['enabled']); self.assertEqual(value['fps'],30); self.assertEqual(value['duration'],220)
        self.assertEqual(value['intensity'],35); self.assertEqual(value['hover'],'glow')
        self.assertEqual(value['wallpaper_speed'],125); self.assertEqual(value['ambient'],'orbit')
        self.assertEqual(a.validated(value),value)
    def test_guard_and_curves(self):
        self.assertTrue(a.allowed(a.DEFAULTS,True,False))
        self.assertFalse(a.allowed(a.DEFAULTS,False,False))
        self.assertFalse(a.allowed(a.validated({'enabled':False}),True,False))
        self.assertFalse(a.allowed(a.validated({'pause_recording':True}),True,True))
        for curve in a.CHOICES['easing']:
            seq=[a.easing(x/10,curve) for x in range(11)]
            self.assertEqual(seq[0],0); self.assertEqual(seq[-1],1); self.assertEqual(seq,sorted(seq))
    def test_wallpaper_validation(self):
        self.assertEqual(a.wallpaper({'mode':'url','path':'https://example.com'}),{'mode':'none','path':''})
        self.assertEqual(a.wallpaper({'mode':'video','path':None}),{'mode':'none','path':''})
        self.assertEqual(a.wallpaper({'mode':'image','path':'/tmp/a.gif'}),{'mode':'image','path':'/tmp/a.gif'})
