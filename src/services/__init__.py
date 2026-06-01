from services.search_service import SearchService

__all__ = ["AIService", "SearchService"]


def __getattr__(name: str):
    if name == "AIService":
        from services.ai_service import AIService

        return AIService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
