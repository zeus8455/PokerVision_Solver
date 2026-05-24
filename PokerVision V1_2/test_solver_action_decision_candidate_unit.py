"""
test_solver_action_decision_candidate_unit.py

PokerVision Solver V1.4 — unit tests for solver action decision candidate builder.
"""

from __future__ import annotations

import json
from pathlib import Path

from logic.solver_action_decision_candidate import (
    build_solver_action_decision_candidate_from_clear_json,
    validate_solver_action_decision_candidate,
)


REPLAY_CLEAR_ROOT = Path(
    r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\ui_display_cycle\current_cycle\Clear_JSON"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _active_preflop_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(REPLAY_CLEAR_ROOT.rglob("*.json")):
        clear_json = _load_json(path)
        if (clear_json.get("board") or {}).get("street") != "preflop":
            continue
        players = clear_json.get("players") or {}
        if not any(isinstance(v, dict) and v.get("hero") is True for v in players.values()):
            continue
        if not isinstance(clear_json.get("engine_decision_preview"), dict):
            continue
        files.append(path)
    return files


def test_build_candidate_from_replay_clear_json_solver_blocks() -> None:
    files = _active_preflop_files()
    assert len(files) == 11, f"Expected 11 replay active preflop files, got {len(files)}"

    for path in files:
        clear_json = _load_json(path)
        candidate = build_solver_action_decision_candidate_from_clear_json(clear_json)
        validation = validate_solver_action_decision_candidate(candidate)

        assert validation["ok"], f"{path.name}: {validation}"
        assert candidate["source"] == "Clear_JSON.engine_decision_preview"
        assert candidate["source_clear_frame_id"] == clear_json["frame_id"]
        assert candidate["solver_stub"] is False
        assert candidate["dry_run_safe"] is True
        assert candidate["action"] in {"fold", "check", "call", "check_fold", "raise", "bet"}
        assert candidate["target_button_classes"]

        engine_action = clear_json["engine_decision_preview"]["engine_action"]
        if engine_action in {"fold", "call", "check"}:
            assert candidate["action"] == engine_action


def test_missing_engine_preview_rejected() -> None:
    bad = {
        "frame_id": "bad_missing_preview",
        "board": {"street": "preflop", "cards": []},
        "players": {"BB": {"hero": True, "cards": ["A_spades", "K_hearts"]}},
    }

    try:
        build_solver_action_decision_candidate_from_clear_json(bad)
    except ValueError as exc:
        assert "engine_decision_preview" in str(exc)
    else:
        raise AssertionError("missing engine_decision_preview was accepted")


def main() -> None:
    test_build_candidate_from_replay_clear_json_solver_blocks()
    test_missing_engine_preview_rejected()
    print("[RESULT] OK: solver action decision candidate unit tests passed.")


if __name__ == "__main__":
    main()
