"""Tạo bảng leader/active_effect_types + seed key mặc định trên pad_cards.db."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from config import Config
from database.sqlite_client import SQLiteClient


def main() -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    store = client.custom_effects
    leader = store.list_effect_types("leader")
    active = store.list_effect_types("active")
    print(f"✅ Custom effects schema ready at {Config.SQLITE_DB_PATH}")
    print(f"   leader_effect_types: {len(leader)} rows")
    print(f"   active_effect_types: {len(active)} rows")
    client.close()


if __name__ == "__main__":
    main()
