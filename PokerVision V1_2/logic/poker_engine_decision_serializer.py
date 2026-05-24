"""
logic/poker_engine_decision_serializer.py

PokerVision Solver V0.8 — compact HeroDecision serializer.

Converts engine HeroDecision into a lightweight JSON-safe block that can later be
attached to Clear_JSON as engine_decision_preview without heavy range combo payloads.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional


SCHEMA_VERSION = "poker_engine_decision_preview_v1"


def _safe_get(source: Dict[str, Any], key: str, default: Any = None) -> Any:
    value = source.get(key, default)
    return default if value is None else value


def _compact_preflop(preflop_payload: Any) -> Optional[Dict[str, Any]]:
    if preflop_payload is None:
        return None

    if is_dataclass(preflop_payload):
        data = asdict(preflop_payload)
    elif isinstance(preflop_payload, dict):
        data = dict(preflop_payload)
    else:
        return {"raw_repr": str(preflop_payload)}

    range_source = data.get("range_source")
    compact_range_source = None
    if isinstance(range_source, dict):
        compact_range_source = {
            "name": range_source.get("name"),
            "source_type": range_source.get("source_type"),
            "raw_expr": range_source.get("raw_expr"),
            "normalized_expr": range_source.get("normalized_expr"),
            "combo_count": len(range_source.get("weighted_combos") or []),
            "meta": dict(range_source.get("meta") or {}),
        }

    return {
        "action": data.get("action"),
        "hand_class": data.get("hand_class"),
        "actor_name": data.get("actor_name"),
        "actor_pos": data.get("actor_pos"),
        "is_mixed_action": bool(data.get("is_mixed_action")),
        "matching_actions": list(data.get("matching_actions") or []),
        "selected_range_expr": data.get("selected_range_expr"),
        "fallback_reason": data.get("fallback_reason"),
        "range_source": compact_range_source,
        "meta": dict(data.get("meta") or {}),
    }


def serialize_hero_decision_preview(decision: Any) -> Dict[str, Any]:
    """Return compact JSON-safe engine_decision_preview from HeroDecision-like object."""
    if is_dataclass(decision):
        data = asdict(decision)
    elif isinstance(decision, dict):
        data = dict(decision)
    else:
        raise TypeError(f"Unsupported decision type: {type(decision)!r}")

    debug = dict(data.get("debug") or {})
    compact_debug = {
        "node_type": debug.get("node_type"),
        "opener_pos": debug.get("opener_pos"),
        "three_bettor_pos": debug.get("three_bettor_pos"),
        "four_bettor_pos": debug.get("four_bettor_pos"),
        "limpers": debug.get("limpers"),
        "callers": debug.get("callers"),
        "range_owner": debug.get("range_owner"),
        "matching_actions": list(debug.get("matching_actions") or []),
        "fallback_reason": debug.get("fallback_reason"),
        "recommended_action": debug.get("recommended_action"),
        "engine_action": debug.get("engine_action"),
        "source_frame_id": debug.get("source_frame_id"),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "street": data.get("street"),
        "engine_action": data.get("engine_action"),
        "recommended_action": data.get("recommended_action"),
        "amount_to": data.get("amount_to"),
        "size_pct": data.get("size_pct"),
        "reason": data.get("reason"),
        "confidence": data.get("confidence"),
        "decision_id": data.get("decision_id"),
        "solver_fingerprint": data.get("solver_fingerprint"),
        "source_frame_id": data.get("source_frame_id"),
        "preflop": _compact_preflop(data.get("preflop")),
        "postflop": None if data.get("postflop") is None else {"present": True},
        "villain_sources_count": len(data.get("villain_sources") or []),
        "debug": compact_debug,
    }
