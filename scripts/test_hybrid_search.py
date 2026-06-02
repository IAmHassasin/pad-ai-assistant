"""Smoke test: hybrid_search (tên + vector) và structured_search (tag SQL)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from models.search_filters import ActiveFilters, SearchFilters
from services.search_service import SearchService

QUERIES = [
    "Ra",  # SQLite: tên chính xác
    "leader skill reduces cooldown for fire team",  # ChromaDB: ngữ nghĩa
]


def main() -> None:
    service = SearchService()

    structured = service.structured_search(
        SearchFilters(active=ActiveFilters(part_tag_ids=[240, 250]), limit=3)
    )
    print("=== Structured (active parts 240+250) ===")
    print(f"SQL hits: {len(structured['sqlite_structured'])}")
    for row in structured["merged"]:
        print(f"  #{row['monster_id']} {row['name_en']}")

    for query in QUERIES:
        print(f"\n=== Query: {query!r} ===")
        result = service.hybrid_search(query, limit=5)
        print(f"SQLite hits: {len(result['sqlite'])}")
        for row in result["sqlite"][:3]:
            print(f"  [sqlite] #{row['monster_id']} {row['name_en']}")
        print(f"Vector hits: {len(result['vector'])}")
        for row in result["vector"][:3]:
            dist = row.get("_distance", "?")
            src = row.get("_source", "vector")
            print(f"  [{src}] #{row['monster_id']} {row['name_en']} (d={dist})")
        print(f"Merged: {len(result['merged'])}")


if __name__ == "__main__":
    main()
