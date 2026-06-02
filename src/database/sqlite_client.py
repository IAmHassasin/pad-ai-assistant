import sqlite3
from pathlib import Path
from typing import Any

from models.effect_constraint import EffectConstraint
from models.search_filters import ActiveFilters, LeaderFilters, MonsterFilters, SearchFilters
from database.custom_effects import CustomEffectsStore
from database.tag_utils import tag_like_clause


class SQLiteClient:
    """Quản lý kết nối và truy vấn SQLite (DadGuide monsters schema)."""

    _MONSTER_SELECT = """
        SELECT
            m.monster_id,
            m.name_en,
            m.name_ja,
            m.name_ko,
            m.rarity,
            m.cost,
            m.level,
            m.hp_max,
            m.atk_max,
            m.rcv_max,
            m.attribute_1_id,
            a1.name AS attribute_1,
            m.attribute_2_id,
            a2.name AS attribute_2,
            m.type_1_id,
            t1.name AS type_1,
            m.type_2_id,
            t2.name AS type_2,
            m.type_3_id,
            t3.name AS type_3,
            m.leader_skill_id,
            ls.name_en AS leader_skill_name_en,
            ls.desc_en AS leader_skill_desc_en,
            m.active_skill_id,
            ac.name_en AS active_skill_name_en,
            ac.desc_en AS active_skill_desc_en,
            ac.cooldown_turns_max AS active_skill_cooldown,
            m.on_na,
            m.on_jp
    """

    _FROM_MONSTERS = """
        FROM monsters m
        LEFT JOIN d_attributes a1 ON m.attribute_1_id = a1.attribute_id
        LEFT JOIN d_attributes a2 ON m.attribute_2_id = a2.attribute_id
        LEFT JOIN d_types t1 ON m.type_1_id = t1.type_id
        LEFT JOIN d_types t2 ON m.type_2_id = t2.type_id
        LEFT JOIN d_types t3 ON m.type_3_id = t3.type_id
        LEFT JOIN leader_skills ls ON m.leader_skill_id = ls.leader_skill_id
        LEFT JOIN active_skills ac ON m.active_skill_id = ac.active_skill_id
    """

    def __init__(self, db_path: str, *, auto_migrate_custom_effects: bool = True) -> None:
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None
        self._auto_migrate_custom_effects = auto_migrate_custom_effects
        self._custom_effects: CustomEffectsStore | None = None

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.db_path}")
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            if self._auto_migrate_custom_effects:
                self.custom_effects.ensure_schema(seed_defaults=True)
        return self._connection

    @property
    def custom_effects(self) -> CustomEffectsStore:
        conn = self.connect()
        if self._custom_effects is None:
            self._custom_effects = CustomEffectsStore(conn)
        return self._custom_effects

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    @staticmethod
    def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

    def _fetch_monsters(self, where_sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        conn = self.connect()
        sql = f"{self._MONSTER_SELECT} {self._FROM_MONSTERS} WHERE {where_sql}"
        cursor = conn.execute(sql, params)
        return self._rows_to_dicts(cursor.fetchall())

    def _resolve_attribute_id(self, value: str | int) -> int | None:
        if isinstance(value, int):
            return value
        conn = self.connect()
        row = conn.execute(
            "SELECT attribute_id FROM d_attributes WHERE LOWER(name) = LOWER(?)",
            (value.strip(),),
        ).fetchone()
        return int(row["attribute_id"]) if row else None

    def _resolve_type_id(self, value: str | int) -> int | None:
        if isinstance(value, int):
            return value
        conn = self.connect()
        row = conn.execute(
            "SELECT type_id FROM d_types WHERE LOWER(name) = LOWER(?)",
            (value.strip(),),
        ).fetchone()
        return int(row["type_id"]) if row else None

    def get_by_id(self, monster_id: int) -> dict[str, Any] | None:
        """Lấy một monster theo monster_id."""
        rows = self._fetch_monsters("m.monster_id = ?", (monster_id,))
        return rows[0] if rows else None

    def search_by_name(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Tìm monster theo tên (LIKE trên name_en / name_ja / name_ko)."""
        pattern = f"%{query.strip()}%"
        return self._fetch_monsters(
            """
            (m.name_en LIKE ? OR m.name_ja LIKE ? OR m.name_ko LIKE ?)
            ORDER BY
                CASE
                    WHEN LOWER(m.name_en) = LOWER(?) THEN 0
                    WHEN m.name_en LIKE ? THEN 1
                    ELSE 2
                END,
                m.rarity DESC,
                m.name_en
            LIMIT ?
            """,
            (pattern, pattern, pattern, query.strip(), f"{query.strip()}%", limit),
        )

    def search_by_filters(
        self,
        *,
        attribute: str | int | None = None,
        monster_type: str | int | None = None,
        rarity: int | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Lọc theo attribute / type / rarity (cột trên bảng monsters)."""
        clauses: list[str] = []
        params: list[Any] = []

        if attribute is not None:
            attr_id = self._resolve_attribute_id(attribute)
            if attr_id is None:
                return []
            clauses.append(
                "(m.attribute_1_id = ? OR m.attribute_2_id = ? OR m.attribute_3_id = ?)"
            )
            params.extend([attr_id, attr_id, attr_id])

        if monster_type is not None:
            type_id = self._resolve_type_id(monster_type)
            if type_id is None:
                return []
            clauses.append("(m.type_1_id = ? OR m.type_2_id = ? OR m.type_3_id = ?)")
            params.extend([type_id, type_id, type_id])

        if rarity is not None:
            clauses.append("m.rarity = ?")
            params.append(rarity)

        if not clauses:
            return []

        where_sql = " AND ".join(clauses) + " ORDER BY m.name_en LIMIT ?"
        params.append(limit)
        return self._fetch_monsters(where_sql, tuple(params))

    def search_monsters(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Alias giữ tương thích với SearchService."""
        return self.search_by_name(query, limit=limit)

    def list_leader_tags(self) -> list[dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT leader_skill_tag_id, name_en FROM leader_skill_tags ORDER BY order_idx"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_active_tags(self) -> list[dict[str, Any]]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT active_skill_tag_id, name_en FROM active_skill_tags ORDER BY order_idx"
        ).fetchall()
        return [dict(r) for r in rows]

    def list_leader_effect_types(self) -> list[dict[str, Any]]:
        return self.custom_effects.list_effect_types("leader")

    def list_active_effect_types(self) -> list[dict[str, Any]]:
        return self.custom_effects.list_effect_types("active")

    @staticmethod
    def _leader_custom_effect_sql(
        constraint: EffectConstraint,
    ) -> tuple[str, list[Any]]:
        params: list[Any] = [constraint.key_name.strip()]
        value_sql = ""
        if constraint.min_value_1 is not None:
            value_sql += " AND lse.value_1 >= ?"
            params.append(constraint.min_value_1)
        if constraint.min_turn_duration is not None:
            value_sql += " AND lse.turn_duration >= ?"
            params.append(constraint.min_turn_duration)
        sql = f"""
            EXISTS (
                SELECT 1
                FROM leader_skill_effects lse
                JOIN leader_effect_types let ON lse.effect_type_id = let.effect_type_id
                WHERE lse.leader_skill_id = m.leader_skill_id
                  AND let.key_name = ?
                  {value_sql}
            )
        """.strip()
        return sql, params

    @staticmethod
    def _active_custom_effect_sql(
        constraint: EffectConstraint,
    ) -> tuple[str, list[Any]]:
        params: list[Any] = [constraint.key_name.strip()]
        value_sql = ""
        if constraint.min_value_1 is not None:
            value_sql += " AND ase.value_1 >= ?"
            params.append(constraint.min_value_1)
        if constraint.min_turn_duration is not None:
            value_sql += " AND ase.turn_duration >= ?"
            params.append(constraint.min_turn_duration)
        sql = f"""
            EXISTS (
                SELECT 1
                FROM active_skill_effects ase
                JOIN active_effect_types aet ON ase.effect_type_id = aet.effect_type_id
                WHERE ase.active_skill_id = m.active_skill_id
                  AND aet.key_name = ?
                  {value_sql}
            )
        """.strip()
        return sql, params

    @staticmethod
    def _merge_effect_constraints(
        effect_keys: list[str],
        effects: list[EffectConstraint],
    ) -> list[EffectConstraint]:
        seen: set[str] = set()
        merged: list[EffectConstraint] = []
        for key in effect_keys:
            k = key.strip()
            if k and k not in seen:
                seen.add(k)
                merged.append(EffectConstraint(key_name=k))
        for eff in effects:
            k = eff.key_name.strip()
            if k and k not in seen:
                seen.add(k)
                merged.append(eff)
            elif k in seen and (eff.min_value_1 is not None or eff.min_turn_duration is not None):
                merged = [e if e.key_name != k else eff for e in merged]
        return merged

    def _append_monster_filters(
        self,
        mf: MonsterFilters,
        joins: list[str],
        clauses: list[str],
        params: list[Any],
    ) -> None:
        if mf.name_query:
            pattern = f"%{mf.name_query.strip()}%"
            clauses.append(
                "(m.name_en LIKE ? OR m.name_ja LIKE ? OR m.name_ko LIKE ?)"
            )
            params.extend([pattern, pattern, pattern])

        if mf.attribute is not None:
            attr_id = self._resolve_attribute_id(mf.attribute)
            if attr_id is None:
                clauses.append("1=0")
                return
            clauses.append(
                "(m.attribute_1_id = ? OR m.attribute_2_id = ? OR m.attribute_3_id = ?)"
            )
            params.extend([attr_id, attr_id, attr_id])

        if mf.monster_type is not None:
            type_id = self._resolve_type_id(mf.monster_type)
            if type_id is None:
                clauses.append("1=0")
                return
            clauses.append("(m.type_1_id = ? OR m.type_2_id = ? OR m.type_3_id = ?)")
            params.extend([type_id, type_id, type_id])

        if mf.rarity is not None:
            clauses.append("m.rarity = ?")
            params.append(mf.rarity)
        if mf.rarity_min is not None:
            clauses.append("m.rarity >= ?")
            params.append(mf.rarity_min)
        if mf.rarity_max is not None:
            clauses.append("m.rarity <= ?")
            params.append(mf.rarity_max)

    def _append_leader_filters(
        self,
        lf: LeaderFilters,
        joins: list[str],
        clauses: list[str],
        params: list[Any],
    ) -> None:
        # ls đã có trong _FROM_MONSTERS (LEFT JOIN leader_skills ls)
        for tag_id in lf.tag_ids:
            sql, val = tag_like_clause("ls.tags", tag_id)
            clauses.append(sql)
            params.append(val)

        if lf.min_atk_mult is not None:
            clauses.append("ls.max_atk >= ?")
            params.append(lf.min_atk_mult)
        if lf.min_hp_mult is not None:
            clauses.append("ls.max_hp >= ?")
            params.append(lf.min_hp_mult)
        if lf.min_rcv_mult is not None:
            clauses.append("ls.max_rcv >= ?")
            params.append(lf.min_rcv_mult)
        if lf.min_combos is not None:
            clauses.append("ls.max_combos >= ?")
            params.append(lf.min_combos)
        if lf.min_bonus_damage is not None:
            clauses.append("ls.bonus_damage >= ?")
            params.append(lf.min_bonus_damage)

        for constraint in self._merge_effect_constraints(lf.effect_keys, lf.effects):
            sql, eff_params = self._leader_custom_effect_sql(constraint)
            clauses.append(sql)
            params.extend(eff_params)

    def _active_part_exists_sql(self, tag_id: int, alias: str) -> tuple[str, list[Any]]:
        """EXISTS: monster có active part mang tag_id."""
        return (
            f"""
            EXISTS (
                SELECT 1
                FROM active_skills ac_p
                JOIN active_skills_subskills ass ON ac_p.active_skill_id = ass.active_skill_id
                JOIN active_subskills_parts asp ON ass.active_subskill_id = asp.active_subskill_id
                JOIN active_parts ap ON asp.active_part_id = ap.active_part_id
                WHERE ac_p.active_skill_id = m.active_skill_id
                  AND ap.tags LIKE ?
            )
            """.strip(),
            [f"%({tag_id})%"],
        )

    def _append_active_filters(
        self,
        af: ActiveFilters,
        joins: list[str],
        clauses: list[str],
        params: list[Any],
    ) -> None:
        # ac đã có trong _FROM_MONSTERS (LEFT JOIN active_skills ac)
        if af.skill_tag_ids:
            for tag_id in af.skill_tag_ids:
                sql, val = tag_like_clause("ac.tags", tag_id)
                clauses.append(sql)
                params.append(val)

        for tag_id in af.part_tag_ids:
            sql, part_params = self._active_part_exists_sql(tag_id, "ap")
            clauses.append(sql)
            params.extend(part_params)

        for constraint in self._merge_effect_constraints(af.effect_keys, af.effects):
            sql, eff_params = self._active_custom_effect_sql(constraint)
            clauses.append(sql)
            params.extend(eff_params)

    def search_structured(self, filters: SearchFilters) -> list[dict[str, Any]]:
        """
        Tìm monster theo DadGuide tags/parts + leader_effect_types / active_effect_types bổ sung.
        """
        joins: list[str] = []
        clauses: list[str] = ["1=1"]
        params: list[Any] = []

        self._append_monster_filters(filters.monsters, joins, clauses, params)
        if filters.leader is not None:
            self._append_leader_filters(filters.leader, joins, clauses, params)
        if filters.active is not None:
            self._append_active_filters(filters.active, joins, clauses, params)

        join_sql = " ".join(joins)
        where_sql = " AND ".join(clauses)
        limit = max(1, min(filters.limit, 100))

        conn = self.connect()
        sql = f"""
            SELECT DISTINCT m.monster_id
            {self._FROM_MONSTERS}
            {join_sql}
            WHERE {where_sql}
            ORDER BY m.rarity DESC, m.name_en
            LIMIT ?
        """
        id_rows = conn.execute(sql, (*params, limit)).fetchall()
        results: list[dict[str, Any]] = []
        for r in id_rows:
            mid = r["monster_id"]
            if mid is None:
                continue
            row = self.get_by_id(int(mid))
            if row is not None:
                results.append(row)
        return results

    def get_all_monsters(self) -> list[dict[str, Any]]:
        """Lấy toàn bộ monster để export sang ChromaDB."""
        return self._fetch_monsters("1=1 ORDER BY m.monster_id", ())

    @staticmethod
    def _monster_label(row: dict[str, Any]) -> str:
        return " / ".join(filter(None, [row.get("name_en"), row.get("name_ja"), row.get("name_ko")]))

    @staticmethod
    def build_leader_embedding_document(row: dict[str, Any]) -> str | None:
        """Văn bản embed chỉ leader skill (+ tên monster để liên kết)."""
        leader_name = row.get("leader_skill_name_en")
        leader_desc = row.get("leader_skill_desc_en")
        if not leader_name and not leader_desc:
            return None

        names = SQLiteClient._monster_label(row)
        attrs = " / ".join(filter(None, [row.get("attribute_1"), row.get("attribute_2")]))
        types = " / ".join(filter(None, [row.get("type_1"), row.get("type_2"), row.get("type_3")]))

        parts = [f"Monster: {names}", f"Rarity: {row.get('rarity')}"]
        if attrs:
            parts.append(f"Attributes: {attrs}")
        if types:
            parts.append(f"Types: {types}")
        parts.append(f"Leader Skill: {leader_name or '—'} — {leader_desc or '—'}")
        return "\n".join(parts)

    @staticmethod
    def build_active_embedding_document(row: dict[str, Any]) -> str | None:
        """Văn bản embed chỉ active skill (+ tên monster để liên kết)."""
        active_name = row.get("active_skill_name_en")
        active_desc = row.get("active_skill_desc_en")
        if not active_name and not active_desc:
            return None

        names = SQLiteClient._monster_label(row)
        cooldown = row.get("active_skill_cooldown")
        cd = f" ({cooldown} turns)" if cooldown is not None else ""

        parts = [
            f"Monster: {names}",
            f"Rarity: {row.get('rarity')}",
            f"Active Skill: {active_name or '—'}{cd} — {active_desc or '—'}",
        ]
        return "\n".join(parts)

    @staticmethod
    def build_embedding_document(row: dict[str, Any]) -> str:
        """Ghép leader + active (legacy / debug, không dùng cho Chroma index)."""
        parts = [
            SQLiteClient.build_leader_embedding_document(row),
            SQLiteClient.build_active_embedding_document(row),
        ]
        docs = [p for p in parts if p]
        if docs:
            return "\n\n".join(docs)
        return f"Monster: {SQLiteClient._monster_label(row)}\nRarity: {row.get('rarity')}"
