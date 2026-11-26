import tempfile
import unittest
from pathlib import Path
from lolreplay_library import Library, EMPTY, matches, tags


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


if __name__ == '__main__':
    unittest.main()
