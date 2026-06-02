"""Điều phối tìm kiếm: SQLite có cấu trúc (tag/stats) + tùy chọn vector fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.query_parser import QueryParser

from config import Config
from database.sqlite_client import SQLiteClient
from database.vector_client import VectorStore
from pydantic import ValidationError

from models.search_filters import SearchFilters


class SearchService:
    def __init__(
        self,
        sqlite_client: SQLiteClient | None = None,
        vector_store: VectorStore | None = None,
        query_parser: QueryParser | None = None,
    ) -> None:
        self._sqlite = sqlite_client or SQLiteClient(Config.SQLITE_DB_PATH)
        self._vector = vector_store or VectorStore(Config.CHROMA_DB_DIR)
        self._parser = query_parser

    def _parser_instance(self):
        if self._parser is None:
            from services.query_parser import QueryParser

            self._parser = QueryParser()
        return self._parser

    def _enrich_vector_hits(self, raw: dict, source: str) -> list[dict[str, Any]]:
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
                    "_source": source,
                    "_snippet": doc,
                    "_distance": distance,
                }
            )
        return hits

    def _vector_search_limited(
        self,
        query: str,
        allowed_ids: set[int] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Vector search trên tập đã lọc (hoặc toàn bộ nếu allowed_ids None)."""
        best_by_id: dict[int, dict[str, Any]] = {}

        for collection, source in (
            (VectorStore.LEADER, "vector_leader"),
            (VectorStore.ACTIVE, "vector_active"),
        ):
            try:
                raw = self._vector.query(collection, query, n_results=limit * 3)
                for hit in self._enrich_vector_hits(raw, source):
                    mid = hit["monster_id"]
                    if allowed_ids is not None and mid not in allowed_ids:
                        continue
                    prev = best_by_id.get(mid)
                    if prev is None or hit["_distance"] < prev["_distance"]:
                        best_by_id[mid] = hit
            except Exception:
                continue

        return sorted(best_by_id.values(), key=lambda r: r["_distance"])[:limit]

    def structured_search(
        self,
        filters: SearchFilters,
        *,
        semantic_query: str | None = None,
        use_vector_fallback: bool = True,
    ) -> dict[str, Any]:
        """
        Bước 1: SQL theo tag/chỉ số (chính xác).
        Bước 2 (tùy chọn): vector trên tập đã lọc nếu có semantic_query.
        """
        sql_results = self._sqlite.search_structured(filters)
        for row in sql_results:
            row["_source"] = "sqlite_structured"

        vector_results: list[dict[str, Any]] = []
        if semantic_query and use_vector_fallback and sql_results:
            allowed = {r["monster_id"] for r in sql_results}
            vector_results = self._vector_search_limited(
                semantic_query,
                allowed,
                limit=filters.limit,
            )

        if vector_results:
            merged = vector_results
        else:
            merged = sql_results

        return {
            "filters": filters.model_dump(),
            "sqlite_structured": sql_results,
            "vector": vector_results,
            "merged": merged,
        }

    def ask(
        self,
        user_question: str,
        *,
        use_ai_parser: bool = True,
        use_vector_fallback: bool = True,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Luồng đầy đủ: Gemini → SearchFilters → SQLite → (vector trên tập nhỏ).
        """
        leader_tags = self._sqlite.list_leader_tags()
        active_tags = self._sqlite.list_active_tags()
        leader_effects = self._sqlite.list_leader_effect_types()
        active_effects = self._sqlite.list_active_effect_types()

        if use_ai_parser and Config.GEMINI_API_KEY:
            try:
                filters = self._parser_instance().parse(
                    user_question,
                    leader_tags,
                    active_tags,
                    leader_effects,
                    active_effects,
                )
            except (ValidationError, ValueError, KeyError, TypeError):
                from services.query_parser import QueryParser

                filters = QueryParser.parse_or_fallback(
                    user_question, leader_tags, active_tags
                )
            filters.limit = limit
        else:
            from services.query_parser import QueryParser

            filters = QueryParser.parse_or_fallback(
                user_question, leader_tags, active_tags
            )
            filters.limit = limit

        if not filters.has_structured_constraints():
            filters.monsters.name_query = user_question.strip()

        return self.structured_search(
            filters,
            semantic_query=user_question if use_vector_fallback else None,
            use_vector_fallback=use_vector_fallback,
        )

    def hybrid_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """Tương thích cũ: tên + vector (không parse AI)."""
        sqlite_results: list[dict[str, Any]] = []
        try:
            sqlite_results = self._sqlite.search_by_name(query, limit=limit)
            for row in sqlite_results:
                row["_source"] = "sqlite_name"
        except FileNotFoundError:
            pass

        vector_results = self._vector_search_limited(query, allowed_ids=None, limit=limit)

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
