import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class SQLiteRepository:
    def __init__(self, path: str, timeout: float = 5.0) -> None:
        self.path = path
        self.timeout = timeout

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=self.timeout)
        connection.execute("PRAGMA busy_timeout = 5000;")
        return connection

    def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL;")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    error TEXT NULL,
                    created_at TEXT NOT NULL
                )"""
            )

    def has_message(self, message_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ?", (message_id,)
            ).fetchone()
        return row is not None

    def mark_message(self, message_id: str, status: str, error: str | None = None) -> None:
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO processed_messages (message_id, status, error, created_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(message_id) DO UPDATE SET status = excluded.status,
                       error = excluded.error""",
                (message_id, status, error, created_at),
            )

    def get_status(self, message_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM processed_messages WHERE message_id = ?", (message_id,)
            ).fetchone()
        return row[0] if row else None

    def get_error(self, message_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT error FROM processed_messages WHERE message_id = ?", (message_id,)
            ).fetchone()
        return row[0] if row else None

    def is_ready(self) -> bool:
        try:
            with self._connect() as connection:
                connection.execute("SELECT 1 FROM processed_messages LIMIT 1")
            return True
        except sqlite3.Error:
            return False
