"""Gemini phân tích câu hỏi → SearchFilters (JSON có cấu trúc)."""

import json
import re

from pydantic import ValidationError

from config import Config
from models.search_filters import (
    ActiveFilters,
    LeaderFilters,
    MonsterFilters,
    SearchFilters,
)


def _format_tag_catalog(tags: list[dict], id_key: str, label_key: str = "name_en") -> str:
    lines = [f"  {t[id_key]}: {t[label_key]}" for t in tags]
    return "\n".join(lines)


def _format_effect_catalog(effects: list[dict]) -> str:
    return "\n".join(f"  {e['key_name']}: {e['display_name']}" for e in effects)


class QueryParser:
    """Bộ dịch câu hỏi tự nhiên → điều kiện SQL (tag + chỉ số số)."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        import google.generativeai as genai

        key = api_key or Config.GEMINI_API_KEY
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model_name or Config.GEMINI_MODEL)

    def build_system_prompt(
        self,
        leader_tags: list[dict],
        active_tags: list[dict],
        leader_effects: list[dict] | None = None,
        active_effects: list[dict] | None = None,
    ) -> str:
        leader_effects = leader_effects or []
        active_effects = active_effects or []
        return f"""Bạn là bộ phân tích truy vấn game Puzzle & Dragons (PAD).
Chuyển câu hỏi người chơi thành JSON điều kiện tìm kiếm. CHỈ trả về JSON hợp lệ, không giải thích.

Quy tắc:
- DadGuide tag_id: dùng khi khớp danh mục tag (không đoán id).
- effect_keys: dùng key_name từ danh mục CUSTOM bên dưới (ưu tiên khi tag DadGuide thiếu / không chính xác).
- Nhiều điều kiện cùng loại = AND.
- Active: part_tag_ids (DadGuide chi tiết) hoặc effect_keys (custom).
- Leader: tag_ids + effect_keys + min_atk_mult, min_combos, min_bonus_damage.
- attribute: Fire, Water, Wood, Light, Dark.

DadGuide LEADER tags (leader_skill_tag_id):
{_format_tag_catalog(leader_tags, "leader_skill_tag_id")}

DadGuide ACTIVE tags (active_skill_tag_id):
{_format_tag_catalog(active_tags, "active_skill_tag_id")}

CUSTOM leader effect_keys (bổ sung — đã gán qua leader_skill_effects):
{_format_effect_catalog(leader_effects)}

CUSTOM active effect_keys:
{_format_effect_catalog(active_effects)}

Schema JSON:
{{
  "monsters": {{"name_query": null, "attribute": null, "monster_type": null, "rarity": null}},
  "leader": {{
    "tag_ids": [],
    "effect_keys": [],
    "effects": [{{"key_name": "reduce_damage", "min_value_1": null, "min_turn_duration": null}}],
    "min_atk_mult": null, "min_combos": null, "min_bonus_damage": null
  }} hoặc null,
  "active": {{
    "skill_tag_ids": [],
    "part_tag_ids": [],
    "effect_keys": [],
    "effects": []
  }} hoặc null,
  "limit": 10
}}
"""

    @staticmethod
    def _extract_json(text: str) -> dict:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    @staticmethod
    def _normalize_payload(data: dict) -> dict:
        """Gemini đôi khi trả monsters=null; chuẩn hóa để qua được pydantic."""
        normalized = dict(data)
        if normalized.get("monsters") is None:
            normalized["monsters"] = {}
        return normalized

    def parse(
        self,
        user_question: str,
        leader_tags: list[dict],
        active_tags: list[dict],
        leader_effects: list[dict] | None = None,
        active_effects: list[dict] | None = None,
    ) -> SearchFilters:
        prompt = (
            f"{self.build_system_prompt(leader_tags, active_tags, leader_effects, active_effects)}\n\n"
            f'Câu hỏi: "{user_question}"\n\nJSON:'
        )
        response = self._model.generate_content(prompt)
        raw = response.text or "{}"
        data = self._normalize_payload(self._extract_json(raw))
        return SearchFilters.model_validate(data)

    @staticmethod
    def parse_or_fallback(
        user_question: str,
        leader_tags: list[dict],
        active_tags: list[dict],
        *,
        api_key: str | None = None,
    ) -> SearchFilters:
        """Không có API key → chỉ tìm theo tên."""
        if not (api_key or Config.GEMINI_API_KEY):
            return SearchFilters(monsters=MonsterFilters(name_query=user_question.strip()))
        try:
            return QueryParser(api_key=api_key).parse(user_question, leader_tags, active_tags)
        except (ValidationError, json.JSONDecodeError, Exception):
            return SearchFilters(monsters=MonsterFilters(name_query=user_question.strip()))
