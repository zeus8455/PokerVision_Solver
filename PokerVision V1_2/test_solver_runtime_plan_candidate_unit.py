"""
test_solver_runtime_plan_candidate_unit.py

PokerVision Solver V1.5 — tests for runtime plan candidate built from solver action candidate.
"""

from __future__ import annotations

import json
from pathlib import Path

from logic.solver_runtime_plan_candidate import (
    build_solver_action_runtime_plan_candidate,
    validate_solver_action_runtime_plan_candidate,
)


CANDIDATE_ROOT = Path(
    r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\ui_display_cycle\current_cycle\Solver_Action_Decision_Candidate_JSON"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_runtime_plan_candidates_from_replay_solver_candidates() -> None:
    files = sorted(CANDIDATE_ROOT.rglob("*.json"))
    assert len(files) == 11, f"Expected 11 solver candidate files, got {len(files)}"

    for path in files:
        candidate = _load_json(path)
        plan = build_solver_action_runtime_plan_candidate(candidate)
        validation = validate_solver_action_runtime_plan_candidate(plan)

        assert validation["ok"], f"{path.name}: {validation}"
        assert plan["source"] == "Solver_Action_Decision_Candidate_JSON"
        assert plan["source_solver_candidate_frame_id"] == candidate["source_clear_frame_id"]
        assert plan["planned_action"] in {"fold", "call", "check", "check_fold", "raise", "bet_raise"}
        assert plan["solver_stub"] is False
        assert plan["diagnostic_candidate"] is True
        assert plan["does_not_replace_runtime_plan"] is True
        assert plan["does_not_enable_real_click"] is True
        assert plan["real_click_enabled"] is False

        if plan["status"] == "ok":
            assert plan["target_sequence"]
            assert plan["target_sequences"]
        elif plan["status"] == "blocked":
            assert plan["blocked_reason"]


def main() -> None:
    test_build_runtime_plan_candidates_from_replay_solver_candidates()
    print("[RESULT] OK: solver runtime plan candidate unit tests passed.")


if __name__ == "__main__":
    main()
