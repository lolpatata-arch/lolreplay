"""Local smart-library metadata. Never modifies or removes media files."""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3


def tags(value):
    return tuple(dict.fromkeys(t.strip() for t in value.split(',') if t.strip()))


def matches(name, metadata, query='', favorites=False, game=''):
    favorite, category, labels = metadata
    if favorites and not favorite:
        return False
    if game and category != game:
        return False
    haystack = ' '.join((name, category, *labels)).casefold()
    return all(word in haystack for word in query.casefold().split())


EMPTY = (False, '', ())


class Library:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=0.25)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS clips (path TEXT, mtime INTEGER, size INTEGER, favorite INTEGER NOT NULL, game TEXT NOT NULL, tags TEXT NOT NULL, PRIMARY KEY(path, mtime, size))')
            yield db

    def load(self):
        with self.connection() as db:
            return {(p, m, s): (bool(f), g, tags(t)) for p, m, s, f, g, t in db.execute('SELECT path,mtime,size,favorite,game,tags FROM clips')}

    def save(self, key, value):
        f, g, labels = value
        with self.connection() as db:
            if value == EMPTY:
                db.execute('DELETE FROM clips WHERE path=? AND mtime=? AND size=?', key)
            else:
                db.execute('INSERT OR REPLACE INTO clips VALUES (?,?,?,?,?,?)', (*key, int(f), g, ','.join(labels)))

    def rename(self, old, new):
        with self.connection() as db:
            db.execute('UPDATE clips SET path=?, mtime=?, size=? WHERE path=? AND mtime=? AND size=?', (*new, *old))
