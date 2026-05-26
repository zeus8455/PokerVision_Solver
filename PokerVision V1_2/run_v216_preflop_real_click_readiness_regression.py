from __future__ import annotations

"""
run_v216_preflop_real_click_readiness_regression.py

PokerVision Solver V2.1.6 — final no-click regression bundle for V2.1 preflop readiness chain.

Runs:
- V2.1.0 preflight gate unit
- V2.1.2 output audit
- V2.1.3 readiness summary
- V2.1.4 candidate export
- V2.1.5 candidate export validator
- V1.1 full regression

Diagnostic-only.
Does not enable or execute real clicks.
"""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON_EXE = r"C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe"


CHECKS = [
    ("v210_preflop_real_click_preflight_gate_unit", ["test_v210_preflop_real_click_preflight_gate_unit.py"]),
    ("v212_preflop_preflight_output_audit", ["audit_v212_preflop_preflight_output.py"]),
    ("v213_preflop_real_click_readiness_summary", ["audit_v213_preflop_real_click_readiness_summary.py"]),
    ("v214_preflop_real_click_candidate_export", ["export_v214_preflop_real_click_candidates.py"]),
    ("v215_preflop_real_click_candidate_export_validator", ["audit_v215_preflop_real_click_candidate_export_validator.py"]),
    ("v12_full_regression", ["test_v12_full_regression.py"]),
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

    print("V2.1.6 PREFLOP REAL-CLICK READINESS REGRESSION BUNDLE")
    print("=" * 100)
    print("ROOT =", ROOT)
    print("DIAGNOSTIC_ONLY = True")
    print("REAL_CLICK_ENABLED_EXPECTED = False")
    print()

    for name, args in CHECKS:
        rc = run_check(name, args)
        if rc != 0:
            failures.append((name, rc))

    if failures:
        print("=" * 100)
        print("[RESULT] FAILED: V2.1.6 regression bundle")
        for name, rc in failures:
            print(f"  {name}: rc={rc}")
        return 1

    print("=" * 100)
    print("[RESULT] OK: V2.1.6 preflop real-click readiness regression bundle passed.")
    print("Safety confirmed: diagnostic-only chain, no real-click enabled by this bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
