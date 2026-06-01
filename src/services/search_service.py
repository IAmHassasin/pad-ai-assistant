"""Điều phối luồng Hybrid Search (SQLite + Vector)."""

from typing import Any

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

    def _enrich_vector_hits(self, raw: dict) -> list[dict[str, Any]]:
        """Map kết quả ChromaDB về monster đầy đủ từ SQLite."""
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        hits: list[dict[str, Any]] = []
        for doc, meta, distance in zip(documents, metadatas, distances):
            monster_id = meta.get("monster_id") if meta else None
            if monster_id is None:
                continue
            row = self._sqlite.get_by_id(int(monster_id))
            if row is None:
                continue
            hits.append(
                {
                    **row,
                    "_source": "vector",
                    "_snippet": doc,
                    "_distance": distance,
                }
            )
        return hits

    def hybrid_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Kết hợp kết quả SQLite (tên chính xác) và ChromaDB (ngữ nghĩa)."""
        sqlite_results: list[dict[str, Any]] = []
        vector_results: list[dict[str, Any]] = []

        try:
            sqlite_results = self._sqlite.search_by_name(query, limit=limit)
            for row in sqlite_results:
                row["_source"] = "sqlite"
        except FileNotFoundError:
            pass

        try:
            raw = self._vector.query(query, n_results=limit)
            vector_results = self._enrich_vector_hits(raw)
        except Exception:
            pass

        seen_ids = {row["monster_id"] for row in sqlite_results}
        merged = list(sqlite_results)
        for row in vector_results:
            if row["monster_id"] not in seen_ids:
                merged.append(row)
                seen_ids.add(row["monster_id"])

        return {
            "query": query,
            "sqlite": sqlite_results,
            "vector": vector_results,
            "merged": merged,
        }
