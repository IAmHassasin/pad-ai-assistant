"""Tạo database SQLite tối thiểu để test search_monsters (DadGuide schema)."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "pad_cards.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS d_attributes (
    attribute_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS d_types (
    type_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leader_skills (
    leader_skill_id INTEGER PRIMARY KEY,
    name_en TEXT,
    desc_en TEXT
);
CREATE TABLE IF NOT EXISTS active_skills (
    active_skill_id INTEGER PRIMARY KEY,
    name_en TEXT,
    desc_en TEXT,
    cooldown_turns_max INTEGER
);
CREATE TABLE IF NOT EXISTS monsters (
    monster_id INTEGER PRIMARY KEY,
    name_en TEXT,
    name_ja TEXT,
    name_ko TEXT,
    rarity INTEGER,
    cost INTEGER,
    level INTEGER,
    hp_max INTEGER,
    atk_max INTEGER,
    rcv_max INTEGER,
    attribute_1_id INTEGER,
    attribute_2_id INTEGER,
    type_1_id INTEGER,
    type_2_id INTEGER,
    type_3_id INTEGER,
    leader_skill_id INTEGER,
    active_skill_id INTEGER,
    on_na INTEGER DEFAULT 1,
    on_jp INTEGER DEFAULT 1
);
"""

SAMPLE_DATA = {
    "d_attributes": [(1, "Fire"), (2, "Water"), (3, "Wood"), (4, "Light"), (5, "Dark")],
    "d_types": [(1, "Dragon"), (2, "God"), (3, "Healer"), (4, "Devil")],
    "leader_skills": [
        (1, "Sun God Ra", "2.5x ATK for Light Att."),
        (2, "Awoken Ra", "3x ATK for Light Att."),
        (3, "Healing Prayer", "1.5x RCV for Healer type"),
        (4, "Flame Tempo", "Reduces cooldown by 1 turn for Fire attribute monsters."),
    ],
    "active_skills": [
        (1, "Solar Beam", "Deal 300000 damage to all enemies.", 8),
        (2, "Mysterious Beam", "Deal 500000 damage to all enemies.", 7),
        (3, "Miracle of Healing", "Recover 5000 HP.", 5),
    ],
    "monsters": [
        (1001, "Ra Dragon", "ラー", "라", 7, 99, 99, 4000, 1200, 500, 4, None, 1, None, None, 1, 1, 1, 1),
        (1002, "Awoken Ra", "覚醒ラー", "각성 라", 8, 99, 99, 4500, 1500, 600, 4, None, 1, 2, None, 2, 2, 1, 1),
        (1003, "Amaterasu", "アマテラス", "아마테라스", 6, 35, 99, 3500, 900, 800, 4, None, 2, 3, None, 3, 3, 1, 1),
        (1004, "Cursed Dragon", "呪龍", "저주받은 드래곤", 5, 25, 99, 2800, 1100, 200, 5, None, 1, 4, None, None, None, 1, 1),
        (1005, "Fire Leader", "火のリーダー", "불의 리더", 6, 35, 99, 3200, 1000, 400, 1, None, 2, None, None, 4, None, 1, 1),
    ],
}


def seed() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    for table, rows in SAMPLE_DATA.items():
        conn.execute(f"DELETE FROM {table}")
        placeholders = ", ".join("?" * len(rows[0]))
        conn.executemany(
            f"INSERT INTO {table} VALUES ({placeholders})",
            rows,
        )

    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH} with {len(SAMPLE_DATA['monsters'])} sample monsters.")


if __name__ == "__main__":
    seed()
