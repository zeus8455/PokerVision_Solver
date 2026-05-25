"""
audit_solver_runtime_source_guard.py

PokerVision Solver V1.7 — audit runtime source guard baseline inside Dark_JSON.

Expected default baseline:
- Action_Runtime_Plan source remains Action_Decision_JSON
- solver candidate runtime source guard is present
- guard.allowed=False
- guard.reason=v16_switch_disabled
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not object")
    return data


def audit_runtime_source_guard(root: Path) -> Dict[str, Any]:
    dark_root = root / "Dark_JSON"

    counters = Counter()
    errors = []
    examples = []

    for path in sorted(dark_root.rglob("*.json")):
        counters["dark_json_total"] += 1

        try:
            dark = _load_json(path)
        except Exception as exc:
            counters["bad_dark_json"] += 1
            errors.append({"path": str(path), "reason": "bad_dark_json", "message": str(exc)})
            continue

        contract = dark.get("clear_json_contract") if isinstance(dark.get("clear_json_contract"), dict) else {}
        action_contract = contract.get("action_decision_contract") if isinstance(contract.get("action_decision_contract"), dict) else {}
        runtime_contract = action_contract.get("action_runtime_plan_contract") if isinstance(action_contract.get("action_runtime_plan_contract"), dict) else {}

        if not runtime_contract:
            counters["runtime_plan_contract_missing_or_skipped"] += 1
            continue

        counters["runtime_plan_contract_present"] += 1

        source = runtime_contract.get("source")
        guard = runtime_contract.get("solver_candidate_runtime_source_guard")

        if source == "Action_Decision_JSON":
            counters["runtime_source_action_decision_json"] += 1
        else:
            counters["runtime_source_other"] += 1
            errors.append({"path": str(path), "reason": "runtime_source_not_action_decision_json", "source": source})

        if not isinstance(guard, dict):
            counters["guard_missing"] += 1
            errors.append({"path": str(path), "reason": "guard_missing"})
            continue

        counters["guard_present"] += 1

        allowed = guard.get("allowed")
        reason = guard.get("reason")

        if allowed is False:
            counters["guard_allowed_false"] += 1
        else:
            counters["guard_allowed_not_false"] += 1
            errors.append({"path": str(path), "reason": "guard_allowed_not_false", "allowed": allowed})

        if reason == "v16_switch_disabled":
            counters["guard_reason_switch_disabled"] += 1
        else:
            counters["guard_reason_other"] += 1
            errors.append({"path": str(path), "reason": "guard_reason_other", "guard_reason": reason})

        examples.append({
            "file": path.name,
            "runtime_source": source,
            "guard_allowed": allowed,
            "guard_reason": reason,
        })

    return {
        "root": str(root),
        "counters": dict(counters),
        "errors": errors,
        "examples": examples[:50],
    }


def print_report(report: Dict[str, Any]) -> int:
    counters = Counter(report.get("counters") or {})

    print("=" * 100)
    print("POKERVISION SOLVER RUNTIME SOURCE GUARD AUDIT")
    print("=" * 100)
    print("ROOT:", report["root"])
    print()

    print("COUNTS:")
    for key in [
        "dark_json_total",
        "bad_dark_json",
        "runtime_plan_contract_present",
        "runtime_plan_contract_missing_or_skipped",
        "runtime_source_action_decision_json",
        "runtime_source_other",
        "guard_present",
        "guard_missing",
        "guard_allowed_false",
        "guard_allowed_not_false",
        "guard_reason_switch_disabled",
        "guard_reason_other",
    ]:
        print(f"  {key}: {counters.get(key, 0)}")

    print()
    print("EXAMPLES:")
    for item in report.get("examples", [])[:20]:
        print(
            f"  {item.get('file')} | source={item.get('runtime_source')} "
            f"| allowed={item.get('guard_allowed')} | reason={item.get('guard_reason')}"
        )

    errors = report.get("errors") or []
    if errors:
        print()
        print("ERRORS:")
        for item in errors[:20]:
            print(f"  {item}")
        print()
        print("[RESULT] FAILED: solver runtime source guard audit found errors.")
        return 1

    print()
    print("[RESULT] OK: solver runtime source guard audit passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit V1.7 solver runtime source guard baseline.")
    parser.add_argument(
        "--root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle"),
        help="current_cycle root containing Dark_JSON.",
    )
    args = parser.parse_args()
    return print_report(audit_runtime_source_guard(Path(args.root)))


if __name__ == "__main__":
    raise SystemExit(main())
