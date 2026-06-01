import sqlite3
from pathlib import Path
from typing import Any


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

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {self.db_path}")
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

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

    def get_all_monsters(self) -> list[dict[str, Any]]:
        """Lấy toàn bộ monster để export sang ChromaDB."""
        return self._fetch_monsters("1=1 ORDER BY m.monster_id", ())

    @staticmethod
    def build_embedding_document(row: dict[str, Any]) -> str:
        """Ghép name + skills + stats thành văn bản để embed."""
        names = " / ".join(filter(None, [row.get("name_en"), row.get("name_ja"), row.get("name_ko")]))
        attrs = " / ".join(filter(None, [row.get("attribute_1"), row.get("attribute_2")]))
        types = " / ".join(filter(None, [row.get("type_1"), row.get("type_2"), row.get("type_3")]))

        parts = [
            f"Name: {names}",
            f"Rarity: {row.get('rarity')} | Cost: {row.get('cost')}",
        ]
        if attrs:
            parts.append(f"Attributes: {attrs}")
        if types:
            parts.append(f"Types: {types}")

        leader_name = row.get("leader_skill_name_en")
        leader_desc = row.get("leader_skill_desc_en")
        if leader_name or leader_desc:
            parts.append(f"Leader Skill: {leader_name or '—'} — {leader_desc or '—'}")

        active_name = row.get("active_skill_name_en")
        active_desc = row.get("active_skill_desc_en")
        cooldown = row.get("active_skill_cooldown")
        if active_name or active_desc:
            cd = f" ({cooldown} turns)" if cooldown is not None else ""
            parts.append(f"Active Skill: {active_name or '—'}{cd} — {active_desc or '—'}")

        parts.append(
            f"Stats: HP {row.get('hp_max')} / ATK {row.get('atk_max')} / RCV {row.get('rcv_max')}"
        )
        return "\n".join(parts)
