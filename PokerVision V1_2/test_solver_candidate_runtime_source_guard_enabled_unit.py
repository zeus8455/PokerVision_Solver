"""
test_solver_candidate_runtime_source_guard_enabled_unit.py

PokerVision Solver V1.6.1 — dry-run-only enabled guard test.

This test monkeypatches display_analysis_cycle module variables only.
It does not edit config.py and does not enable real clicks.
"""

from __future__ import annotations

import display_analysis_cycle as dac


def test_v16_guard_allows_solver_candidate_source_in_dry_run_only_mode() -> None:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    }

    try:
        dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False
        dac.V11_CLICK_DRY_RUN = True
        dac.V11_REAL_MOUSE_CLICK_ENABLED = False
        dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

        guard = dac.build_solver_candidate_runtime_source_guard()

        assert guard["enabled"] is True
        assert guard["allowed"] is True
        assert guard["reason"] == "v16_allowed_dry_run_only"
        assert guard["source"] == "Solver_Action_Decision_Candidate_JSON"

        flags = guard["real_click_flags"]
        assert flags["V11_CLICK_DRY_RUN"] is True
        assert flags["V11_REAL_MOUSE_CLICK_ENABLED"] is False
        assert flags["V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"] is False
        assert flags["V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK"] is False

    finally:
        for name, value in original.items():
            setattr(dac, name, value)


def test_v16_guard_blocks_when_real_mouse_click_enabled() -> None:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    }

    try:
        dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False
        dac.V11_CLICK_DRY_RUN = True
        dac.V11_REAL_MOUSE_CLICK_ENABLED = True
        dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

        guard = dac.build_solver_candidate_runtime_source_guard()

        assert guard["enabled"] is True
        assert guard["allowed"] is False
        assert guard["reason"] == "v16_blocked_because_real_click_flag_is_enabled"

    finally:
        for name, value in original.items():
            setattr(dac, name, value)


def main() -> None:
    test_v16_guard_allows_solver_candidate_source_in_dry_run_only_mode()
    test_v16_guard_blocks_when_real_mouse_click_enabled()
    print("[RESULT] OK: solver candidate runtime source guard enabled unit tests passed.")


if __name__ == "__main__":
    main()
