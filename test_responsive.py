"""Responsive layout and seeking tests; Qt smoke tests run when available."""
import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from lolreplay_preferences import layout_mode, media_stacked
from lolreplay_shortcuts import LABELS

ROOT = Path(__file__).resolve().parent

class ResponsiveTests(unittest.TestCase):
    def test_window_breakpoints(self):
        self.assertEqual(layout_mode(1920,1080), (False,False,False,False))
        self.assertEqual(layout_mode(1280,660), (True,False,False,False))
        self.assertEqual(layout_mode(800,600), (True,True,True,True))
        self.assertEqual(layout_mode(1280,720,120), (True,False,True,False))
        self.assertEqual(layout_mode(960,540,120), (True,True,True,True))
    def test_media_layout_uses_both_dimensions(self):
        self.assertFalse(media_stacked(700,400))
        self.assertTrue(media_stacked(700,900))
        self.assertFalse(media_stacked(1100,900))
        self.assertTrue(media_stacked(380,400))
        self.assertTrue(media_stacked(900,900,120))
        self.assertFalse(media_stacked(900,450,120))
    def test_hidden_pages_and_adjustable_editor(self):
        ui=(ROOT/'lolreplay-ui').read_text()
        widgets=(ROOT/'lolreplay_widgets.py').read_text()
        editor=(ROOT/'lolreplay_editor.py').read_text()
        self.assertIn('self.stack=PageStack()',ui)
        self.assertIn('tabs=PageStack()',ui)
        self.assertIn('return QSize(0, 0)',widgets)
        self.assertIn('self.editor.set_stacked(stacked)',ui)
        self.assertIn('area=QSplitter(',editor)
        self.assertIn('area.setChildrenCollapsible(False)',editor)
        self.assertIn('fit_combo(self.sort)',ui)
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
from PySide6.QtCore import Qt, QPoint, QSize, QCoreApplication, QEvent, QObject, Signal
from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtTest import QTest
from lolreplay_widgets import SeekSlider, PlaybackSpeedButton
from lolreplay_i18n import set_language, LANGUAGES
from lolreplay_preferences import media_stacked, OPTIONS
from lolreplay_shortcuts import LABELS
app=QApplication([]); app.setStyle('Fusion')
class RatePlayer(QObject):
    playbackRateChanged=Signal(float)
    def __init__(self):
        super().__init__(); self.rate=1.
    def playbackRate(self): return self.rate
    def setPlaybackRate(self,rate):
        self.rate=rate; self.playbackRateChanged.emit(rate)
fake=RatePlayer()
button=PlaybackSpeedButton(fake,lambda p:fake.setPlaybackRate(p/100))
assert button.text()=='1×' and button.rate_actions[100].isChecked()
for percent in (25,50,75,100,125,150,175,200):
    button.rate_actions[percent].trigger()
    assert fake.playbackRate()==percent/100
    assert button.text()==f'{percent/100:g}×'
    assert sum(a.isChecked() for a in button.rate_actions.values())==1
fake.setPlaybackRate(.75); assert button.text()=='0.75×'
button.deleteLater()

s=SeekSlider(); s.setRange(0,120000); s.resize(400,30); s.show(); app.processEvents()
values=[]; s.seekRequested.connect(values.append)
for x,expected in ((0,0),(200,60000),(399,120000)):
    QTest.mouseClick(s,Qt.MouseButton.LeftButton,pos=QPoint(x,15))
    assert values and abs(values[-1]-expected)<1000, (x,values)
s.setValue(30000); assert values[-1]>110000, values
QTest.keyClick(s,Qt.Key.Key_Right); assert values[-1]>30000, values
loader=importlib.machinery.SourceFileLoader('lr_ui','lolreplay-ui')
spec=importlib.util.spec_from_loader(loader.name,loader); ui=importlib.util.module_from_spec(spec); loader.exec_module(ui)
def contained(widget, parent):
    pos=widget.mapTo(parent,QPoint(0,0))
    assert pos.x()>=0 and pos.y()>=0 and pos.x()+widget.width()<=parent.width()+2 and pos.y()+widget.height()<=parent.height()+2, (locale,scale,width,height,widget.objectName(),widget.size(),parent.size(),pos)

