import json
import sqlite3
from pathlib import Path


class Store:
    def __init__(self, path="private/pagewatch.sqlite3"):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(target)
        self.db.execute("CREATE TABLE IF NOT EXISTS baselines (page TEXT, post TEXT, snapshot TEXT, PRIMARY KEY(page, post))")
        self.db.execute("CREATE TABLE IF NOT EXISTS scans (seq INTEGER PRIMARY KEY, page TEXT, kind TEXT, payload TEXT)")
        self.db.commit()

    def baseline(self, page, post):
        row = self.db.execute("SELECT snapshot FROM baselines WHERE page=? AND post=?", (page, post)).fetchone()
        return json.loads(row[0]) if row else None

    def accept(self, page, post, snapshot):
        self.db.execute("INSERT OR REPLACE INTO baselines VALUES (?, ?, ?)", (page, post, json.dumps(snapshot, ensure_ascii=False)))
        self.db.commit()

    def save(self, page, result):
        self.db.execute("INSERT INTO scans(page, kind, payload) VALUES (?, ?, ?)", (page, result["kind"], json.dumps(result, ensure_ascii=False)))
        self.db.commit()

    def latest(self, page, kind):
        row = self.db.execute("SELECT payload FROM scans WHERE page=? AND kind=? ORDER BY seq DESC LIMIT 1", (page, kind)).fetchone()
        return json.loads(row[0]) if row else None

    def close(self):
        self.db.close()
