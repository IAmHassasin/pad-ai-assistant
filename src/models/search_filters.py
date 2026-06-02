"""Điều kiện tìm kiếm có cấu trúc — DadGuide tags + effect_types bổ sung."""

from pydantic import BaseModel, Field

from models.effect_constraint import EffectConstraint


class MonsterFilters(BaseModel):
    name_query: str | None = None
    attribute: str | int | None = None
    monster_type: str | int | None = None
    rarity: int | None = None
    rarity_min: int | None = None
    rarity_max: int | None = None


class LeaderFilters(BaseModel):
    """Leader: DadGuide tag_ids + effect_types bổ sung (leader_effect_types)."""

    tag_ids: list[int] = Field(default_factory=list)
    effect_keys: list[str] = Field(default_factory=list)
    effects: list[EffectConstraint] = Field(default_factory=list)
    min_atk_mult: float | None = None
    min_hp_mult: float | None = None
    min_rcv_mult: float | None = None
    min_combos: int | None = None
    min_bonus_damage: int | None = None


class ActiveFilters(BaseModel):
    """Active: DadGuide tags/parts + effect_types bổ sung (active_effect_types)."""

    skill_tag_ids: list[int] = Field(default_factory=list)
    part_tag_ids: list[int] = Field(default_factory=list)
    effect_keys: list[str] = Field(default_factory=list)
    effects: list[EffectConstraint] = Field(default_factory=list)


class SearchFilters(BaseModel):
    monsters: MonsterFilters = Field(default_factory=MonsterFilters)
    leader: LeaderFilters | None = None
    active: ActiveFilters | None = None
    limit: int = 10

    def has_structured_constraints(self) -> bool:
        m = self.monsters
        if any(
            (
                m.name_query,
                m.attribute is not None,
                m.monster_type is not None,
                m.rarity is not None,
                m.rarity_min is not None,
                m.rarity_max is not None,
            )
        ):
            return True
        if self.leader is not None:
            lf = self.leader
            if (
                lf.tag_ids
                or lf.effect_keys
                or lf.effects
                or any(
                    v is not None
                    for v in (
                        lf.min_atk_mult,
                        lf.min_hp_mult,
                        lf.min_rcv_mult,
                        lf.min_combos,
                        lf.min_bonus_damage,
                    )
                )
            ):
                return True
        if self.active is not None:
            af = self.active
            if af.skill_tag_ids or af.part_tag_ids or af.effect_keys or af.effects:
                return True
        return False
