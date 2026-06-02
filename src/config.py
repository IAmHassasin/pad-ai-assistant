import os
from dotenv import load_dotenv

# Nạp các biến từ file .env
load_dotenv()


class Config:
    ENV = os.getenv("ENV", "development")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    # Đổi qua .env; gemini-2.0-flash thường 404 — dùng 2.5 hoặc gemini-flash-latest
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/pad_cards.db")
    CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "data/chroma_db")

    @classmethod
    def validate(cls, *, require_gemini: bool = False) -> None:
        if require_gemini and not cls.GEMINI_API_KEY:
            raise ValueError("❌ THIẾU CẤU HÌNH: Hãy bổ sung GEMINI_API_KEY vào file .env!")
