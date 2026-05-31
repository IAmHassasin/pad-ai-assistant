import os
from dotenv import load_dotenv

# Nạp các biến từ file .env
load_dotenv()


class Config:
    ENV = os.getenv("ENV", "development")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/pad_cards.db")
    CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "data/chroma_db")

    @classmethod
    def validate(cls):
        if not cls.GEMINI_API_KEY:
            raise ValueError("❌ THIẾU CẤU HÌNH: Hãy bổ sung GEMINI_API_KEY vào file .env!")
