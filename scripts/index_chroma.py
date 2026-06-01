"""Export text từ SQLite (name + skills + stats) và embed vào data/chroma_db/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Config
from database.sqlite_client import SQLiteClient
from database.vector_client import VectorClient

BATCH_SIZE = 200


def index_monsters(*, reset: bool = True) -> int:
    Config.validate()
    sqlite = SQLiteClient(Config.SQLITE_DB_PATH)
    vector = VectorClient(Config.CHROMA_DB_DIR)

    monsters = sqlite.get_all_monsters()
    if not monsters:
        print("Không có monster nào trong SQLite.")
        return 0

    if reset:
        vector.reset_collection()

    documents: list[str] = []
    ids: list[str] = []
    metadatas: list[dict] = []
    indexed = 0

    for row in monsters:
        documents.append(SQLiteClient.build_embedding_document(row))
        ids.append(str(row["monster_id"]))
        metadatas.append(
            {
                "monster_id": row["monster_id"],
                "name_en": row.get("name_en") or "",
            }
        )

        if len(documents) >= BATCH_SIZE:
            vector.add_documents(documents, ids, metadatas)
            indexed += len(documents)
            documents, ids, metadatas = [], [], []
            print(f"  ... {indexed}/{len(monsters)}")

    if documents:
        vector.add_documents(documents, ids, metadatas)
        indexed += len(documents)

    sqlite.close()
    print(f"Indexed {indexed} monsters -> {Config.CHROMA_DB_DIR}")
    return indexed


if __name__ == "__main__":
    index_monsters()
