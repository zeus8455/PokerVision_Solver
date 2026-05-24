"""
test_poker_preflop_solver_preview_builder_unit.py

PokerVision Solver V0.9 — unit tests for unified preflop solver preview builder.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from logic.poker_preflop_solver_preview_builder import build_preflop_solver_preview


FIXTURE_ROOT = Path("test_fixtures/solver_context/preflop_clear_json")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_has_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        if key_name in value:
            return True
        return any(_walk_has_key(v, key_name) for v in value.values())
    if isinstance(value, list):
        return any(_walk_has_key(v, key_name) for v in value)
    return False


def test_all_preflop_fixtures_build_solver_preview() -> None:
    files = sorted(FIXTURE_ROOT.glob("*.json"))
    assert len(files) == 16, f"Expected 16 preflop fixtures, got {len(files)}"

    for path in files:
        clear_json = _load_json(path)
        expected = clear_json["expected_engine_context"]

        result = build_preflop_solver_preview(clear_json)

        assert result["schema_version"] == "poker_preflop_solver_preview_v1"
        assert result["status"] == "ok", f"{path.name}: {result}"
        assert result["source_frame_id"] == clear_json["frame_id"]
        assert result["errors"] == []

        engine_context = result["engine_context"]
        assert engine_context["status"] == "ok"
        assert engine_context["node_type"] == expected["node_type"]
        assert engine_context["hero_hand"] == expected["hero_hand"]
        assert engine_context["hero_pos"] == expected["hero_pos"]

        preview = result["engine_decision_preview"]
        assert preview["schema_version"] == "poker_engine_decision_preview_v1"
        assert preview["status"] == "ok"
        assert preview["street"] == "preflop"
        assert preview["source_frame_id"] == clear_json["frame_id"]
        assert preview["engine_action"] in {"fold", "call", "check", "raise", "bet", "all_in"}
        assert isinstance(preview["decision_id"], str) and preview["decision_id"]
        assert isinstance(preview["solver_fingerprint"], str) and preview["solver_fingerprint"]

        assert not _walk_has_key(result, "weighted_combos"), f"{path.name}: weighted_combos leaked"


def test_bad_input_returns_structured_error() -> None:
    bad_clear_json = {
        "frame_id": "bad_solver_preview_input",
        "board": {"cards": ["A_spades", "K_hearts", "2_clubs"], "street": "flop"},
        "players": {},
    }

    result = build_preflop_solver_preview(bad_clear_json)

    assert result["schema_version"] == "poker_preflop_solver_preview_v1"
    assert result["status"] == "error"
    assert result["source_frame_id"] == "bad_solver_preview_input"
    assert result["engine_decision_preview"] is None
    assert result["engine_context"]["status"] == "error"
    assert result["errors"]


def main() -> None:
    test_all_preflop_fixtures_build_solver_preview()
    test_bad_input_returns_structured_error()
    print("[RESULT] OK: preflop solver preview builder unit tests passed.")


if __name__ == "__main__":
    main()
