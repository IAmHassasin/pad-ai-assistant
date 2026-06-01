"""Smoke test: SQLite (tên) vs ChromaDB (ngữ nghĩa) qua SearchService."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Config
from services.search_service import SearchService

QUERIES = [
    "Ra",  # SQLite: tên chính xác
    "leader skill reduces cooldown for fire team",  # ChromaDB: ngữ nghĩa
]


def main() -> None:
    Config.validate()
    service = SearchService()

    for query in QUERIES:
        print(f"\n=== Query: {query!r} ===")
        result = service.hybrid_search(query, limit=5)
        print(f"SQLite hits: {len(result['sqlite'])}")
        for row in result["sqlite"][:3]:
            print(f"  [sqlite] #{row['monster_id']} {row['name_en']}")
        print(f"Vector hits: {len(result['vector'])}")
        for row in result["vector"][:3]:
            dist = row.get("_distance", "?")
            print(f"  [vector] #{row['monster_id']} {row['name_en']} (d={dist})")
        print(f"Merged: {len(result['merged'])}")


if __name__ == "__main__":
    main()
