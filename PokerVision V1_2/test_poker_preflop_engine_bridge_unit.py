"""
test_poker_preflop_engine_bridge_unit.py

PokerVision Solver V0.6 — dry-run bridge test:
Clear_JSON fixture -> engine_context -> PreflopContext -> solve_hero_preflop -> HeroDecision.

This test does not touch live runtime and does not click anything.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parent
ENGINE_REFERENCE_DIR = PROJECT_ROOT.parent / "Engine_Reference"
FIXTURE_ROOT = PROJECT_ROOT / "test_fixtures" / "solver_context" / "preflop_clear_json"

if str(ENGINE_REFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_REFERENCE_DIR))

from decision_types import HeroDecision, PreflopContext  # noqa: E402
from hero_decision import solve_hero_preflop  # noqa: E402
from logic.poker_preflop_context_builder import build_preflop_engine_context  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_preflop_context_from_engine_context(engine_context: Dict[str, Any]) -> PreflopContext:
    """Convert compact PokerVision engine_context into engine PreflopContext.

    Note: dead_cards is intentionally not part of PokerVision engine_context JSON.
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


def _assert_hero_decision(decision: HeroDecision, source_frame_id: str) -> None:
    payload = asdict(decision)

    assert isinstance(decision, HeroDecision)
    assert payload["street"] == "preflop"
    assert payload["engine_action"] in {"fold", "call", "check", "raise", "bet", "all_in"}
    assert isinstance(payload["decision_id"], str) and payload["decision_id"]
    assert isinstance(payload["solver_fingerprint"], str) and payload["solver_fingerprint"]
    assert payload["source_frame_id"] == source_frame_id
    assert payload["preflop"] is not None
    assert payload["debug"]["source_frame_id"] == source_frame_id


def test_all_preflop_fixtures_can_run_through_engine_bridge() -> None:
    files = sorted(FIXTURE_ROOT.glob("*.json"))
    assert files, f"No fixtures found in {FIXTURE_ROOT}"

    for path in files:
        clear_json = _load_json(path)

        engine_context = build_preflop_engine_context(clear_json)
        assert engine_context["status"] == "ok", f"{path.name}: bad engine_context: {engine_context}"

        preflop_context = build_preflop_context_from_engine_context(engine_context)
        decision = solve_hero_preflop(preflop_context)

        _assert_hero_decision(decision, str(engine_context["source_frame_id"]))


def main() -> None:
    files = sorted(FIXTURE_ROOT.glob("*.json"))
    print(f"fixtures: {len(files)}")

    for path in files:
        clear_json = _load_json(path)
        engine_context = build_preflop_engine_context(clear_json)
        preflop_context = build_preflop_context_from_engine_context(engine_context)
        decision = solve_hero_preflop(preflop_context)
        payload = asdict(decision)

        print("=" * 100)
        print(path.name)
        print("source_frame_id=", payload["source_frame_id"])
        print("node_type=", engine_context["node_type"])
        print("hero=", engine_context["hero_pos"], engine_context["hero_hand"])
        print("engine_action=", payload["engine_action"])
        print("decision_id=", payload["decision_id"])
        print("solver_fingerprint=", payload["solver_fingerprint"])
        _assert_hero_decision(decision, str(engine_context["source_frame_id"]))

    print("=" * 100)
    print("[RESULT] OK: preflop engine bridge dry-run tests passed.")


if __name__ == "__main__":
    main()
