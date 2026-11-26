"""Local smart-library metadata. Never modifies or removes media files."""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3
import math
import os
import time


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


def time_matches(mtime_ns, duration, days=0, length='', now=None):
    if days and mtime_ns / 1e9 < (time.time() if now is None else now) - days * 86400:
        return False
    if not length:
        return True
    if duration is None:
        return False
    if length == 'short':
        return duration <= 30
    if length == 'medium':
        return 30 < duration <= 120
    if length == 'long':
        return duration > 120
    return False


def parse_duration(raw):
    try:
        value = float(raw.strip())
        return value if math.isfinite(value) and value > 0 else None
    except (ValueError, TypeError, AttributeError):
        return None


def duration_text(seconds):
    n = max(0, round(seconds))
    return f'{n // 60}:{n % 60:02d}'


EMPTY = (False, '', ())


def default_path():
    return Path(os.environ.get('XDG_STATE_HOME',str(Path.home()/'.local/state')))/'lolreplay/library.sqlite3'


def file_key(path):
    path=Path(path).absolute(); st=path.stat()
    return str(path),st.st_mtime_ns,st.st_size


class Library:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connection(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=0.25)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS clips (path TEXT, mtime INTEGER, size INTEGER, favorite INTEGER NOT NULL, game TEXT NOT NULL, tags TEXT NOT NULL, PRIMARY KEY(path, mtime, size))')
            db.execute('CREATE TABLE IF NOT EXISTS durations (path TEXT, mtime INTEGER, size INTEGER, seconds REAL NOT NULL, PRIMARY KEY(path,mtime,size))')
            db.execute('CREATE TABLE IF NOT EXISTS thumbnails (path TEXT, mtime INTEGER, size INTEGER, png BLOB NOT NULL, saved INTEGER NOT NULL, PRIMARY KEY(path,mtime,size))')
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

    def assign_game(self,path,game):
        key=file_key(path)
        with self.connection() as db:
            db.execute("INSERT INTO clips VALUES (?,?,?,?,?,?) ON CONFLICT(path,mtime,size) DO UPDATE SET game=excluded.game WHERE clips.game=''",(*key,0,game,''))

    def copy_metadata(self,old,new,replace=False):
        with self.connection() as db:
            row=db.execute('SELECT favorite,game,tags FROM clips WHERE path=? AND mtime=? AND size=?',old).fetchone()
            if row:
                f,g,t=row
                db.execute('INSERT OR REPLACE INTO clips VALUES (?,?,?,?,?,?)',(*new,f if replace else 0,g,t))
                if replace and old!=new: db.execute('DELETE FROM clips WHERE path=? AND mtime=? AND size=?',old)

    def load_durations(self):
        with self.connection() as db:
            return {(p,m,s):v for p,m,s,v in db.execute('SELECT path,mtime,size,seconds FROM durations')}

    def save_duration(self, key, seconds):
        if seconds is None or not math.isfinite(seconds) or seconds <= 0:
            return
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO durations VALUES (?,?,?,?)', (*key,seconds))
            db.execute('DELETE FROM durations WHERE rowid IN (SELECT rowid FROM durations ORDER BY rowid DESC LIMIT -1 OFFSET 10000)')

    def thumbnail(self, key):
        with self.connection() as db:
            row = db.execute('SELECT png FROM thumbnails WHERE path=? AND mtime=? AND size=?',key).fetchone()
            return row[0] if row else None

    def save_thumbnail(self, key, png):
        if not png or len(png) > 1024*1024:
            return
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO thumbnails VALUES (?,?,?,?,?)',(*key,png,time.time_ns()))
            db.execute('DELETE FROM thumbnails WHERE rowid IN (SELECT rowid FROM thumbnails ORDER BY saved DESC,rowid DESC LIMIT -1 OFFSET 128)')
