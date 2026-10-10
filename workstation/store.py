from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
import time
import uuid


def new_id(prefix):
    return prefix + '-' + uuid.uuid4().hex[:16]


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'state.sqlite3'
        with self.transaction() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY, title TEXT NOT NULL, worker_id TEXT NOT NULL,
              version INTEGER NOT NULL, approved_version INTEGER NOT NULL DEFAULT 0,
              plan_hash TEXT NOT NULL, requirements TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL, node TEXT NOT NULL,
              role TEXT NOT NULL, kind TEXT NOT NULL, dependencies TEXT NOT NULL,
              status TEXT NOT NULL, generation INTEGER NOT NULL DEFAULT 1,
              attempt INTEGER NOT NULL DEFAULT 0, review_round INTEGER NOT NULL DEFAULT 0,
              lock_key TEXT NOT NULL, config TEXT NOT NULL, active_run TEXT,
              error TEXT, checkpoint TEXT, UNIQUE(project_id, node));
            CREATE TABLE IF NOT EXISTS runs (
              id TEXT PRIMARY KEY, task_id TEXT NOT NULL, project_version INTEGER NOT NULL,
              generation INTEGER NOT NULL, author TEXT NOT NULL, status TEXT NOT NULL,
              input_hash TEXT NOT NULL, result TEXT, started REAL NOT NULL, ended REAL);
            CREATE UNIQUE INDEX IF NOT EXISTS active_run ON runs(task_id) WHERE status='running';
            CREATE TABLE IF NOT EXISTS resource_locks (key TEXT PRIMARY KEY, run_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews (
              id TEXT PRIMARY KEY, run_id TEXT NOT NULL, dimension TEXT NOT NULL,
              reviewer TEXT NOT NULL, verdict TEXT NOT NULL, findings TEXT NOT NULL,
              created REAL NOT NULL, UNIQUE(run_id, dimension));
            CREATE TABLE IF NOT EXISTS artifacts (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT NOT NULL,
              run_id TEXT NOT NULL, generation INTEGER NOT NULL, name TEXT NOT NULL,
              path TEXT NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
              stale INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL, card TEXT NOT NULL, created REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS issues (
              id TEXT PRIMARY KEY, project_id TEXT NOT NULL, task_id TEXT NOT NULL,
              fingerprint TEXT UNIQUE NOT NULL, severity TEXT NOT NULL,
              body TEXT NOT NULL, status TEXT NOT NULL, mirror_status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
              kind TEXT NOT NULL, body TEXT NOT NULL, created REAL NOT NULL);
            ''')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.db, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def event(db, project_id, kind, body):
        db.execute('INSERT INTO events(project_id,kind,body,created) VALUES(?,?,?,?)',
                   (project_id, kind, encode(body), time.time()))

    def snapshot(self, project_id):
        with self.transaction() as db:
            project = db.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
            if project is None:
                return None
            result = {'project': dict(project)}
            for table in ('tasks', 'artifacts', 'decisions', 'issues', 'events'):
                result[table] = [dict(r) for r in db.execute(
                    'SELECT * FROM ' + table + ' WHERE project_id=? ORDER BY rowid', (project_id,))]
            result['reviews'] = [dict(r) for r in db.execute('''
              SELECT reviews.* FROM reviews JOIN runs ON reviews.run_id=runs.id
              JOIN tasks ON runs.task_id=tasks.id WHERE tasks.project_id=?''', (project_id,))]
        for table in ('tasks', 'decisions', 'issues', 'events', 'reviews'):
            for row in result[table]:
                for key in ('dependencies', 'config', 'checkpoint', 'card', 'body', 'findings'):
                    if row.get(key) is not None:
                        row[key] = json.loads(row[key])
        result['project']['requirements'] = json.loads(result['project']['requirements'])
        return result
