"""Quản lý Prompt và gọi Gemini 1.5 Flash API."""

import google.generativeai as genai

from config import Config


class AIService:
    def __init__(self, api_key: str | None = None, model_name: str = "gemini-1.5-flash") -> None:
        key = api_key or Config.GEMINI_API_KEY
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel(model_name)

    def ask(self, prompt: str, context: str = "") -> str:
        full_prompt = f"{context}\n\nCâu hỏi: {prompt}" if context else prompt
        response = self._model.generate_content(full_prompt)
        return response.text or ""
