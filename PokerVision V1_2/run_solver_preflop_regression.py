"""
run_solver_preflop_regression.py

PokerVision Solver V1.1 — preflop solver layer regression runner.

Runs all current preflop solver checks:
1. context builder unit test
2. engine bridge dry-run test
3. decision serializer unit test
4. unified solver preview builder unit test
5. real Clear_JSON preflop solver preview audit
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PYTHON_EXE = sys.executable
ROOT = Path(__file__).resolve().parent


CHECKS = [
    ("context_builder_unit", ["test_poker_preflop_context_builder_unit.py"]),
    ("engine_bridge_unit", ["test_poker_preflop_engine_bridge_unit.py"]),
    ("decision_serializer_unit", ["test_poker_engine_decision_serializer_unit.py"]),
    ("solver_preview_builder_unit", ["test_poker_preflop_solver_preview_builder_unit.py"]),
    ("clear_solver_preview_adapter_unit", ["test_poker_clear_solver_preview_adapter_unit.py"]),
    ("clear_json_solver_blocks_audit", ["audit_clear_json_solver_blocks.py", "--root", r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\ui_display_cycle\current_cycle\Clear_JSON"]),
    ("solver_vs_runtime_actions_audit", ["audit_solver_vs_runtime_actions.py", "--root", "C:/PokerVision_Solver/Script_Test_PokerVision_All_files/Test_Replay_Output/ui_display_cycle/current_cycle"]),
    ("solver_action_decision_candidate_unit", ["test_solver_action_decision_candidate_unit.py"]),
    ("solver_action_decision_candidate_audit", ["audit_solver_action_decision_candidates.py", "--root", "C:/PokerVision_Solver/Script_Test_PokerVision_All_files/Test_Replay_Output/ui_display_cycle/current_cycle"]),
    ("solver_runtime_plan_candidate_unit", ["test_solver_runtime_plan_candidate_unit.py"]),
    ("solver_runtime_plan_candidate_audit", ["audit_solver_runtime_plan_candidates.py", "--root", "C:/PokerVision_Solver/Script_Test_PokerVision_All_files/Test_Replay_Output/ui_display_cycle/current_cycle"]),
    ("solver_candidate_runtime_source_guard_unit", ["test_solver_candidate_runtime_source_guard_unit.py"]),
    ("solver_candidate_runtime_source_guard_enabled_unit", ["test_solver_candidate_runtime_source_guard_enabled_unit.py"]),
    ("solver_candidate_shadow_runtime_source_unit", ["test_solver_candidate_shadow_runtime_source_unit.py"]),
    ("solver_runtime_source_guard_audit", ["audit_solver_runtime_source_guard.py", "--root", "C:/PokerVision_Solver/Script_Test_PokerVision_All_files/Test_Replay_Output/ui_display_cycle/current_cycle"]),
    ("runtime_plan_source_selection_unit", ["test_runtime_plan_source_selection_unit.py"]),
    ("real_clear_json_preview_audit", ["audit_real_clear_json_preflop_solver_preview.py"]),
]


def run_check(name: str, args: list[str]) -> int:
    print("=" * 100)
    print(f"RUNNING: {name}")
    print("=" * 100)

    proc = subprocess.run(
        [PYTHON_EXE, *args],
        cwd=str(ROOT),
        text=True,
    )

    print()
    if proc.returncode == 0:
        print(f"[CHECK_RESULT] OK: {name}")
    else:
        print(f"[CHECK_RESULT] FAILED: {name} returncode={proc.returncode}")

    return proc.returncode


def main() -> int:
    print("=" * 100)
    print("POKERVISION SOLVER PREFLOP REGRESSION")
    print("=" * 100)
    print(f"ROOT: {ROOT}")
    print(f"PYTHON: {PYTHON_EXE}")
    print()

    failed = []

    for name, args in CHECKS:
        rc = run_check(name, args)
        if rc != 0:
            failed.append((name, rc))

    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"checks_total: {len(CHECKS)}")
    print(f"checks_failed: {len(failed)}")

    if failed:
        for name, rc in failed:
            print(f"  FAILED: {name} returncode={rc}")
        print()
        print("[RESULT] FAILED: solver preflop regression failed.")
        return 1

    print("[RESULT] OK: solver preflop regression passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
