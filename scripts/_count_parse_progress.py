import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")
p = os.getenv("SQLITE_DB_PATH", "data/pad_cards.db")
c = sqlite3.connect(p)


def stats(side: str) -> dict:
    st = f"{side}_skills"
    ef = f"{side}_skill_effects"
    idc = f"{side}_skill_id"
    total = c.execute(
        f"SELECT COUNT(*) FROM {st} WHERE desc_en IS NOT NULL AND desc_en != ''"
    ).fetchone()[0]
    done = c.execute(
        f"""
        SELECT COUNT(DISTINCT s.{idc}) FROM {st} s
        WHERE s.desc_en IS NOT NULL AND s.desc_en != ''
          AND EXISTS (SELECT 1 FROM {ef} e WHERE e.{idc} = s.{idc})
        """
    ).fetchone()[0]
    gemini = c.execute(
        f"SELECT COUNT(DISTINCT {idc}) FROM {ef} WHERE source = 'gemini'"
    ).fetchone()[0]
    return {
        "total": total,
        "parsed": done,
        "remaining": total - done,
        "gemini_skills": gemini,
    }


for side in ("active", "leader"):
    s = stats(side)
    print(f"\n{side.upper()}:")
    print(f"  Có mô tả EN:     {s['total']:,}")
    print(f"  Đã parse:       {s['parsed']:,}")
    print(f"  Còn lại:        {s['remaining']:,}")
    print(f"  Nguồn gemini:   {s['gemini_skills']:,} skill")

a = stats("active")
if a["parsed"] > 0:
    cost_per_50 = 4000
    est_total_vnd = cost_per_50 * (a["remaining"] / 50)
    est_all_vnd = cost_per_50 * (a["total"] / 50)
    print(f"\nƯớc tính (nếu ~4.000 VNĐ / 50 skill):")
    print(f"  Phần còn lại active: ~{est_total_vnd:,.0f} VNĐ")
    print(f"  Toàn bộ active:      ~{est_all_vnd:,.0f} VNĐ")

c.close()
