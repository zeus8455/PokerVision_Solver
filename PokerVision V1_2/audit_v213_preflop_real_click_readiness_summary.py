from __future__ import annotations

"""
audit_v213_preflop_real_click_readiness_summary.py

PokerVision Solver V2.1.3 — strict preflop real-click readiness summary.

Reads saved Action_Runtime_Plan_JSON files and summarizes V21 preflight eligibility.
Diagnostic-only.
Does not modify JSON files.
Does not enable or execute real clicks.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_ROOT = Path(r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output")


def _iter_runtime_plan_json(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return root.rglob("*.runtime_plan.json")


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def audit(root: Path = DEFAULT_ROOT) -> Dict[str, Any]:
    counters = Counter()
    action_counter = Counter()
    allowed_kind_counter = Counter()
    blocked_reason_counter = Counter()
    examples: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for path in _iter_runtime_plan_json(root):
        payload = _read_json(path)
        if payload is None:
            counters["runtime_plan_unreadable"] += 1
            continue

        counters["runtime_plan_json_checked"] += 1

        preflight = payload.get("v21_preflop_real_click_preflight_gate")
        validation = payload.get("v21_preflop_real_click_preflight_gate_validation")

        if not isinstance(preflight, dict):
            counters["v21_preflight_missing"] += 1

            name_lower = path.name.lower()
            source = str(payload.get("source") or "")
            decision_context = payload.get("decision_context") if isinstance(payload.get("decision_context"), dict) else {}
            street = str(decision_context.get("street") or "").lower()

            # V2.1.3 is a preflop-only readiness summary.
            # Postflop / old Action_Decision fallback runtime plans are expected to have no V21 preflight block.
            if "preflop" in name_lower and source == "Solver_Action_Decision_Candidate_JSON":
                errors.append({"path": str(path), "reason": "v21_preflight_missing_on_solver_preflop_runtime_plan"})
            else:
                counters["skipped_without_v21_preflight"] += 1
            continue

        if not isinstance(validation, dict):
            counters["v21_preflight_validation_missing"] += 1
            errors.append({"path": str(path), "reason": "v21_preflight_validation_missing"})
            continue

        counters["v21_preflight_present"] += 1

        if validation.get("ok") is not True:
            counters["v21_preflight_validation_not_ok"] += 1
            errors.append({
                "path": str(path),
                "reason": "v21_preflight_validation_not_ok",
                "validation": validation,
            })

        if preflight.get("real_click_enabled") is True or payload.get("real_click_enabled") is True:
            counters["real_click_enabled_true_total"] += 1
            errors.append({"path": str(path), "reason": "real_click_enabled_true_forbidden"})

        action = str(preflight.get("planned_action") or payload.get("planned_action") or "")
        allowed_kind = preflight.get("allowed_kind")
        action_counter[action] += 1
        allowed_kind_counter[allowed_kind] += 1

        if preflight.get("ok") is True and preflight.get("allowed") is True:
            counters["eligible_total"] += 1
        else:
            counters["blocked_or_invalid_total"] += 1
            for item in preflight.get("errors") or []:
                blocked_reason_counter[str(item)] += 1

        if allowed_kind == "simple_preflop_action":
            counters["simple_preflop_action_total"] += 1
        elif allowed_kind == "preflop_raise_98_sequence":
            counters["preflop_raise_98_sequence_total"] += 1

        if len(examples) < 20:
            examples.append({
                "file": path.name,
                "ok": preflight.get("ok"),
                "allowed": preflight.get("allowed"),
                "allowed_kind": allowed_kind,
                "street": preflight.get("street"),
                "planned_action": action,
                "target_sequence": preflight.get("target_sequence"),
                "real_click_enabled": preflight.get("real_click_enabled"),
                "validation_ok": validation.get("ok"),
                "path": str(path),
            })

    ok = (
        counters.get("runtime_plan_json_checked", 0) > 0
        and counters.get("v21_preflight_present", 0) > 0
        and counters.get("eligible_total", 0) > 0
        and counters.get("real_click_enabled_true_total", 0) == 0
        and counters.get("v21_preflight_validation_not_ok", 0) == 0
        and not errors
    )

    return {
        "schema_version": "v213_preflop_real_click_readiness_summary_v1",
        "root": str(root),
        "ok": ok,
        "counters": dict(counters),
        "action_counter": dict(action_counter),
        "allowed_kind_counter": dict(allowed_kind_counter),
        "blocked_reason_counter": dict(blocked_reason_counter),
        "errors": errors,
        "examples": examples,
    }


def main() -> int:
    report = audit()

    print("V2.1.3 PREFLOP REAL-CLICK READINESS SUMMARY")
    print("=" * 100)
    print("ROOT =", report["root"])

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("ACTION_COUNTER:", report["action_counter"])
    print("ALLOWED_KIND_COUNTER:", report["allowed_kind_counter"])
    print("BLOCKED_REASON_COUNTER:", report["blocked_reason_counter"])

    print()
    print("EXAMPLES:")
    for item in report["examples"][:20]:
        print(
            f"  {item['file']} | ok={item['ok']} | kind={item['allowed_kind']} "
            f"| action={item['planned_action']} | seq={item['target_sequence']} "
            f"| real_click={item['real_click_enabled']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.1.3 preflop real-click readiness summary")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
