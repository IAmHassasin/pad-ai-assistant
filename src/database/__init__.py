from database.sqlite_client import SQLiteClient

__all__ = ["SQLiteClient", "VectorClient"]


def __getattr__(name: str):
    if name == "VectorClient":
        from database.vector_client import VectorClient

        return VectorClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
