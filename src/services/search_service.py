"""Điều phối luồng Hybrid Search (SQLite + Vector)."""

from config import Config
from database.sqlite_client import SQLiteClient
from database.vector_client import VectorClient


class SearchService:
    def __init__(
        self,
        sqlite_client: SQLiteClient | None = None,
        vector_client: VectorClient | None = None,
    ) -> None:
        self._sqlite = sqlite_client or SQLiteClient(Config.SQLITE_DB_PATH)
        self._vector = vector_client or VectorClient(Config.CHROMA_DB_DIR)

    def hybrid_search(self, query: str) -> dict:
        """Kết hợp kết quả SQLite (structured) và ChromaDB (semantic)."""
        sqlite_results: list = []
        vector_results: dict = {"documents": [], "metadatas": []}

        try:
            sqlite_results = self._sqlite.search_monsters(query)
        except FileNotFoundError:
            pass

        try:
            vector_results = self._vector.query(query)
        except Exception:
            pass

        return {
            "query": query,
            "sqlite": sqlite_results,
            "vector": vector_results,
        }
