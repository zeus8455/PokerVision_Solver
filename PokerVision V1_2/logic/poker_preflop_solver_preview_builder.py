"""
logic/poker_preflop_solver_preview_builder.py

PokerVision Solver V0.9 — unified preflop solver preview builder.

Builds a complete dry-run preflop solver preview from a Clear_JSON-like state:
Clear_JSON -> engine_context -> PreflopContext -> HeroDecision -> compact engine_decision_preview.

This module does not modify Clear_JSON files, does not touch live runtime, and does not click.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENGINE_REFERENCE_DIR = PROJECT_ROOT.parent / "Engine_Reference"

if str(ENGINE_REFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_REFERENCE_DIR))

from decision_types import PreflopContext  # noqa: E402
from hero_decision import solve_hero_preflop  # noqa: E402

from logic.poker_engine_decision_serializer import serialize_hero_decision_preview
from logic.poker_preflop_context_builder import build_preflop_engine_context


SCHEMA_VERSION = "poker_preflop_solver_preview_v1"


def build_preflop_context_from_engine_context(engine_context: Dict[str, Any]) -> PreflopContext:
    """Convert compact PokerVision engine_context into engine PreflopContext.

    dead_cards is intentionally not part of PokerVision engine_context JSON.
    The bridge supplies the engine's technical default here.
    """
    return PreflopContext(
        hero_hand=list(engine_context["hero_hand"]),
        hero_pos=str(engine_context["hero_pos"]),
        node_type=str(engine_context["node_type"]),
        range_owner="hero",
        opener_pos=engine_context.get("opener_pos"),
        three_bettor_pos=engine_context.get("three_bettor_pos"),
        four_bettor_pos=engine_context.get("four_bettor_pos"),
        limpers=int(engine_context.get("limpers") or 0),
        callers=int(engine_context.get("callers") or 0),
        dead_cards=[],
        action_history=list(engine_context.get("action_history") or []),
        meta={
            "source_frame_id": engine_context.get("source_frame_id"),
            "hero_hand": list(engine_context["hero_hand"]),
            "hero_original_position": engine_context.get("hero_pos"),
            "table_id": engine_context.get("table_id"),
            "street": "preflop",
            "inference_source": (engine_context.get("meta") or {}).get("inference_source"),
        },
    )


def build_preflop_solver_preview(clear_json: Dict[str, Any]) -> Dict[str, Any]:
    """Build full preflop solver preview from Clear_JSON-like state."""
    frame_id = clear_json.get("frame_id")

    engine_context = build_preflop_engine_context(clear_json)
    if engine_context.get("status") != "ok":
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "source_frame_id": frame_id,
            "engine_context": engine_context,
            "engine_decision_preview": None,
            "errors": list(engine_context.get("errors") or []),
            "warnings": list(engine_context.get("warnings") or []),
        }

    try:
        preflop_context = build_preflop_context_from_engine_context(engine_context)
        decision = solve_hero_preflop(preflop_context)
        preview = serialize_hero_decision_preview(decision)
    except Exception as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "source_frame_id": frame_id,
            "engine_context": engine_context,
            "engine_decision_preview": None,
            "errors": [{"reason": "solver_preview_failed", "message": str(exc)}],
            "warnings": [],
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "source_frame_id": frame_id,
        "engine_context": engine_context,
        "engine_decision_preview": preview,
        "errors": [],
        "warnings": [],
    }
