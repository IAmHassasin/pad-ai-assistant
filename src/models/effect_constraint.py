"""Ràng buộc effect bổ sung (key_name + giá trị tùy chọn)."""

from pydantic import BaseModel, Field


class EffectConstraint(BaseModel):
    key_name: str
    min_value_1: float | None = None
    min_turn_duration: int | None = None
