"""
test_solver_candidate_runtime_source_guard_unit.py

PokerVision Solver V1.6 — tests for controlled solver-candidate runtime source guard.
"""

from __future__ import annotations

import config
from display_analysis_cycle import build_solver_candidate_runtime_source_guard


def test_v16_guard_default_switch_disabled() -> None:
    guard = build_solver_candidate_runtime_source_guard()

    assert guard["enabled"] is False
    assert guard["allowed"] is False
    assert guard["source"] == "Solver_Action_Decision_Candidate_JSON"
    assert guard["reason"] == "v16_switch_disabled"

    flags = guard["real_click_flags"]
    assert flags["V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK"] is False


def test_v16_config_defaults_are_safe() -> None:
    assert config.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE is False
    assert config.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY is True
    assert config.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK is False
    assert config.V16_SOLVER_CANDIDATE_RUNTIME_SOURCE_LABEL == "Solver_Action_Decision_Candidate_JSON"


def main() -> None:
    test_v16_guard_default_switch_disabled()
    test_v16_config_defaults_are_safe()
    print("[RESULT] OK: solver candidate runtime source guard unit tests passed.")


if __name__ == "__main__":
    main()
