"""Embed leader skills và active skills vào hai ChromaDB collection riêng."""

import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Config
from database.sqlite_client import SQLiteClient
from database.vector_client import VectorStore

BATCH_SIZE = 200


def _index_collection(
    store: VectorStore,
    collection: str,
    monsters: list[dict],
    build_doc: Callable[[dict], str | None],
    id_prefix: str,
) -> int:
    documents: list[str] = []
    ids: list[str] = []
    metadatas: list[dict] = []
    indexed = 0
    total = len(monsters)

    for row in monsters:
        doc = build_doc(row)
        if doc is None:
            continue

        mid = row["monster_id"]
        documents.append(doc)
        ids.append(f"{id_prefix}_{mid}")
        metadatas.append(
            {
                "monster_id": mid,
                "name_en": row.get("name_en") or "",
                "skill_type": id_prefix,
            }
        )

        if len(documents) >= BATCH_SIZE:
            store.add_documents(collection, documents, ids, metadatas)
            indexed += len(documents)
            documents, ids, metadatas = [], [], []
            print(f"  [{collection}] ... {indexed}")

    if documents:
        store.add_documents(collection, documents, ids, metadatas)
        indexed += len(documents)

    print(f"  [{collection}] done: {indexed} documents")
    return indexed


def index_monsters(*, reset: bool = True) -> dict[str, int]:
    Config.validate()
    sqlite = SQLiteClient(Config.SQLITE_DB_PATH)
    store = VectorStore(Config.CHROMA_DB_DIR)

    monsters = sqlite.get_all_monsters()
    if not monsters:
        print("Không có monster nào trong SQLite.")
        return {"leader": 0, "active": 0}

    if reset:
        print("Reset Chroma collections...")
        store.reset_all()

    print(f"Indexing {len(monsters)} monsters from SQLite...")
    leader_n = _index_collection(
        store,
        VectorStore.LEADER,
        monsters,
        SQLiteClient.build_leader_embedding_document,
        "leader",
    )
    active_n = _index_collection(
        store,
        VectorStore.ACTIVE,
        monsters,
        SQLiteClient.build_active_embedding_document,
        "active",
    )

    sqlite.close()
    store.close()
    print(f"\nIndexed -> {Config.CHROMA_DB_DIR}")
    print(f"  leader: {leader_n} | active: {active_n}")
    return {"leader": leader_n, "active": active_n}


if __name__ == "__main__":
    index_monsters()
