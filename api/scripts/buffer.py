# buffer.py
import sqlite3
from typing import List, Tuple

class SQLiteBuffer:
    """
    Classe pour gérer une base de données SQLite servant de buffer
    pour les abstracts extraits avant leur traitement.
    """
    def __init__(self, db_path="buffer.db"):
        # `check_same_thread=False` est nécessaire pour l'utilisation avec FastAPI
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        """Crée la table `abstracts` si elle n'existe pas."""
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS abstracts (
                    id TEXT PRIMARY KEY,
                    abstract TEXT NOT NULL,
                    processed INTEGER DEFAULT 0
                )
            ''')

    def add_abstract(self, article_id: str, abstract: str):
        """Ajoute ou remplace un abstract dans le buffer."""
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO abstracts (id, abstract, processed) VALUES (?, ?, 0)",
                (article_id, abstract)
            )

    def get_unprocessed_batch(self, batch_size: int = 50) -> List[Tuple[str, str]]:
        """Récupère un lot d'abstracts non traités."""
        cursor = self.conn.execute(
            "SELECT id, abstract FROM abstracts WHERE processed = 0 LIMIT ?",
            (batch_size,)
        )
        return [(row["id"], row["abstract"]) for row in cursor.fetchall()]

    def mark_as_processed(self, article_id: str):
        """Marque un abstract comme traité."""
        with self.conn:
            self.conn.execute(
                "UPDATE abstracts SET processed = 1 WHERE id = ?", (article_id,)
            )

    def clear_all(self) -> int:
        """Vide complètement la table et retourne le nombre de lignes supprimées."""
        with self.conn:
            cursor = self.conn.execute("SELECT COUNT(*) FROM abstracts")
            count = cursor.fetchone()[0]
            self.conn.execute("DELETE FROM abstracts")
        return count

