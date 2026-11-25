import unittest
import ast
from pathlib import Path
import lolreplay_preferences as p
from lolreplay_i18n import CATALOG

class PreferencesTests(unittest.TestCase):
    def test_defaults_and_invalid(self):
        self.assertEqual(p.validated(None),p.DEFAULTS)
        self.assertEqual(p.validated({'text_scale':True,'refresh_ms':-1,'tile_size':[],'high_contrast':1}),p.DEFAULTS)
    def test_every_option_roundtrips(self):
        for key,options in p.OPTIONS.items():
            for value in options:
                self.assertEqual(p.validated({key:value})[key],value)
    def test_preserve_unrelated_values(self):
        initial={'language':'ja_JP','theme':'AMOLED','custom':{'accent':'#abcdef'},'playback_volume':33,'library_sort':'name'}
        updated=p.merge_ui(initial,{'text_scale':120,'loop_playback':True})
        reset=p.merge_ui(updated,p.DEFAULTS)
        self.assertEqual({k:v for k,v in reset.items() if k!='preferences'},initial)
        self.assertEqual(reset['preferences'],p.DEFAULTS)
        self.assertNotIn('preferences',initial)
    def test_controls_and_catalog(self):
        tree=ast.parse(Path(__file__).with_name('lolreplay-ui').read_text())
        fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='build_preferences')
        keys=set()
        for n in ast.walk(fn):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('choice','toggle','group'):
                if n.func.id=='group': self.assertIn(n.args[0].value,CATALOG); continue
                keys.add(n.args[0].value); self.assertIn(n.args[1].value,CATALOG)
                if n.func.id=='choice':
                    values={ast.literal_eval(item.elts[0]) for item in n.args[2].elts}
                    self.assertEqual(values,set(p.OPTIONS[n.args[0].value]))
                    for item in n.args[2].elts: self.assertIn(ast.literal_eval(item.elts[1]),CATALOG)
        self.assertEqual(keys,set(p.OPTIONS))

if __name__=='__main__': unittest.main()
