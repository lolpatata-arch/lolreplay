"""Pure layout model regression tests; Qt is not required."""
import unittest
import itertools
import random
from datetime import datetime, date, timedelta
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
        # Exhaust all six original width combinations, plus deterministic full-catalog samples.
        rng=random.Random(23)
        combinations=[base+(1,)*(len(d.IDS)-6) for base in itertools.product((1,2,3),repeat=6)]
        combinations.extend([(width,)*len(d.IDS) for width in (1,2,3)])
        combinations.extend(tuple(rng.choice((1,2,3)) for _ in d.IDS) for _ in range(512))
        for widths in combinations:
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

    def test_catalog_and_legacy_layout(self):
        self.assertEqual(len(d.IDS),20)
        self.assertCountEqual([key for group in d.GROUPS.values() for key in group],d.IDS)
        self.assertEqual(set(d.NAMES),set(d.IDS))
        legacy={'order':['storage','hero','capture','session','gallery','favorites'],'widgets':{'storage':{'visible':True}}}
        restored=d.validated(legacy)
        self.assertEqual(restored['order'][:6],legacy['order'])
        self.assertTrue(restored['widgets']['storage']['visible'])
        self.assertFalse(any(restored['widgets'][key]['visible'] for key in d.IDS[6:]))
        for key in d.IDS: restored=d.change(restored,key,visible=True)
        self.assertCountEqual(d.positions(restored,True),d.IDS)

    def test_library_summary(self):
        today=date(2026,11,27)
        def entry(name,days,size):
            dt=datetime.combine(today-timedelta(days=days),datetime.min.time())
            return (name,int(dt.timestamp()*1e9),size)
        files=[entry('a',0,10),entry('b',1,20),entry('c',6,30),entry('d',8,40)]
        metadata={'a':(False,'CS2',[]),'b':(False,'CS2',[]),'c':(False,'Portal 2',[]),'d':(False,'',[])}
        summary=d.library_summary(files,metadata.get,{files[0]:15,files[2]:30},today)
        self.assertEqual(summary['counts'],(1,0,0,0,0,1,1))
        self.assertEqual((summary['games'],summary['top_game'],summary['top_count']),(2,'CS2',2))
        self.assertEqual((summary['longest'],summary['longest_duration']),(files[2],30))
        empty=d.library_summary([],metadata.get,{},today)
        self.assertEqual(empty['counts'],(0,)*7)
        self.assertIsNone(empty['longest'])
