import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import Config
from database.sqlite_client import SQLiteClient

client = SQLiteClient(Config.SQLITE_DB_PATH)
results = client.search_monsters("Ra")
print(f"DB: {Config.SQLITE_DB_PATH}")
print(f"Found: {len(results)}")
for row in results[:5]:
    print(f"  #{row['monster_id']} | {row['name_en']} | R{row['rarity']}")
