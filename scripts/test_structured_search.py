"""Test structured search không cần Gemini API."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from models.search_filters import ActiveFilters, LeaderFilters, MonsterFilters, SearchFilters
from database.sqlite_client import SQLiteClient
from config import Config

# active_skill_id có part #949 (pierce absorb) — skill 956
DEMO_ACTIVE_SKILL_ID = 956


def run_case(label: str, filters: SearchFilters) -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    rows = client.search_structured(filters)
    print(f"\n=== {label} ({len(rows)} hits) ===")
    for row in rows[:5]:
        print(
            f"  #{row['monster_id']} {row['name_en']} | "
            f"L: {row.get('leader_skill_name_en')} | "
            f"A: {row.get('active_skill_name_en')}"
        )
    client.close()


def main() -> None:
    client = SQLiteClient(Config.SQLITE_DB_PATH)
    store = client.custom_effects
    store.set_skill_effect(
        "active",
        DEMO_ACTIVE_SKILL_ID,
        "void_dmg_absorb",
        turn_duration=2,
        source="test",
    )
    store.set_skill_effect("active", DEMO_ACTIVE_SKILL_ID, "void_attr_absorb", turn_duration=2, source="test")
    client.close()

    # Custom effect_keys (bảng bổ sung)
    run_case(
        "Custom active void absorbs (skill #956)",
        SearchFilters(
            active=ActiveFilters(effect_keys=["void_dmg_absorb", "void_attr_absorb"]),
            limit=5,
        ),
    )

    # Leader: Reduce Damage (32) + Extra Combos (211)
    run_case(
        "Leader Reduce Damage + Extra Combos",
        SearchFilters(
            leader=LeaderFilters(tag_ids=[32, 211]),
            limit=5,
        ),
    )

    # Active part: void att/dmg absorb (240, 250)
    run_case(
        "Active pierce void absorbs (parts)",
        SearchFilters(
            active=ActiveFilters(part_tag_ids=[240, 250]),
            limit=5,
        ),
    )

    # Fire + active Recover Bind (41)
    run_case(
        "Fire + Recover Bind",
        SearchFilters(
            monsters=MonsterFilters(attribute="Fire"),
            active=ActiveFilters(skill_tag_ids=[41]),
            limit=5,
        ),
    )


if __name__ == "__main__":
    main()
