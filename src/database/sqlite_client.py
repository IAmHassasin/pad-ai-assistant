import sqlite3
from pathlib import Path
from typing import Any


class SQLiteClient:
    """Quản lý kết nối và truy vấn SQLite (monster / card metadata)."""

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.db_path}")
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def search_monsters(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Tìm monster theo tên (placeholder — mở rộng schema sau)."""
        conn = self.connect()
        cursor = conn.execute(
            """
            SELECT name FROM monsters
            WHERE name LIKE ?
            LIMIT ?
            """,
            (f"%{query}%", limit),
        )
        return [dict(row) for row in cursor.fetchall()]
