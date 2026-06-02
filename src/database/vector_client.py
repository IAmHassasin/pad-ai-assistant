from pathlib import Path

import chromadb
from chromadb.config import Settings

# Legacy single-collection index (re-index sẽ xóa)
LEGACY_COLLECTION = "pad_knowledge"


class VectorStore:
    """ChromaDB với collection riêng cho leader skill và active skill."""

    LEADER = "pad_leader_skills"
    ACTIVE = "pad_active_skills"
    SKILL_COLLECTIONS = (LEADER, ACTIVE)

    def __init__(self, persist_dir: str) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._connect()

    def _connect(self) -> None:
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )

    def _collection(self, name: str):
        if self._client is None:
            raise RuntimeError("VectorStore is closed")
        return self._client.get_or_create_collection(name=name)

    def count(self, collection: str) -> int:
        return self._collection(collection).count()

    def close(self) -> None:
        self._client = None

    def reset_all(self) -> None:
        """Xóa toàn bộ skill collections (và legacy) rồi tạo client mới."""
        import gc

        if self._client is None:
            self._connect()

        for name in (*self.SKILL_COLLECTIONS, LEGACY_COLLECTION):
            try:
                self._client.delete_collection(name)
            except Exception:
                pass

        self.close()
        gc.collect()
        self._connect()

    def add_documents(
        self,
        collection: str,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        self._collection(collection).upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )

    def query(self, collection: str, text: str, n_results: int = 5) -> dict:
        coll = self._collection(collection)
        if coll.count() == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return coll.query(query_texts=[text], n_results=n_results)


class VectorClient(VectorStore):
    """Giữ tương thích cũ — ưu tiên dùng VectorStore."""

    def __init__(self, persist_dir: str, collection_name: str = LEGACY_COLLECTION) -> None:
        super().__init__(persist_dir)
        self._legacy_collection = collection_name

    def reset_collection(self) -> None:
        self.reset_all()

    def query(self, text: str, n_results: int = 5) -> dict:  # type: ignore[override]
        return super().query(self._legacy_collection, text, n_results=n_results)

    def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        super().add_documents(self._legacy_collection, documents, ids, metadatas)

    @property
    def collection_name(self) -> str:
        return self._legacy_collection
