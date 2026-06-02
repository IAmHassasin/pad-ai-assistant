import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dotenv import load_dotenv

load_dotenv()
p = os.getenv("SQLITE_DB_PATH", "data/pad_cards.db")
c = sqlite3.connect(p)
c.row_factory = sqlite3.Row

print("=== leader_skill_tags (en) ===")
for r in c.execute("SELECT leader_skill_tag_id, name_en FROM leader_skill_tags ORDER BY order_idx"):
    print(r[0], r[1])

print("\n=== sample tags column on leader_skills ===")
for r in c.execute(
    "SELECT leader_skill_id, name_en, tags FROM leader_skills WHERE tags IS NOT NULL AND tags != '' LIMIT 5"
):
    print(r[0], r[1], "| tags:", repr(r[2])[:120])

print("\n=== count with tags ===")
print(c.execute("SELECT COUNT(*) FROM leader_skills WHERE tags IS NOT NULL AND tags != ''").fetchone()[0])

print("\n=== AND search example ===")
q = """
SELECT COUNT(DISTINCT m.monster_id)
FROM monsters m
JOIN leader_skills ls ON m.leader_skill_id = ls.leader_skill_id
WHERE ls.desc_en LIKE '%reduce%damage%'
  AND ls.desc_en LIKE '%combo%'
  AND ls.desc_en LIKE '%true%damage%'
"""
print("monsters matching 3 keywords:", c.execute(q).fetchone()[0])

c.close()
