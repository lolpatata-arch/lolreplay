import unittest
import lolreplay_visual as v
import lolreplay_preferences as p

class VisualTests(unittest.TestCase):
    def test_styles_and_geometry(self):
        self.assertTrue(v.profile(p.DEFAULTS).floating)
        self.assertFalse(v.profile({'visual_style':'classic'}).floating)
        self.assertEqual(v.profile({'corner_style':'sharp'}).radius,3)
        self.assertFalse(v.profile({'accent_glow':False}).sheen)
        for density in p.OPTIONS['visual_density']:
            self.assertEqual(v.spacing({'visual_density':density},True),(8,12,8))

    def test_persistence_and_defaults(self):
        initial={'theme':'AMOLED','replay_background':{'mode':'image','path':'/tmp/a.png'}}
        data=p.merge_ui(initial,{'visual_style':'glass','wallpaper_dim':30,'icon_navigation':True})
        self.assertEqual(data['theme'],'AMOLED')
        self.assertEqual(data['replay_background'],initial['replay_background'])
        self.assertEqual(data['preferences']['wallpaper_dim'],30)
        self.assertEqual(p.validated({'wallpaper_dim':900})['wallpaper_dim'],0)
