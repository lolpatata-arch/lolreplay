"""Static UI integration checks; no Qt runtime required."""
import ast
from pathlib import Path
import unittest
import lolreplay_compositor as compositor

ROOT=Path(__file__).resolve().parent

class UIContractTests(unittest.TestCase):
    def test_compositor_api(self):
        tree=ast.parse((ROOT/'lolreplay-ui').read_text())
        calls={n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='compositor'}
        self.assertIn('detect',calls)
        for name in calls:
            self.assertTrue(callable(getattr(compositor,name,None)),name)

    def test_release_version(self):
        self.assertIn("setApplicationVersion('1.5.0-dev')",(ROOT/'lolreplay-ui').read_text())
        self.assertIn("self.footer_meta.setText('v1.5.0-dev",(ROOT/'lolreplay-ui').read_text())
        # Keep the release updater baseline unchanged until 1.3 is published.
        self.assertIn("print('lolreplay 1.2.0')",(ROOT/'lolreplay').read_text())

if __name__=='__main__': unittest.main()
