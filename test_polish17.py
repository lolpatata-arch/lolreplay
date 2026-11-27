import ast
import unittest
from pathlib import Path
import lolreplay_preferences as p
import lolreplay_updater as u
ROOT=Path(__file__).resolve().parent

class PolishTests(unittest.TestCase):
    def test_versions(self):
        self.assertEqual(u.VERSION,'2.2.0')
        self.assertIn("print('lolreplay 2.2.0')",(ROOT/'lolreplay').read_text())
        self.assertIn("setApplicationVersion('2.2.0')",(ROOT/'lolreplay-ui').read_text())
    def test_tray_opt_in(self):
        self.assertFalse(p.validated({})['close_to_tray'])
        self.assertTrue(p.validated({'close_to_tray':True})['close_to_tray'])
    def test_compile(self):
        for name in ('lolreplay-ui','lolreplay','crimson-clips','lolreplay_editor.py','lolreplay_games.py','lolreplay_updater.py'):
            compile((ROOT/name).read_text(),name,'exec')
    def test_background_health(self):
        tree=ast.parse((ROOT/'lolreplay-ui').read_text())
        fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='background_health')
        self.assertTrue(any(isinstance(n,ast.Attribute) and n.attr=='check_status' for n in ast.walk(fn)))
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr=='refresh_library' for n in ast.walk(fn)))
