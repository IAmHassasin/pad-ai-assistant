from pathlib import Path

import chromadb
from chromadb.config import Settings


class VectorClient:
    """Quản lý nhúng (embedding) và truy vấn ChromaDB."""

    def __init__(self, persist_dir: str, collection_name: str = "pad_knowledge") -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(name=collection_name)

    @property
    def collection_name(self) -> str:
        return self._collection.name

    def count(self) -> int:
        return self._collection.count()

    def reset_collection(self) -> None:
        """Xóa và tạo lại collection (dùng khi re-index)."""
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(name=name)

    def query(self, text: str, n_results: int = 5) -> dict:
        """Truy vấn vector theo văn bản (embedding do Chroma xử lý mặc định)."""
        if self.count() == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]]}
        return self._collection.query(query_texts=[text], n_results=n_results)

    def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        self._collection.upsert(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )
