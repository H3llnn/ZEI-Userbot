"""Per-account settings; secrets are encrypted by the hosting Gate."""
import json
import re
import sqlite3
from pathlib import Path


def validate_prefix(value):
    if not isinstance(value, str) or not re.fullmatch(r"[^\w\s]{1,3}", value):
        raise ValueError("Prefix harus 1–3 simbol tanpa spasi.")
    return value


class State:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS notes (name TEXT PRIMARY KEY, text TEXT NOT NULL)")
        self.conn.commit()

    def get(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key, value):
        if key == "prefix": validate_prefix(value)
        with self.conn:
            self.conn.execute("INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value)))

    @property
    def prefix(self):
        return self.get("prefix", ".")

    def close(self):
        self.conn.close()
