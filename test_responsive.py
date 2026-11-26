"""Responsive layout and seeking tests; Qt smoke tests run when available."""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from lolreplay_preferences import layout_mode
from lolreplay_shortcuts import LABELS

ROOT = Path(__file__).resolve().parent

class ResponsiveTests(unittest.TestCase):
    def test_window_breakpoints(self):
        self.assertEqual(layout_mode(1920,1080), (False,False,False,False))
        self.assertEqual(layout_mode(1280,660), (True,False,False,False))
        self.assertEqual(layout_mode(800,600), (True,True,True,True))
        self.assertEqual(layout_mode(1280,720,120), (True,False,True,False))
        self.assertEqual(layout_mode(960,540,120), (True,True,True,True))
    def test_shortcut_groups_cover_every_action(self):
        tree=ast.parse((ROOT/'lolreplay-ui').read_text())
        method=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='build_key_settings')
        groups=next(n for n in method.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='groups')
        actions=[a for _,values in ast.literal_eval(groups.value) for a in values]
        self.assertCountEqual(actions,LABELS.keys())
    def test_seek_integration(self):
        for filename in ('lolreplay-ui','lolreplay_editor.py'):
            text=(ROOT/filename).read_text()
            self.assertIn('self.seek=SeekSlider()',text)
            self.assertIn('self.seek.seekRequested.connect(',text)
            self.assertNotIn('self.seek.sliderMoved.connect(',text)
        self.assertIn("'lolreplay_widgets.py'",(ROOT/'install.py').read_text())

    def test_editor_scroll_boundaries(self):
        ui=(ROOT/'lolreplay-ui').read_text()
        editor=(ROOT/'lolreplay_editor.py').read_text()
        self.assertIn("self.page(t('Editor'),'',scroll=False)",ui)
        self.assertIn('self.trim_scroll=PageScroll(trim)',editor)
        self.assertIn('self.rail=PageScroll(rail)',editor)
        self.assertIn('l.addWidget(self.video,3)',editor)
        self.assertNotIn('trim_layout.addWidget(self.video',editor)

    def test_library_scroll_boundaries(self):
        ui=(ROOT/'lolreplay-ui').read_text()
        tree=ast.parse(ui)
        library=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='build_library')
        source=ast.get_source_segment(ui,library)
        self.assertIn("self.page(t('Clips'),'',scroll=False)",source)
        self.assertIn('pv.addWidget(self.video,3)',source)
        self.assertIn('self.library_controls_scroll=PageScroll(controls)',source)
        self.assertIn('cv.addWidget(self.seek)',source)
        self.assertNotIn('cv.addWidget(self.video',source)
        self.assertIn('self.library_split.setMinimumHeight(0)',ui)
        self.assertNotIn('self.library_split.setMinimumHeight(590',ui)

    @unittest.skipUnless(importlib.util.find_spec('PySide6'), 'PySide6 not installed; run on a desktop with Qt')
    def test_qt_offscreen(self):
        # Use a separate process and temporary home; do not touch the user's library.
        script = r'''
import importlib.machinery, importlib.util
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtTest import QTest
from lolreplay_widgets import SeekSlider
from lolreplay_i18n import set_language
app=QApplication([]); app.setStyle('Fusion')
s=SeekSlider(); s.setRange(0,120000); s.resize(400,30); s.show(); app.processEvents()
values=[]; s.seekRequested.connect(values.append)
for x,expected in ((0,0),(200,60000),(399,120000)):
    QTest.mouseClick(s,Qt.MouseButton.LeftButton,pos=QPoint(x,15))
    assert values and abs(values[-1]-expected)<1000, (x,values)
s.setValue(30000); assert values[-1]>110000, values
QTest.keyClick(s,Qt.Key.Key_Right); assert values[-1]>30000, values
loader=importlib.machinery.SourceFileLoader('lr_ui','lolreplay-ui')
spec=importlib.util.spec_from_loader(loader.name,loader); ui=importlib.util.module_from_spec(spec); loader.exec_module(ui)
for locale in ('en_US','es_ES','de_DE','ja_JP'):
    set_language(locale); w=ui.Window(); w.show(); app.processEvents()
    assert w.settings_stack.count()==10
    assert len(w.key_fields)==27 and len(w.pref_controls)==16
    for width,height in ((1280,800),(1280,660),(800,600),(1920,1080)):
        w.resize(width,height); app.processEvents()
        for index in range(4):
            w.navigate(index); app.processEvents()
        w.navigate(1); app.processEvents()
        assert w.library_controls_scroll.isVisible()
        assert w.library_split.minimumHeight()==0
        if w.player:
            ancestor=w.video.parentWidget()
            while ancestor is not None:
                assert not isinstance(ancestor,QScrollArea), 'Library video inside a scroll area'
                ancestor=ancestor.parentWidget()
            assert w.video.isVisible()
        w.navigate(2); app.processEvents()
        if w.editor.player:
            ancestor=w.editor.video.parentWidget()
            while ancestor is not None:
                assert not isinstance(ancestor,QScrollArea), 'Native video inside a scroll area'
                ancestor=ancestor.parentWidget()
            assert w.editor.video.isVisible()
        assert w.editor.trim_scroll.isVisible() and w.editor.rail.isVisible()
        w.navigate(3); app.processEvents()
        w.select_settings(7); app.processEvents()
        assert w.settings_stack.currentIndex()==7
        if width==800: assert w.library_split.orientation()==Qt.Orientation.Vertical
        if width==1920: assert w.library_split.orientation()==Qt.Orientation.Horizontal
    w.close(); app.processEvents()
'''
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory); (home/'Videos/CrimsonClips').mkdir(parents=True)
            env={**os.environ,'HOME':directory,'XDG_CONFIG_HOME':str(home/'.config'),'XDG_DATA_HOME':str(home/'.local/share'),'XDG_RUNTIME_DIR':directory,'QT_QPA_PLATFORM':'offscreen'}
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)

if __name__=='__main__': unittest.main()
