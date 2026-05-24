from __future__ import annotations

"""Shared decision-layer contracts for the NLHE project.

This file intentionally contains only lightweight data structures that can be
passed between:
- preflop_advisor.py
- postflop_advisor.py
- hero_decision.py
- later main.py / launcher files

Goal:
- stop passing loose dicts / raw range strings between layers
- make the integration explicit and stable
- keep engine.py / engine_core.py / equity.py untouched
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

CardLike = int | str
Combo = tuple[int, int]
WeightedCombo = tuple[Combo, float]


@dataclass(slots=True, frozen=True)
class RangeSource:
    """Official range container passed between decision layers.

    raw_expr:
        Original human-readable range expression when it exists.
    normalized_expr:
        Canonical / cleaned text form that is safe for downstream parsers.
    weighted_combos:
        Expanded combo list with weights, ready for equity / filtering layers.
    meta:
        Free-form details describing how this range was produced.
    """

    name: str
    source_type: str
    raw_expr: Optional[str] = None
    normalized_expr: Optional[str] = None
    weighted_combos: list[WeightedCombo] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)

    @property
    def combo_count(self) -> int:
        return len(self.weighted_combos)

    @property
    def total_weight(self) -> float:
        return float(sum(weight for _, weight in self.weighted_combos))

    @property
    def is_empty(self) -> bool:
        return not self.weighted_combos


@dataclass(slots=True)
class PreflopContext:
    """Structured input for preflop decision logic."""

    hero_hand: list[str]
    hero_pos: str
    node_type: str
    range_owner: str = "hero"
    opener_pos: Optional[str] = None
    three_bettor_pos: Optional[str] = None
    four_bettor_pos: Optional[str] = None
    limpers: int = 0
    callers: int = 0
    dead_cards: list[str] = field(default_factory=list)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PostflopContext:
    """Structured input for postflop filtering and HERO decisions."""

    hero_hand: list[str]
    board: list[str]
    pot_before_hero: float
    to_call: float = 0.0
    effective_stack: Optional[float] = None
    hero_position: Optional[str] = None
    villain_positions: list[str] = field(default_factory=list)
    line_context: dict[str, object] = field(default_factory=dict)
    dead_cards: list[str] = field(default_factory=list)
    street: Optional[str] = None
    player_count: Optional[int] = None
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PreflopDecision:
    """Decision result returned by the preflop layer."""

    action: str
    hand_class: str
    actor_name: str = "Hero"
    actor_pos: Optional[str] = None
    is_mixed_action: bool = False
    matching_actions: list[str] = field(default_factory=list)
    selected_range_expr: Optional[str] = None
    action_map: dict[str, str] = field(default_factory=dict)
    range_source: Optional[RangeSource] = None
    amount_to: Optional[float] = None
    size_pct: Optional[float] = None
    fallback_reason: Optional[str] = None
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class PostflopDecision:
    """Decision or filtered-range result returned by the postflop layer."""

    action: str
    street: str
    actor_name: str = "Hero"
    actor_pos: Optional[str] = None
    size_pct: Optional[float] = None
    amount_to: Optional[float] = None
    hero_equity: Optional[float] = None
    realized_equity: Optional[float] = None
    range_before: Optional[RangeSource] = None
    range_after: Optional[RangeSource] = None
    villain_sources: list[RangeSource] = field(default_factory=list)
    report: dict[str, object] = field(default_factory=dict)
    fallback_reason: Optional[str] = None
    meta: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class HeroDecision:
    """Unified action payload that launcher files can pass into the engine.

    engine_action:
        Canonical engine action name: fold / check / call / raise / bet / all_in.
    amount_to:
        Final target amount for raise/bet actions when relevant.
    size_pct:
        Human / strategy-side sizing in pot-% form when relevant.
    """

    street: str
    engine_action: str
    amount_to: Optional[float] = None
    size_pct: Optional[float] = None
    actor_name: str = "Hero"
    actor_pos: Optional[str] = None
    reason: str = ""
    confidence: Optional[float] = None
    source: str = "hero_decision"
    solver_fingerprint: Optional[str] = None
    decision_id: Optional[str] = None
    source_frame_id: Optional[str] = None
    preflop: Optional[PreflopDecision] = None
    postflop: Optional[PostflopDecision] = None
    villain_sources: list[RangeSource] = field(default_factory=list)
    debug: dict[str, object] = field(default_factory=dict)


__all__ = [
    "CardLike",
    "Combo",
    "WeightedCombo",
    "RangeSource",
    "PreflopContext",
    "PostflopContext",
    "PreflopDecision",
    "PostflopDecision",
    "HeroDecision",
]
