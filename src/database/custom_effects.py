"""Bảng effect_types bổ sung — mở rộng tag DadGuide khi data chưa đủ."""

from __future__ import annotations

import sqlite3
from typing import Any, Literal

Side = Literal["leader", "active"]

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS leader_effect_types (
    effect_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS active_effect_types (
    effect_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS leader_skill_effects (
    leader_skill_id INTEGER NOT NULL,
    effect_type_id INTEGER NOT NULL,
    value_1 REAL,
    value_2 REAL,
    turn_duration INTEGER,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    PRIMARY KEY (leader_skill_id, effect_type_id),
    FOREIGN KEY (effect_type_id) REFERENCES leader_effect_types(effect_type_id)
);

CREATE TABLE IF NOT EXISTS active_skill_effects (
    active_skill_id INTEGER NOT NULL,
    effect_type_id INTEGER NOT NULL,
    value_1 REAL,
    value_2 REAL,
    turn_duration INTEGER,
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    PRIMARY KEY (active_skill_id, effect_type_id),
    FOREIGN KEY (effect_type_id) REFERENCES active_effect_types(effect_type_id)
);

CREATE INDEX IF NOT EXISTS idx_leader_skill_effects_skill
    ON leader_skill_effects (leader_skill_id);
CREATE INDEX IF NOT EXISTS idx_active_skill_effects_skill
    ON active_skill_effects (active_skill_id);
"""

DEFAULT_LEADER_EFFECTS: list[tuple[str, str, str]] = [
    ("enhanced_atk", "Enhanced ATK", "Nhân ATK cho điều kiện hệ/type"),
    ("enhanced_hp", "Enhanced HP", "Nhân HP"),
    ("enhanced_rcv", "Enhanced RCV", "Nhân RCV"),
    ("reduce_damage", "Reduce Damage", "Giảm sát thương nhận (%)"),
    ("add_combo", "Add Combo", "Thêm combo cố định"),
    ("bonus_damage", "Bonus/True Damage", "Sát thương cố định khi match điều kiện"),
    ("auto_heal", "Auto Heal", "Hồi HP mỗi lượt"),
    ("extend_time", "Extend Time", "Thêm thời gian di chuyển orb"),
    ("no_skyfall", "No Skyfall", "Không rơi orb ngẫu nhiên"),
]

DEFAULT_ACTIVE_EFFECTS: list[tuple[str, str, str]] = [
    ("pierce_void_dmg", "Pierce Void Damage", "Bypass / void damage void shield"),
    ("void_dmg_absorb", "Void Damage Absorb", "Phá hút sát thương (damage absorption)"),
    ("void_attr_absorb", "Void Attribute Absorb", "Phá hút thuộc tính"),
    ("rcv_buff", "RCV Buff", "Nhân RCV tạm thời"),
    ("atk_buff", "ATK Buff", "Nhân ATK tạm thời"),
    ("delay", "Delay", "Trì hoãn lượt địch"),
    ("recover_bind", "Recover Bind", "Gỡ bind / awoken bind"),
    ("board_change", "Board Change", "Đổi bàn orb"),
    ("spawn_orbs", "Spawn Orbs", "Tạo orb"),
    ("heal", "Heal", "Hồi HP"),
    ("reduce_damage", "Reduce Damage", "Giảm sát thương nhận"),
    ("gravity", "Gravity", "Gravity"),
    ("void_damage", "Void Damage", "Void sát thương hệ"),
]


class CustomEffectsStore:
    """CRUD cho effect_types và gán effect vào skill."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def ensure_schema(self, *, seed_defaults: bool = True) -> None:
        self._conn.executescript(SCHEMA_SQL)
        if seed_defaults:
            self._seed_defaults()
        self._conn.commit()

    def _seed_defaults(self) -> None:
        for key, display, desc in DEFAULT_LEADER_EFFECTS:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO leader_effect_types (key_name, display_name, description)
                VALUES (?, ?, ?)
                """,
                (key, display, desc),
            )
        for key, display, desc in DEFAULT_ACTIVE_EFFECTS:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO active_effect_types (key_name, display_name, description)
                VALUES (?, ?, ?)
                """,
                (key, display, desc),
            )

    def list_effect_types(self, side: Side) -> list[dict[str, Any]]:
        table = f"{side}_effect_types"
        rows = self._conn.execute(
            f"SELECT effect_type_id, key_name, display_name, description "
            f"FROM {table} ORDER BY key_name"
        ).fetchall()
        return [dict(r) for r in rows]

    def upsert_effect_type(
        self,
        side: Side,
        key_name: str,
        display_name: str,
        description: str | None = None,
    ) -> int:
        table = f"{side}_effect_types"
        self._conn.execute(
            f"""
            INSERT INTO {table} (key_name, display_name, description)
            VALUES (?, ?, ?)
            ON CONFLICT(key_name) DO UPDATE SET
                display_name = excluded.display_name,
                description = COALESCE(excluded.description, {table}.description)
            """,
            (key_name.strip(), display_name.strip(), description),
        )
        row = self._conn.execute(
            f"SELECT effect_type_id FROM {table} WHERE key_name = ?",
            (key_name.strip(),),
        ).fetchone()
        self._conn.commit()
        return int(row["effect_type_id"])

    def resolve_effect_type_id(self, side: Side, key_name: str) -> int | None:
        table = f"{side}_effect_types"
        row = self._conn.execute(
            f"SELECT effect_type_id FROM {table} WHERE key_name = ?",
            (key_name.strip(),),
        ).fetchone()
        return int(row["effect_type_id"]) if row else None

    def set_skill_effect(
        self,
        side: Side,
        skill_id: int,
        key_name: str,
        *,
        value_1: float | None = None,
        value_2: float | None = None,
        turn_duration: int | None = None,
        source: str = "manual",
        notes: str | None = None,
        create_type_if_missing: bool = True,
    ) -> None:
        effect_id = self.resolve_effect_type_id(side, key_name)
        if effect_id is None:
            if not create_type_if_missing:
                raise ValueError(f"Unknown {side} effect key: {key_name}")
            effect_id = self.upsert_effect_type(side, key_name, key_name.replace("_", " ").title())

        skill_table = f"{side}_skill_effects"
        skill_col = f"{side}_skill_id"
        self._conn.execute(
            f"""
            INSERT INTO {skill_table}
                ({skill_col}, effect_type_id, value_1, value_2, turn_duration, source, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT({skill_col}, effect_type_id) DO UPDATE SET
                value_1 = excluded.value_1,
                value_2 = excluded.value_2,
                turn_duration = excluded.turn_duration,
                source = excluded.source,
                notes = COALESCE(excluded.notes, {skill_table}.notes)
            """,
            (skill_id, effect_id, value_1, value_2, turn_duration, source, notes),
        )
        self._conn.commit()

    def list_skill_effects(self, side: Side, skill_id: int) -> list[dict[str, Any]]:
        types = f"{side}_effect_types"
        effects = f"{side}_skill_effects"
        col = f"{side}_skill_id"
        rows = self._conn.execute(
            f"""
            SELECT et.key_name, et.display_name, e.value_1, e.value_2, e.turn_duration, e.source
            FROM {effects} e
            JOIN {types} et ON e.effect_type_id = et.effect_type_id
            WHERE e.{col} = ?
            ORDER BY et.key_name
            """,
            (skill_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def skills_missing_effects(
        self,
        side: Side,
        limit: int = 100,
        *,
        order: Literal["asc", "desc"] = "desc",
    ) -> list[dict[str, Any]]:
        """Skill chưa có dòng nào trong bảng effects bổ sung."""
        if order not in ("asc", "desc"):
            raise ValueError("order must be 'asc' or 'desc'")
        skill_table = f"{side}_skills"
        id_col = f"{side}_skill_id"
        effects = f"{side}_skill_effects"
        rows = self._conn.execute(
            f"""
            SELECT s.{id_col}, s.name_en, s.desc_en
            FROM {skill_table} s
            WHERE s.desc_en IS NOT NULL AND s.desc_en != ''
              AND NOT EXISTS (
                  SELECT 1 FROM {effects} e WHERE e.{id_col} = s.{id_col}
              )
            ORDER BY s.{id_col} {order.upper()}
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
