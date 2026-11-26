import tempfile
import unittest
from pathlib import Path
from lolreplay_library import Library, EMPTY, matches, tags, time_matches, parse_duration, duration_text


class LibraryTests(unittest.TestCase):
    def test_persistence_and_rename(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d)/'library.sqlite3'
            original = ('/clips/a.mp4', 123, 456)
            renamed = ('/clips/b.mp4', 123, 456)
            value = (True, 'CS2', ('ace', 'ranked'))
            Library(db).save(original, value)
            self.assertEqual(Library(db).load()[original], value)
            Library(db).rename(original, renamed)
            self.assertEqual(Library(db).load(), {renamed:value})
            Library(db).save(renamed, EMPTY)
            self.assertEqual(Library(db).load(), {})

    def test_replaced_files_do_not_inherit_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            db = Library(Path(d)/'db')
            db.save(('a', 1, 10), (True, '', ()))
            self.assertEqual(db.load().get(('a', 2, 10), EMPTY), EMPTY)

    def test_search_and_filter(self):
        meta = (True, 'Counter-Strike 2', ('Ace', 'ranked'))
        self.assertTrue(matches('Mirage', meta, 'mirage ACE', True, 'Counter-Strike 2'))
        self.assertFalse(matches('Mirage', meta, 'inferno'))
        self.assertFalse(matches('Mirage', meta, game='Minecraft'))
        self.assertFalse(matches('Mirage', EMPTY, favorites=True))
        self.assertEqual(tags(' ace, ranked, ace, , '), ('ace','ranked'))


    def test_duration_and_date(self):
        now = 40*86400
        self.assertTrue(time_matches(int(now*1e9),30,1,'short',now))
        self.assertFalse(time_matches(int((now-2*86400)*1e9),30,1,'short',now))
        self.assertTrue(time_matches(int(now*1e9),120,0,'medium',now))
        self.assertFalse(time_matches(int(now*1e9),None,0,'long',now))
        self.assertTrue(time_matches(int(now*1e9),None,0,'',now))
        self.assertEqual(parse_duration('30.125\n'),30.125)
        for raw in ('N/A','nan','inf','-1','0',''):
            self.assertIsNone(parse_duration(raw))
        self.assertEqual(duration_text(120),'2:00')

    def test_media_cache(self):
        with tempfile.TemporaryDirectory() as d:
            db = Library(Path(d)/'db')
            key = ('a',1,10)
            db.save_duration(key,31.5)
            db.save_thumbnail(key,b'example')
            self.assertEqual(Library(db.path).load_durations()[key],31.5)
            self.assertEqual(Library(db.path).thumbnail(key),b'example')
            self.assertIsNone(db.thumbnail(('a',2,10)))
            for n in range(128):
                db.save_thumbnail((str(n),2,10),b'png')
            self.assertIsNone(db.thumbnail(key))
            self.assertIsNone(db.thumbnail(('missing',2,10)))


if __name__ == '__main__':
    unittest.main()
