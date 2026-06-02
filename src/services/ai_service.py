"""Gemini 1.5 Flash — tổng hợp câu trả lời từ kết quả tìm kiếm có cấu trúc."""

import json
from typing import Any

import google.generativeai as genai

from config import Config


class AIService:
    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        key = api_key or Config.GEMINI_API_KEY
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model_name or Config.GEMINI_MODEL)

    def ask(self, prompt: str, context: str = "") -> str:
        full_prompt = f"{context}\n\nCâu hỏi: {prompt}" if context else prompt
        response = self._model.generate_content(full_prompt)
        return response.text or ""

    @staticmethod
    def format_monsters_context(rows: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        for row in rows:
            attrs = " / ".join(
                filter(None, [row.get("attribute_1"), row.get("attribute_2")])
            )
            blocks.append(
                f"- #{row['monster_id']} {row.get('name_en')} | R{row.get('rarity')} | {attrs}\n"
                f"  Leader: {row.get('leader_skill_name_en')} — {row.get('leader_skill_desc_en')}\n"
                f"  Active: {row.get('active_skill_name_en')} — {row.get('active_skill_desc_en')}"
            )
        return "\n".join(blocks)

    def answer_from_search(
        self,
        user_question: str,
        monsters: list[dict[str, Any]],
        *,
        filters_json: dict | None = None,
    ) -> str:
        if not monsters:
            return "Không tìm thấy quái thú nào khớp điều kiện trong database."

        context = self.format_monsters_context(monsters)
        filter_note = ""
        if filters_json:
            filter_note = f"\nĐiều kiện đã lọc (SQL): {json.dumps(filters_json, ensure_ascii=False)}\n"

        prompt = f"""Bạn là trợ lý Puzzle & Dragons. Trả lời bằng tiếng Việt, ngắn gọn.
Chỉ dùng thông tin trong danh sách dưới — không bịa stats hay skill.
{filter_note}
Dữ liệu từ database:
{context}

Câu hỏi người chơi: {user_question}
"""
        return self.ask(prompt)
