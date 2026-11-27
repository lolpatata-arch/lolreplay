import unittest
import tempfile
from pathlib import Path
import importlib.util

@unittest.skipUnless(importlib.util.find_spec('PySide6'),'PySide6 required')
class BackgroundTests(unittest.TestCase):
    def test_preferences(self):
        import lolreplay_backgrounds as b
        self.assertEqual(len(b.STYLES),5)
        self.assertEqual(len(b.MODES),9)
        self.assertEqual(b.validated({'mode':'video','path':123}),{'mode':'logo','path':''})
        for mode in b.MODES:
            self.assertEqual(b.validated({'mode':mode,'path':'/tmp/wall.png'})['mode'],mode)
    def test_install_manifest(self):
        import install
        self.assertIn('lolreplay_backgrounds.py',install.PROGRAM_FILES)
