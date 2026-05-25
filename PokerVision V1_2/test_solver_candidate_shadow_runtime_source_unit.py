"""
test_solver_candidate_shadow_runtime_source_unit.py

PokerVision Solver V1.6.2 — shadow dry-run runtime source test.

Purpose:
- temporarily enable solver-candidate runtime source inside test only
- build runtime plan from Solver_Action_Decision_Candidate_JSON
- verify action alignment and dry-run safety
- do not edit config.py
- do not enable real clicks
"""

from __future__ import annotations

import json
from pathlib import Path

import display_analysis_cycle as dac
from logic.solver_runtime_plan_candidate import (
    build_solver_action_runtime_plan_candidate,
    validate_solver_action_runtime_plan_candidate,
)


CANDIDATE_ROOT = Path(
    r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\ui_display_cycle\current_cycle\Solver_Action_Decision_Candidate_JSON"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _enable_shadow_dry_run_guard() -> dict:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    }

    dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
    dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
    dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False
    dac.V11_CLICK_DRY_RUN = True
    dac.V11_REAL_MOUSE_CLICK_ENABLED = False
    dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

    return original


def _restore_guard(original: dict) -> None:
    for name, value in original.items():
        setattr(dac, name, value)


def test_shadow_runtime_source_builds_solver_runtime_plans_in_dry_run() -> None:
    original = _enable_shadow_dry_run_guard()

    try:
        guard = dac.build_solver_candidate_runtime_source_guard()
        assert guard["enabled"] is True
        assert guard["allowed"] is True
        assert guard["reason"] == "v16_allowed_dry_run_only"

        files = sorted(CANDIDATE_ROOT.rglob("*.json"))
        assert len(files) == 11, f"Expected 11 solver candidate files, got {len(files)}"

        status_counter: dict[str, int] = {}
        action_pairs: list[tuple[str, str, str]] = []
        expected_ok = 0
        expected_blocked = 0

        for path in files:
            candidate = _load_json(path)
            plan = build_solver_action_runtime_plan_candidate(candidate)
            validation = validate_solver_action_runtime_plan_candidate(plan)

            assert validation["ok"], f"{path.name}: {validation}"
            assert plan["source"] == "Solver_Action_Decision_Candidate_JSON"
            assert plan["solver_stub"] is False
            assert plan["diagnostic_candidate"] is True
            assert plan["does_not_replace_runtime_plan"] is True
            assert plan["does_not_enable_real_click"] is True
            assert plan["real_click_enabled"] is False
            assert plan["dry_run"] is True

            status = str(plan.get("status"))
            status_counter[status] = status_counter.get(status, 0) + 1
            action_pairs.append((path.name, str(candidate.get("action")), str(plan.get("planned_action"))))

            candidate_action = str(candidate.get("action"))
            planned_action = str(plan.get("planned_action"))

            if candidate_action == "raise":
                expected_blocked += 1
                assert planned_action in {"raise", "bet_raise"}
                assert plan["status"] == "blocked"
                assert plan["blocked_reason"] == "bet_raise_branch_disabled_for_v1_1_first_real_click_stage"
            else:
                expected_ok += 1
                assert planned_action == candidate_action
                assert plan["status"] == "ok"
                assert plan["target_sequence"]

        assert status_counter.get("ok", 0) == expected_ok
        assert status_counter.get("blocked", 0) == expected_blocked
        assert expected_ok + expected_blocked == len(files)

    finally:
        _restore_guard(original)


def main() -> None:
    test_shadow_runtime_source_builds_solver_runtime_plans_in_dry_run()
    print("[RESULT] OK: solver candidate shadow runtime source unit tests passed.")


if __name__ == "__main__":
    main()
