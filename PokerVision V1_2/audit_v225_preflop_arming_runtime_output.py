from __future__ import annotations

"""
audit_v225_preflop_arming_runtime_output.py

PokerVision Solver V2.2.5 — audit V22 controlled arming diagnostics in Action_Runtime_Plan_JSON.

Diagnostic-only.
Does not enable real-click.
Does not execute clicks.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


ROOT = Path(r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output")


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _iter_runtime_plans(root: Path):
    for path in root.rglob("*.json"):
        parts = set(path.parts)
        if "Action_Runtime_Plan_JSON" not in parts:
            continue
        yield path


def audit(root: Path = ROOT) -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []

    for path in _iter_runtime_plans(root):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            counters["runtime_plan_unreadable"] += 1
            continue

        counters["runtime_plan_json_checked"] += 1

        v21 = payload.get("v21_preflop_real_click_preflight_gate")
        if isinstance(v21, dict):
            counters["v21_preflight_present"] += 1
        else:
            counters["v21_preflight_missing"] += 1
            continue

        v22 = payload.get("v22_controlled_real_click_arming_gate")
        v22_validation = payload.get("v22_controlled_real_click_arming_gate_validation")

        if isinstance(v22, dict):
            counters["v22_arming_present"] += 1
        else:
            counters["v22_arming_missing"] += 1
            errors.append({"path": str(path), "reason": "v22_arming_missing"})
            continue

        if isinstance(v22_validation, dict):
            counters["v22_arming_validation_present"] += 1
        else:
            counters["v22_arming_validation_missing"] += 1
            errors.append({"path": str(path), "reason": "v22_arming_validation_missing"})

        if v22.get("diagnostic_only") is True:
            counters["diagnostic_only_true"] += 1
        else:
            errors.append({"path": str(path), "reason": "diagnostic_only_not_true", "value": v22.get("diagnostic_only")})

        if v22.get("does_not_enable_real_click") is True:
            counters["does_not_enable_real_click_true"] += 1
        else:
            errors.append({"path": str(path), "reason": "does_not_enable_real_click_not_true", "value": v22.get("does_not_enable_real_click")})

        if v22.get("armed") is True:
            counters["armed_true"] += 1
            errors.append({"path": str(path), "reason": "armed_true_forbidden_in_v225_default"})
        else:
            counters["armed_false"] += 1

        if payload.get("real_click_enabled") is True:
            counters["runtime_real_click_enabled_true"] += 1
            errors.append({"path": str(path), "reason": "runtime_real_click_enabled_true_forbidden"})

        if v22.get("candidate_real_click_enabled") is True:
            counters["candidate_real_click_enabled_true"] += 1
            errors.append({"path": str(path), "reason": "candidate_real_click_enabled_true_forbidden"})

        if len(examples) < 20:
            examples.append({
                "path": str(path),
                "planned_action": payload.get("planned_action"),
                "target_sequence": payload.get("target_sequence"),
                "v22_ok": v22.get("ok"),
                "v22_armed": v22.get("armed"),
                "v22_reason": v22.get("reason"),
                "real_click_enabled": payload.get("real_click_enabled"),
            })

    ok = (
        counters.get("v21_preflight_present", 0) > 0
        and counters.get("v22_arming_present", 0) == counters.get("v21_preflight_present", 0)
        and counters.get("v22_arming_validation_present", 0) == counters.get("v21_preflight_present", 0)
        and counters.get("armed_true", 0) == 0
        and counters.get("runtime_real_click_enabled_true", 0) == 0
        and counters.get("candidate_real_click_enabled_true", 0) == 0
        and not errors
    )

    return {
        "schema_version": "v225_preflop_arming_runtime_output_audit_v1",
        "ok": ok,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "root": str(root),
        "counters": dict(counters),
        "errors": errors,
        "examples": examples,
    }


def main() -> int:
    report = audit()

    print("V2.2.5 PREFLOP ARMING RUNTIME OUTPUT AUDIT")
    print("=" * 100)
    print("ROOT =", report["root"])

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("EXAMPLES:")
    for item in report["examples"][:20]:
        print(
            f"  action={item['planned_action']} seq={item['target_sequence']} "
            f"v22_ok={item['v22_ok']} armed={item['v22_armed']} "
            f"real_click={item['real_click_enabled']} reason={item['v22_reason']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:30]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.2.5 preflop arming runtime output audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
