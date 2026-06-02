"""Tiện ích parse tag DadGuide dạng '(26),(37)'."""

import re

_TAG_PATTERN = re.compile(r"\((\d+)\)")


def parse_tag_ids(tags: str | None) -> list[int]:
    if not tags:
        return []
    return [int(m) for m in _TAG_PATTERN.findall(tags)]


def tag_like_clause(column: str, tag_id: int) -> tuple[str, str]:
    """Điều kiện SQL: cột tags chứa tag_id."""
    return (f"{column} LIKE ?", f"%({tag_id})%")
