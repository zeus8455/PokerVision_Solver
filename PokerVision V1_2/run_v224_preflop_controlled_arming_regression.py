from __future__ import annotations

"""
run_v224_preflop_controlled_arming_regression.py

PokerVision Solver V2.2.4 — controlled preflop arming regression bundle.

Runs the full diagnostic/no-click preflop readiness and controlled arming chain:
- V2.2.0 controlled arming gate unit
- V2.1.4 candidate export
- V2.1.5 / V2.2.3 strict candidate export validator
- V2.2.1 arming gate export audit
- V2.1.6 no-click readiness regression bundle

Diagnostic-only.
Does not enable or execute real clicks.
"""

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON_EXE = r"C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe"


CHECKS = [
    ("v220_controlled_preflop_real_click_arming_gate_unit", ["test_v220_preflop_controlled_real_click_arming_gate_unit.py"]),
    ("v214_preflop_real_click_candidate_export", ["export_v214_preflop_real_click_candidates.py"]),
    ("v215_v223_strict_candidate_export_validator", ["audit_v215_preflop_real_click_candidate_export_validator.py"]),
    ("v221_preflop_arming_gate_export_audit", ["audit_v221_preflop_arming_gate_export_audit.py"]),
    ("v225_preflop_arming_runtime_output_audit", ["audit_v225_preflop_arming_runtime_output.py"]),
    ("v230_preflop_only_postflop_hard_block_unit", ["test_v230_preflop_only_postflop_hard_block_unit.py"]),
    ("v232_runtime_postflop_never_arms_audit", ["audit_v232_runtime_postflop_never_arms.py"]),
    ("v234_preflop_controlled_arming_dryrun_contract_unit", ["test_v234_preflop_controlled_arming_dryrun_contract_unit.py"]),
    ("v236_preflop_arming_runtime_diagnostic_activation_audit", ["audit_v236_preflop_arming_runtime_diagnostic_activation.py"]),
    ("v238_config_driven_arming_activation_audit", ["audit_v238_config_driven_arming_activation.py"]),
    ("v240_controlled_armed_source_switch_unit", ["test_v240_controlled_armed_source_switch_unit.py"]),
    ("v242_controlled_source_switch_runtime_output_audit", ["audit_v242_controlled_source_switch_runtime_output.py"]),
    ("v244_source_switch_default_safe_audit", ["audit_v244_source_switch_default_safe.py"]),
    ("v216_preflop_real_click_readiness_regression_bundle", ["run_v216_preflop_real_click_readiness_regression.py"]),
]


def run_check(name: str, args: list[str]) -> int:
    print("=" * 100)
    print(f"RUNNING: {name}")
    print("=" * 100)

    proc = subprocess.run(
        [PYTHON_EXE, *args],
        cwd=str(ROOT),
    )

    if proc.returncode == 0:
        print(f"[OK] {name}")
    else:
        print(f"[FAILED] {name} rc={proc.returncode}")

    print()
    return int(proc.returncode)


def main() -> int:
    failures: list[tuple[str, int]] = []

    print("V2.2.4 PREFLOP CONTROLLED ARMING REGRESSION BUNDLE")
    print("=" * 100)
    print("ROOT =", ROOT)
    print("DIAGNOSTIC_ONLY = True")
    print("REAL_CLICK_ENABLED_EXPECTED = False")
    print("CLICK_POINTS_EXPECTED = 0")
    print()

    for name, args in CHECKS:
        rc = run_check(name, args)
        if rc != 0:
            failures.append((name, rc))

    if failures:
        print("=" * 100)
        print("[RESULT] FAILED: V2.2.4 controlled arming regression bundle")
        for name, rc in failures:
            print(f"  {name}: rc={rc}")
        return 1

    print("=" * 100)
    print("[RESULT] OK: V2.2.4 controlled preflop arming regression bundle passed.")
    print("Safety confirmed: diagnostic-only chain, no real-click enabled by this bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