sizes=((640,480),(800,600),(960,540),(1024,768),(1280,720),(1366,768),(1440,900),(1920,1080),(2560,1440),(3840,2160),(720,1280),(3440,1440))
for locale in LANGUAGES:
    set_language(locale); w=ui.Window(); w.show(); app.processEvents()
    try:
        assert w.settings_stack.count()==11
        assert len(w.dashboard_cards)==4 and len(w.widgets_by_id)==20
        assert w.hub.objectName()=='commandHub' and w.dock.objectName()=='bottomDock'
        assert len(w.nav)==4 and all(b.parentWidget()==w.dock for b in w.nav)
        assert w.outer_layout.itemAt(0).widget()==w.hub
        assert w.outer_layout.itemAt(w.outer_layout.count()-1).layout()==w.dock_row
        assert w.hub_save.isEnabled()==w.save_btn.isEnabled()
        assert w.hub_toggle.isEnabled()==(w.stop_btn.isEnabled() if w.active is True else w.start_btn.isEnabled())
        assert w.hub_save.accessibleName()==w.save_btn.text()
        assert w.dashboard_total.text()==str(len(w.snapshot or []))
        assert w.dashboard_favorites.text()==str(sum(bool(w.metadata_for(key[0])[0]) for key in (w.snapshot or [])))
        assert w.dashboard_history.text()==w.format_duration_label(w.buffer_seconds)
        w.reflow_dashboard(False,False)
        assert w.overview_layout.getItemPosition(w.overview_layout.indexOf(w.dashboard_hero))==(0,0,1,2)
        assert w.overview_layout.getItemPosition(w.overview_layout.indexOf(w.dashboard_gallery))==(2,0,1,3)
        assert w.overview_layout.getItemPosition(w.overview_layout.indexOf(w.overview_rail))==(0,2,1,1)
        assert w.overview_layout.getItemPosition(w.overview_layout.indexOf(w.dashboard_session))==(1,0,1,3)
        w.reflow_dashboard(True,True)
        assert w.overview_layout.getItemPosition(w.overview_layout.indexOf(w.overview_rail))==(0,0,1,1)
        w.navigate(0); app.processEvents()
        import lolreplay_dashboard as dashboard
        assert w.dashboard_layout==dashboard.defaults()
        assert not w.dashboard_favorite_card.isVisible() and not w.dashboard_storage_card.isVisible()
        w.reflow_dashboard(False,False)
        w.toggle_widget_edit(True); app.processEvents()
        assert w.widget_headers['hero'].isVisible()
        w.widget_controls['hero'][0].setCurrentIndex(0)
        assert w.dashboard_layout['widgets']['hero']['width']==1
        w.widget_controls['hero'][1].setCurrentIndex(2)
        assert w.dashboard_layout['widgets']['hero']['height']=='large' and w.art.minimumHeight()==460
        w.move_dashboard_widget('gallery','hero')
        assert w.dashboard_layout['order'][0]=='gallery'
        w.change_dashboard_widget('capture',visible=False)
        assert w.overview_layout.indexOf(w.overview_rail)==-1 and not w.overview_rail.isVisible()
        assert w.hub.isVisible() and w.hub_save.isEnabled()==w.save_btn.isEnabled()
        w.change_dashboard_widget('favorites',visible=True); w.change_dashboard_widget('storage',visible=True); app.processEvents()
        assert w.dashboard_favorite_card.isVisible() and w.dashboard_storage_card.isVisible()
        assert w.widget_favorite_count.text()==w.dashboard_favorites.text()
        assert w.widget_disk.text()==w.disk.text()
        for key in dashboard.IDS[6:]: w.change_dashboard_widget(key,visible=True)
        app.processEvents()
        assert not w.overview_rail.isVisible(), 'Capture must stay hidden until restored'
        assert all(card.isVisible() for key,card in w.widgets_by_id.items() if key!='capture'), [key for key,card in w.widgets_by_id.items() if key!='capture' and not card.isVisible()]
        w.change_dashboard_widget('capture',visible=True); app.processEvents()
        assert all(card.isVisible() for card in w.widgets_by_id.values()), [key for key,card in w.widgets_by_id.items() if not card.isVisible()]
        assert w.overview_layout.count()==20
        assert w.widget_values['size'].text()==w.dashboard_size.text()
        assert w.widget_values['hotkey'].text()==(w.global_key or '—')
        assert w.widget_actions['quick_save'].isEnabled()==w.save_btn.isEnabled()
        assert w.widget_actions['mic'].isEnabled()==w.mic_btn.isEnabled()
        assert w.widget_values['duration'].text()==w.format_duration_label(w.duration)
        assert w.widget_values['buffer'].text()==w.dashboard_history.text()
        assert w.widget_actions['latest'].isEnabled()==bool(w.snapshot)
        assert len(w.widget_activity)==7
        assert w.widget_values['today'].text()==str(w.widget_summary['counts'][-1])
        assert ui.read_json(ui.UI_CONFIG)['dashboard_layout']==w.dashboard_layout
        for key in dashboard.IDS: w.change_dashboard_widget(key,visible=False)
        assert not w.widget_empty.isHidden() and w.overview_layout.count()==0
        w.reset_dashboard(); w.toggle_widget_edit(False)
        assert w.dashboard_layout==dashboard.defaults() and all(h.isHidden() for h in w.widget_headers.values())
        assert ui.read_json(ui.UI_CONFIG)['dashboard_layout']==dashboard.defaults()
        w.update_layout(force=True)
        assert w.settings_list.objectName()=='settingsNavigation'
        assert w.settings_list.count()==11 and w.settings_selector.count()==11
        assert all(w.settings_list.item(i).data(Qt.ItemDataRole.UserRole+1) for i in range(11))
        assert len(w.settings_previews)==2
        assert set(w.pref_sliders)=={'text_scale','wallpaper_dim','refresh_ms'}
        w.navigate(3); app.processEvents()
        speed_title=w.pref_controls['playback_speed'].accessibleName(); w.settings_search.setText(speed_title)
        app.processEvents(); assert w.settings_results.count()>0
        found=[i for i in range(w.settings_results.count()) if w.settings_index[w.settings_results.item(i).data(Qt.ItemDataRole.UserRole)][2] is w.pref_controls['playback_speed']]
        assert found, speed_title
        w.open_setting_result(w.settings_results.item(found[0])); app.processEvents()
        assert w.settings_stack.currentIndex()==5 and not w.settings_search.text()
        w.settings_search.setText('zzzzzzzzzzzzqzx'); app.processEvents(); assert w.settings_results.count()==0 and not w.settings_search_hint.isHidden()
        w.settings_search.clear(); assert w.settings_search_hint.isHidden()
        w.select_settings(4); app.processEvents(); assert w.settings_previews[1].isVisible()
        original=w.prefs['wallpaper_dim']; slider=w.pref_sliders['wallpaper_dim']; slider.setValue(2)
        assert w.prefs['wallpaper_dim']==30 and w.pref_controls['wallpaper_dim'].currentData()==30
        w.set_preference('wallpaper_dim',original); assert slider.value()==w.pref_controls['wallpaper_dim'].currentIndex()
        switch=w.pref_controls['accent_glow']; previous=switch.isChecked(); switch.click(); assert w.prefs['accent_glow']==(not previous); switch.click(); assert w.prefs['accent_glow']==previous
        assert w.settings_previews[1].grab().size().width()>0
        w.navigate(0); app.processEvents()
        assert w.background_preview.objectName()=='wallpaperPreview'
        assert w.background_btn.property('lrIcon')=='image'
        assert not w.background_btn.icon().isNull()
        assert w.background_choice.count()==8
        for mode in ui.backgrounds.STYLES:
            w.save_background(mode); assert not w.art.selected_art().isNull(), mode
        custom_path=ui.HOME/'test-background.png'; custom=ui.QPixmap(640,360); custom.fill(ui.QColor('#ba1234')); assert custom.save(str(custom_path),'PNG')
        loaded=ui.backgrounds.load_image(str(custom_path)); assert not loaded.isNull()
        w.save_background('image',str(custom_path),loaded); assert not w.art.selected_art().isNull()
        assert ui.read_json(ui.UI_CONFIG)['replay_background']=={'mode':'image','path':str(custom_path)}
        custom_path.unlink(); w.save_background('image',str(custom_path)); assert w.art.selected_art().isNull()
        w.save_background('last_clip'); assert w.replay_background['mode']=='last_clip'
        if w.snapshot:
            assert w.latest_title.text()==ui.Path(w.snapshot[0][0]).stem
            assert not w.latest_btn.isHidden() and not w.latest_edit.isHidden()
        w.save_background('logo'); assert w.art.selected_art() is None
        assert w.latest_title.text()==ui.t('Classic logo') and not w.latest_meta.text()
        assert w.latest_btn.isHidden() and w.latest_edit.isHidden() and not w.background_btn.isHidden()
        if w.snapshot: assert w.recent.item(0).data(ui.Qt.ItemDataRole.UserRole)==w.snapshot[0][0]
        assert set(w.key_fields)==set(LABELS), (set(w.key_fields),set(LABELS))
        assert set(w.pref_controls)==set(OPTIONS), (set(w.pref_controls),set(OPTIONS))
        for style in ('shell','glass','minimal','classic'):
            w.set_preference('visual_style',style); app.processEvents(); assert w.prefs['visual_style']==style
        w.set_preference('visual_style','shell')
        w.set_preference('icon_navigation',True); assert all(not b.text() for b in w.nav)
        w.set_preference('icon_navigation',False)
        assert {'Obsidian','Arctic','Ember','Rose Quartz'}.issubset(ui.THEMES)
        w.prefs['thumbnails']=False
        if w.list.count():
            w.navigate(1); w.list.setCurrentRow(0); app.processEvents()
            assert w.preview_path and w.player.source().isLocalFile()
            w.navigate(2); app.processEvents(); assert w.editor.source and w.editor.total>0
        for scale in (100,110,120):
            w.prefs['text_scale']=scale; w.prefs['large_targets']=(scale==120); w.apply_preferences(refresh=False)
            for width,height in sizes:
                w.resize(width,height); app.processEvents()
                for index in range(4):
                    w.navigate(index); app.processEvents()
                    assert w.width()<=width+2 and w.height()<=height+2, (locale,scale,width,height,w.size(),index)
                    page=w.stack.currentWidget(); contained(page,w.stack)
                    assert page.width()>0 and page.height()>0
                    assert w.hub.isVisible() and w.dock.isVisible()
                    assert w.hub.geometry().bottom()<w.body.geometry().top()
                    assert w.dock.geometry().top()>w.body.geometry().bottom()
                    assert sum(b.isChecked() for b in w.nav)==1 and w.nav[index].isChecked()
                    assert all(b.width()>0 and b.height()>0 for b in w.nav)
                w.navigate(0); app.processEvents()
                for card in w.dashboard_cards:
                    assert card.isVisible() and card.width()>0 and card.height()>0
                assert w.start_btn.isVisible() and w.save_btn.isVisible() and w.stop_btn.isVisible()
                w.navigate(1); app.processEvents()
                assert w.library_controls_scroll.isVisible() and w.library_controls_scroll.height()>0
                assert w.library_split.minimumHeight()==0
                assert w.compact_filters.isVisible()!=w.filter_panel.isVisible()
                assert w.list.width()>0 and w.list.height()>0
                contained(w.library_split,w.stack.currentWidget())
                if w.player:
                    ancestor=w.video.parentWidget()
                    while ancestor is not None:
                        assert not isinstance(ancestor,QScrollArea), 'Library video inside a scroll area'
                        ancestor=ancestor.parentWidget()
                    assert w.video.isVisible() and w.video.height()>0
                    contained(w.video,w.stack.currentWidget())
                w.navigate(2); app.processEvents()
                if w.editor.player:
                    ancestor=w.editor.video.parentWidget()
                    while ancestor is not None:
                        assert not isinstance(ancestor,QScrollArea), 'Native video inside a scroll area'
                        ancestor=ancestor.parentWidget()
                    assert w.editor.video.isVisible() and w.editor.video.height()>0
                    contained(w.editor.video,w.stack.currentWidget())
                assert w.editor.trim_scroll.isVisible() and w.editor.rail.isVisible()
                assert w.editor.trim_scroll.height()>0 and w.editor.rail.height()>0
                contained(w.editor.area,w.editor)
                w.navigate(3); app.processEvents()
                for category in range(11):
                    w.select_settings(category); app.processEvents()
                    assert w.settings_stack.currentIndex()==category
                    contained(w.settings_stack.currentWidget(),w.settings_stack)
                assert w.library_split.orientation()==w.editor.area.orientation()
                if (width,height)==(720,1280): assert w.library_split.orientation()==Qt.Orientation.Vertical
                if (width,height)==(1920,1080): assert w.library_split.orientation()==Qt.Orientation.Horizontal
        if w.player and w.list.count():
            w.navigate(1); w.list.setCurrentRow(0); app.processEvents()
            assert w.speed_btn.isEnabled()
            source=w.player.source(); state=w.player.playbackState()
            from unittest.mock import patch
            with patch.object(w,'apply_theme',side_effect=AssertionError('rate change rebuilt theme')), patch.object(w,'refresh_library',side_effect=AssertionError('rate change refreshed library')):
                w.speed_btn.rate_actions[175].trigger()
                assert w.prefs['playback_speed']==175 and w.player.playbackRate()==1.75
                assert w.speed_btn.text()=='1.75×'
                assert w.pref_controls['playback_speed'].currentData()==175
                assert ui.read_json(ui.UI_CONFIG)['preferences']['playback_speed']==175
                assert w.player.source()==source and w.player.playbackState()==state
                dialog=ui.show_fullscreen(w,w.player,w.video,w.play); app.processEvents()
                assert w.player.videoOutput()==dialog.video and dialog.speed_btn.text()=='1.75×'
                dialog.speed_btn.rate_actions[50].trigger()
                assert w.speed_btn.text()=='0.5×' and w.player.playbackRate()==.5
                assert w.pref_controls['playback_speed'].currentData()==50
                dialog.reject(); app.processEvents(); assert w.player.videoOutput()==w.video
                w.set_playback_speed(100)
                assert w.speed_btn.text()=='1×'
            w.list.setCurrentRow(-1); app.processEvents(); assert not w.speed_btn.isEnabled()
    finally:
        w.exiting=True; w.close(); w.deleteLater(); QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete.value); app.processEvents()
'''
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory); clips=home/'Videos/CrimsonClips'; clips.mkdir(parents=True)
            if shutil.which('ffmpeg') and shutil.which('ffprobe'):
                subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=160x90:rate=12','-t','2','-c:v','libx264',str(clips/('Test clip with a long filename '+('x'*120)+'.mp4'))],check=True,timeout=30)
            env={**os.environ,'HOME':directory,'XDG_CONFIG_HOME':str(home/'.config'),'XDG_DATA_HOME':str(home/'.local/share'),'XDG_RUNTIME_DIR':directory,'QT_QPA_PLATFORM':'offscreen'}
            result=subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)

if __name__=='__main__': unittest.main()
