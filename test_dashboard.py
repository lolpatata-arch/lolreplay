"""Pure layout model regression tests; Qt is not required."""
import unittest
import itertools
import lolreplay_dashboard as d


class DashboardTests(unittest.TestCase):
    def test_default_and_mobile(self):
        self.assertEqual(d.positions(None),{'hero':(0,0,1,2),'capture':(0,2,1,1),'session':(1,0,1,3),'gallery':(2,0,1,3)})
        self.assertEqual(list(d.positions(None,True)),['capture','hero','session','gallery'])

    def test_validation(self):
        raw={'order':['storage','storage',None,{},'bad','hero'],'widgets':{'hero':{'width':True,'height':[],'visible':1},'storage':{'width':2,'height':'large','visible':True},'bad':{'visible':True}}}
        result=d.validated(raw)
        self.assertEqual(result['order'][:2],['storage','hero'])
        self.assertCountEqual(result['order'],d.IDS)
        self.assertEqual(result['widgets']['hero'],d.defaults()['widgets']['hero'])
        self.assertEqual(result['widgets']['storage'],{'width':2,'height':'large','visible':True})
        self.assertEqual(d.validated(result),result)

    def test_changes_and_order(self):
        original=d.defaults()
        changed=d.change(original,'favorites',visible=True,width=3,height='compact')
        self.assertFalse(original['widgets']['favorites']['visible'])
        self.assertEqual(changed['widgets']['favorites'],{'visible':True,'width':3,'height':'compact'})
        self.assertEqual(d.move(changed,'favorites','hero')['order'][0],'favorites')
        self.assertEqual(list(d.positions(d.step(original,'hero',-1,True),True))[:2],['hero','capture'])
        self.assertEqual(d.step(original,'hero',-1),original)
        self.assertEqual(d.move(original,'bad','hero'),original)
        self.assertEqual(d.validated(None),original)

    def test_no_overlap_or_out_of_bounds(self):
        for widths in itertools.product((1,2,3),repeat=len(d.IDS)):
            value=d.defaults()
            for key,width in zip(d.IDS,widths):
                value=d.change(value,key,visible=True,width=width)
            for stacked in (False,True):
                used=set(); positions=d.positions(value,stacked)
                self.assertCountEqual(positions,d.IDS)
                for row,col,_,width in positions.values():
                    self.assertLessEqual(col+width,1 if stacked else 3)
                    for c in range(col,col+width):
                        self.assertNotIn((row,c),used); used.add((row,c))
        for key in d.IDS: value=d.change(value,key,visible=False)
        self.assertEqual(d.positions(value),{})
