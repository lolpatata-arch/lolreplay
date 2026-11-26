import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import lolreplay_games as games
import lolreplay_library as library

class GameTests(unittest.TestCase):
    def test_identify(self):
        self.assertEqual(games.identify({'class':'steam_app_730'},games.KNOWN),'Counter-Strike 2')
        self.assertEqual(games.identify({'class':'Minecraft 1.21'},games.KNOWN),'Minecraft')
        self.assertEqual(games.identify({'app_id':'rythia'},games.KNOWN),'Rythia')
        self.assertEqual(games.identify({'class':'firefox','title':'CS2'},games.KNOWN),'')
        self.assertEqual(games.identify({'class':'steam_app_999'},games.KNOWN),'')
        with patch.object(games,'steam_id',return_value='322170'):
            self.assertEqual(games.identify({'class':'game.exe','pid':123},games.KNOWN),'Geometry Dash')
    def test_history(self):
        samples=[(80,'CS2'),(90,'CS2'),(98,'CS2'),(99,'Minecraft'),(100,'')]
        self.assertEqual(games.choose_game(samples,30,100),'CS2')
        self.assertEqual(games.choose_game(samples,2,120),'')
        self.assertEqual(games.choose_game([(97,'CS2'),(99,'Minecraft')],5,100),'Minecraft')
    def test_external_steam_library(self):
        with tempfile.TemporaryDirectory() as d:
            home=Path(d); steam=home/'.local/share/Steam/steamapps'; steam.mkdir(parents=True)
            external=home/'external'; (external/'steamapps').mkdir(parents=True)
            (steam/'libraryfolders.vdf').write_text(f'"path" "{external}"\n')
            (external/'steamapps/appmanifest_12345.acf').write_text('"name" "Example Game"\n')
            self.assertEqual(games.steam_names(home)['12345'],'Example Game')
    def test_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); db=library.Library(root/'db'); clip=root/'a.mp4'; clip.write_bytes(b'clip'); key=library.file_key(clip)
            db.save(key,(True,'',('ace',))); db.assign_game(clip,'CS2'); db.assign_game(clip,'Other')
            self.assertEqual(db.load()[key],(True,'CS2',('ace',)))
            copy=root/'b.mp4'; copy.write_bytes(b'edit'); db.copy_metadata(key,library.file_key(copy))
            self.assertEqual(db.load()[library.file_key(copy)],(False,'CS2',('ace',)))
if __name__=='__main__': unittest.main()
