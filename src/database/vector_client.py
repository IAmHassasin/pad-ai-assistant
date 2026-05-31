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

    def query(self, text: str, n_results: int = 5) -> dict:
        """Truy vấn vector theo văn bản (embedding do Chroma xử lý mặc định)."""
        return self._collection.query(query_texts=[text], n_results=n_results)

    def add_documents(
        self,
        documents: list[str],
        ids: list[str],
        metadatas: list[dict] | None = None,
    ) -> None:
        self._collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )
