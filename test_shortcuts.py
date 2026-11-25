import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import subprocess
import lolreplay_shortcuts as k
from lolreplay_i18n import CATALOG

class ShortcutsTests(unittest.TestCase):
    def test_defaults_and_persistence(self):
        self.assertEqual(k.load({}),(k.DEFAULTS,'F8'))
        m={**k.DEFAULTS,'play':'K','rename':''}
        self.assertEqual(k.load({'shortcuts':m,'replay_hotkey':'Ctrl+F9'}),(m,'Ctrl+F9'))
        self.assertEqual(k.load({'shortcuts':{'play':42}}),(k.DEFAULTS,'F8'))
        self.assertTrue(set(k.LABELS.values())<=set(CATALOG))
    def test_conflicts_and_validation(self):
        for m in ({'play':'F8'},{'rename':'Space'},{'play':'Esc'},{'play':'Ctrl+Ctrl+A'}):
            with self.assertRaises(ValueError): k.validate(m)
        for key in ('A','Space','Ctrl+K, Ctrl+L','Ctrl+X;evil'):
            with self.assertRaises(ValueError): k.normalize(key,True)
        self.assertEqual(k.normalize('Shift+Ctrl+F9',True),'Ctrl+Shift+F9')
    def test_hypr_owned_block(self):
        exe=Path('/tmp/lolreplay'); old=k.snippet('F8','hyprland',exe)
        text='-- other\n'+k.BEGIN+'\n'+old+'\n'+k.END+'\n-- end\n'
        out=k.hypr_candidate(text,'F8','Ctrl+F9',exe)
        self.assertIn('CTRL + F9',out); self.assertNotIn(old,out); self.assertIn('-- other',out)
        with self.assertRaises(ValueError): k.hypr_candidate(text.replace(old,'hl.bind("F8", other)'), 'F8','F9',exe)
    def test_hypr_live_conflict_and_backup(self):
        exe=Path('/tmp/lolreplay')
        with TemporaryDirectory() as d:
            p=Path(d)/'hyprland.lua'; text=k.BEGIN+'\n'+k.snippet('F8','hyprland',exe)+'\n'+k.END; p.write_text(text)
            with patch.object(k.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[{"modmask":4,"key":"F9"}]','')):
                with self.assertRaises(ValueError): k.apply_global('F8','Ctrl+F9',exe,'hyprland',p)
            self.assertEqual(p.read_text(),text)
            with patch.object(k.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[]','')):
                backup=k.apply_global('F8','Ctrl+F9',exe,'hyprland',p)
            self.assertEqual(Path(backup).read_text(),text); self.assertIn('CTRL + F9',p.read_text())
    def test_niri_validate_before_write(self):
        exe=Path('/tmp/lolreplay')
        with TemporaryDirectory() as d:
            p=Path(d)/'config.kdl'; text='binds {\n    '+k.snippet('F8','niri',exe)+'\n}\n'; p.write_text(text)
            with patch.object(k.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],1,'','invalid')]):
                with self.assertRaises(ValueError): k.apply_global('F8','Ctrl+F9',exe,'niri',p)
            self.assertEqual(p.read_text(),text)
            with patch.object(k.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')):
                k.apply_global('F8','Ctrl+F9',exe,'niri',p)
            self.assertIn('Ctrl+F9',p.read_text()); self.assertNotIn('F8 repeat',p.read_text())
