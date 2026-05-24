"""
logic/poker_clear_solver_preview_adapter.py

PokerVision Solver V1.2 — Clear_JSON-safe solver preview adapter.

Converts full solver preview result into contract-safe Clear_JSON top-level blocks:
- engine_context
- engine_decision_preview

The adapter intentionally removes keys forbidden by validate_clear_json_contract,
including errors, warnings, confidence and any heavy/debug-only internals.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


ENGINE_CONTEXT_SCHEMA_VERSION = "clear_engine_context_v1"
ENGINE_DECISION_SCHEMA_VERSION = "clear_engine_decision_preview_v1"


def _copy_optional(source: Dict[str, Any], key: str) -> Any:
    return source.get(key) if isinstance(source, dict) else None


def build_clear_safe_solver_preview_blocks(solver_preview: Dict[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    """Return Clear_JSON-safe solver blocks or None if solver preview is not OK."""
    if not isinstance(solver_preview, dict) or solver_preview.get("status") != "ok":
        return None

    engine_context = solver_preview.get("engine_context")
    decision_preview = solver_preview.get("engine_decision_preview")

    if not isinstance(engine_context, dict) or not isinstance(decision_preview, dict):
        return None

    safe_context = {
        "schema_version": ENGINE_CONTEXT_SCHEMA_VERSION,
        "street": _copy_optional(engine_context, "street"),
        "context_type": _copy_optional(engine_context, "context_type"),
        "source_frame_id": _copy_optional(engine_context, "source_frame_id"),
        "hero_hand": list(engine_context.get("hero_hand") or []),
        "hero_pos": _copy_optional(engine_context, "hero_pos"),
        "player_count": _copy_optional(engine_context, "player_count"),
        "node_type": _copy_optional(engine_context, "node_type"),
        "opener_pos": _copy_optional(engine_context, "opener_pos"),
        "three_bettor_pos": _copy_optional(engine_context, "three_bettor_pos"),
        "four_bettor_pos": _copy_optional(engine_context, "four_bettor_pos"),
        "limpers": int(engine_context.get("limpers") or 0),
        "callers": int(engine_context.get("callers") or 0),
        "action_history": list(engine_context.get("action_history") or []),
    }

    preflop = decision_preview.get("preflop") if isinstance(decision_preview.get("preflop"), dict) else {}
    range_source = preflop.get("range_source") if isinstance(preflop.get("range_source"), dict) else None

    safe_range_source = None
    if isinstance(range_source, dict):
        safe_range_source = {
            "name": range_source.get("name"),
            "source_type": range_source.get("source_type"),
            "raw_expr": range_source.get("raw_expr"),
            "normalized_expr": range_source.get("normalized_expr"),
            "combo_count": int(range_source.get("combo_count") or 0),
        }

    safe_preflop = {
        "action": preflop.get("action"),
        "hand_class": preflop.get("hand_class"),
        "actor_name": preflop.get("actor_name"),
        "actor_pos": preflop.get("actor_pos"),
        "is_mixed_action": bool(preflop.get("is_mixed_action")),
        "matching_actions": list(preflop.get("matching_actions") or []),
        "selected_range_expr": preflop.get("selected_range_expr"),
        "fallback_reason": preflop.get("fallback_reason"),
        "range_source": safe_range_source,
    }

    safe_decision = {
        "schema_version": ENGINE_DECISION_SCHEMA_VERSION,
        "street": decision_preview.get("street"),
        "engine_action": decision_preview.get("engine_action"),
        "recommended_action": decision_preview.get("recommended_action"),
        "amount_to": decision_preview.get("amount_to"),
        "size_pct": decision_preview.get("size_pct"),
        "reason": decision_preview.get("reason"),
        "decision_id": decision_preview.get("decision_id"),
        "solver_fingerprint": decision_preview.get("solver_fingerprint"),
        "source_frame_id": decision_preview.get("source_frame_id"),
        "preflop": safe_preflop,
    }

    return {
        "engine_context": safe_context,
        "engine_decision_preview": safe_decision,
    }
