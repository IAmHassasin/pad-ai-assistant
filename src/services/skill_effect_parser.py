"""Gemini parse mô tả skill → danh sách effect (nạp vào effect_types bổ sung)."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from config import Config
from database.custom_effects import DEFAULT_ACTIVE_EFFECTS, DEFAULT_LEADER_EFFECTS

Side = Literal["leader", "active"]


def _effect_catalog_lines(side: Side) -> str:
    catalog = DEFAULT_LEADER_EFFECTS if side == "leader" else DEFAULT_ACTIVE_EFFECTS
    return "\n".join(f"  - {key}: {display}" for key, display, _ in catalog)


class SkillEffectParser:
    """Một lần chạy batch: đọc desc_en → ghi leader_skill_effects / active_skill_effects."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        import google.generativeai as genai

        key = api_key or Config.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY required for skill effect parsing")
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model_name or Config.GEMINI_MODEL)

    @staticmethod
    def _extract_json(text: str) -> list[dict[str, Any]]:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        data = json.loads(cleaned)
        if isinstance(data, dict) and "effects" in data:
            return data["effects"]
        if isinstance(data, list):
            return data
        raise ValueError("Expected JSON array of effects")

    def parse_skill_description(self, side: Side, skill_id: int, description: str) -> list[dict[str, Any]]:
        prompt = f"""Bạn phân tích {side} skill Puzzle & Dragons.
Chỉ trả về JSON array, mỗi phần tử:
{{"effect_key": "snake_case", "value_1": number|null, "value_2": number|null, "turn_duration": int|null}}

Ưu tiên key có trong danh mục (có thể thêm key mới nếu bắt buộc):
{_effect_catalog_lines(side)}

Skill ID {skill_id}:
\"\"\"{description}\"\"\"
"""
        response = self._model.generate_content(prompt)
        return self._extract_json(response.text or "[]")
