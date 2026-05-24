"""
test_poker_engine_decision_serializer_unit.py

PokerVision Solver V0.8 — unit tests for compact HeroDecision serializer.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent
ENGINE_REFERENCE_DIR = PROJECT_ROOT.parent / "Engine_Reference"
FIXTURE_ROOT = PROJECT_ROOT / "test_fixtures" / "solver_context" / "preflop_clear_json"

if str(ENGINE_REFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_REFERENCE_DIR))

from hero_decision import solve_hero_preflop  # noqa: E402
from logic.poker_engine_decision_serializer import serialize_hero_decision_preview  # noqa: E402
from logic.poker_preflop_context_builder import build_preflop_engine_context  # noqa: E402
from test_poker_preflop_engine_bridge_unit import build_preflop_context_from_engine_context  # noqa: E402


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_has_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        if key_name in value:
            return True
        return any(_walk_has_key(v, key_name) for v in value.values())
    if isinstance(value, list):
        return any(_walk_has_key(v, key_name) for v in value)
    return False


def test_serialize_all_preflop_fixtures_to_compact_preview() -> None:
    files = sorted(FIXTURE_ROOT.glob("*.json"))
    assert len(files) == 16, f"Expected 16 preflop fixtures, got {len(files)}"

    for path in files:
        clear_json = _load_json(path)
        engine_context = build_preflop_engine_context(clear_json)
        assert engine_context["status"] == "ok", f"{path.name}: bad engine_context"

        preflop_context = build_preflop_context_from_engine_context(engine_context)
        decision = solve_hero_preflop(preflop_context)
        preview = serialize_hero_decision_preview(decision)

        assert preview["schema_version"] == "poker_engine_decision_preview_v1"
        assert preview["status"] == "ok"
        assert preview["street"] == "preflop"
        assert preview["engine_action"] in {"fold", "call", "check", "raise", "bet", "all_in"}
        assert isinstance(preview["decision_id"], str) and preview["decision_id"]
        assert isinstance(preview["solver_fingerprint"], str) and preview["solver_fingerprint"]
        assert preview["source_frame_id"] == engine_context["source_frame_id"]

        assert isinstance(preview["preflop"], dict)
        preflop_action = preview["preflop"]["action"]
        engine_action = preview["engine_action"]
        assert preflop_action
        assert (
            preflop_action == engine_action
            or (preflop_action in {"3bet", "4bet", "5bet", "iso_raise"} and engine_action == "raise")
        )
        assert isinstance(preview["preflop"]["matching_actions"], list)

        range_source = preview["preflop"].get("range_source")
        if range_source is not None:
            assert "weighted_combos" not in range_source
            assert isinstance(range_source.get("combo_count"), int)

        assert not _walk_has_key(preview, "weighted_combos"), f"{path.name}: weighted_combos leaked"


def main() -> None:
    test_serialize_all_preflop_fixtures_to_compact_preview()
    print("[RESULT] OK: engine decision serializer unit tests passed.")


if __name__ == "__main__":
    main()
