import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import lolreplay_compositor as c

class CompositorTests(unittest.TestCase):
    def test_sessions(self):
        self.assertEqual(c.detect({'NIRI_SOCKET':'socket'}),'niri')
        self.assertEqual(c.detect({'HYPRLAND_INSTANCE_SIGNATURE':'a'}),'hyprland')
        self.assertEqual(c.detect({'XDG_CURRENT_DESKTOP':'niri'}),'niri')
        self.assertEqual(c.detect({'XDG_CURRENT_DESKTOP':'GNOME'}),'unknown')
    def test_capture(self):
        cfg={'capture':'DP-1','niri_capture':'portal'}
        self.assertEqual(c.capture(cfg,{'NIRI_SOCKET':'socket'}),'portal')
        self.assertEqual(c.capture(cfg,{'HYPRLAND_INSTANCE_SIGNATURE':'a'}),'DP-1')
        self.assertEqual(c.capture({'niri_capture':'screen'},{'NIRI_SOCKET':'socket'}),'screen')
    def test_bind_candidate(self):
        text='input {\n}\nbinds {\n    Mod+Q { close-window; }\n}\n'
        exe='/home/test user/.local/bin/lolreplay'
        new=c.candidate(text,exe)
        self.assertIn(c.binding_line(exe),new)
        self.assertIn('Mod+Q { close-window; }',new)
        self.assertEqual(c.candidate(new,exe),new)
        for bad in ('binds {\n F8 { spawn "other"; }\n}\n','include "other.kdl"\nbinds {\n}\n','// binds {\n// }\n'):
            with self.assertRaises(ValueError): c.candidate(bad,exe)
    def test_transaction(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.kdl'; text='binds {\n}\n'; p.write_text(text)
            with patch.object(c,'detect',return_value='niri'),patch.object(c.shutil,'which',return_value='/bin/niri'),patch.object(c.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,'',''),subprocess.CompletedProcess([],1,'','invalid')]):
                with self.assertRaises(ValueError): c.install_niri_bind('/tmp/lolreplay',p)
            self.assertEqual(p.read_text(),text)
            with patch.object(c,'detect',return_value='niri'),patch.object(c.shutil,'which',return_value='/bin/niri'),patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'','')):
                c.install_niri_bind('/tmp/lolreplay',p); c.install_niri_bind('/tmp/lolreplay',p)
            self.assertIn('F8 repeat=false',p.read_text())
            backups=list(Path(d).glob('*.bak-*')); self.assertEqual(len(backups),1); self.assertEqual(backups[0].read_text(),text)
    def test_hyprland_no_config_change(self):
        with patch.object(c,'detect',return_value='hyprland'):
            with self.assertRaises(ValueError): c.install_niri_bind('/tmp/lolreplay','/tmp/config.kdl')
if __name__=='__main__': unittest.main(verbosity=2)
