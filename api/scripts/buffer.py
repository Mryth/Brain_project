"""SQLite buffer for abstracts fetched from PubMed before they are processed.
(Unchanged in spirit from v1; carries title so the graph/RAG can cite it.)"""
import sqlite3
from typing import List, Tuple


class SQLiteBuffer:
    def __init__(self, db_path: str = "buffer.db"):
        # check_same_thread=False so FastAPI's threadpool can use the connection
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS abstracts (
                   pmid TEXT PRIMARY KEY,
                   title TEXT,
                   abstract TEXT,
                   processed INTEGER DEFAULT 0
               )"""
        )
        self.conn.commit()

    def add_abstract(self, pmid: str, abstract: str, title: str = "") -> bool:
        """Insert an abstract if new. Returns True if inserted."""
        try:
            self.conn.execute(
                "INSERT OR IGNORE INTO abstracts (pmid, title, abstract) VALUES (?, ?, ?)",
                (pmid, title, abstract),
            )
            self.conn.commit()
            return self.conn.total_changes > 0
        except sqlite3.Error:
            return False

    def get_unprocessed(self) -> List[Tuple[str, str, str]]:
        """Return [(pmid, title, abstract), ...] not yet pushed to Neo4j."""
        cur = self.conn.execute(
            "SELECT pmid, title, abstract FROM abstracts WHERE processed = 0"
        )
        return cur.fetchall()

    def mark_processed(self, pmid: str):
        self.conn.execute("UPDATE abstracts SET processed = 1 WHERE pmid = ?", (pmid,))
        self.conn.commit()

    def close(self):
        self.conn.close()
