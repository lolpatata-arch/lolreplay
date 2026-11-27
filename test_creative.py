"""Creative Studio model tests without Qt."""
import unittest
import lolreplay_creative as c
import lolreplay_dashboard as d

class CreativeTests(unittest.TestCase):
    def test_validation_and_presets(self):
        value=c.validated({'dock':'bad','radius':True,'gap':100,'opacity':30,'palette':{'bg':'#ffffff','accent':'#Aa0022'},'widget_styles':{'hero':{'color':'#101010','radius':0},'bad':{'radius':4}}})
        self.assertEqual(value['dock'],'bottom')
        self.assertEqual(value['radius'],-1)
        self.assertEqual(value['gap'],-1)
        self.assertEqual(value['opacity'],100)
        self.assertEqual(value['palette'],{'accent':'#aa0022'})
        self.assertEqual(value['widget_styles'],{'hero':{'color':'#101010','radius':0}})
        self.assertEqual(c.validated(value),value)
        self.assertEqual(c.validated(None),c.DEFAULTS)
        self.assertEqual({c.validated(v)['dock'] for v in c.PRESETS.values()},{'top','bottom','left','right'})
    def test_history_and_reset(self):
        history=c.History(c.snapshot(None,None)); previous=history.current
        updated=c.snapshot({'dock':'right'},d.change(None,'storage',visible=True))
        history.push(updated); updated['design']['dock']='left'
        self.assertEqual(history.current['design']['dock'],'right')
        history.undo(); self.assertEqual(history.current,previous)
        history.redo(); self.assertEqual(history.current['design']['dock'],'right')
        history.undo(); history.push(c.snapshot({'dock':'top'},None)); self.assertFalse(history.future)
    def test_profile_and_unrelated_config(self):
        data={'theme':'Obsidian','preferences':{'playback_speed':175},'replay_hotkey':'F8'}
        saved={'My design':c.snapshot({'dock':'left'},d.change(None,'favorites',visible=True))}
        merged=c.merge_ui(data,{'dock':'right'},None,saved)
        for key in data: self.assertEqual(merged[key],data[key])
        self.assertEqual(merged['creative_profiles'],saved)
        self.assertFalse(data.get('creative_design'))
        self.assertEqual(c.profiles(merged['creative_profiles']),saved)
    def test_hub_guard_and_blending(self):
        design=c.validated({'hub_visible':False})
        self.assertFalse(c.effective_hub(design,d.defaults(),0))
        self.assertTrue(c.effective_hub(design,d.change(None,'capture',visible=False),0))
        self.assertTrue(c.effective_hub(design,d.defaults(),3))
        self.assertEqual(c.mix('#ffffff','#000000',50),'#808080')
