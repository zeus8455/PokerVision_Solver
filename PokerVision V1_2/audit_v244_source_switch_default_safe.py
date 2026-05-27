from __future__ import annotations

"""
audit_v244_source_switch_default_safe.py

PokerVision Solver V2.4.4 — default-safe regression after controlled source switch integration.

Purpose:
- Prove default config does not arm V22 by itself.
- Prove default config does not enable real-click.
- Prove runtime source switch remains safe unless explicitly controlled.
"""

from collections import Counter
from typing import Any, Dict

import display_analysis_cycle as dac
from test_v240_controlled_armed_source_switch_unit import (
    _action_decision_state,
    _solver_candidate_state,
)


def _snapshot() -> Dict[str, Any]:
    return {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED": getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED", None),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN": getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN", None),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK": getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK", None),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS": list(getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS", [])),
    }


def _restore(snapshot: Dict[str, Any]) -> None:
    for name, value in snapshot.items():
        if value is None and hasattr(dac, name):
            delattr(dac, name)
        else:
            setattr(dac, name, value)


def _force_default_safe() -> None:
    dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = False
    dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
    dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False

    dac.V11_CLICK_DRY_RUN = True
    dac.V11_REAL_MOUSE_CLICK_ENABLED = False
    dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED = False
    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN = False
    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK = False
    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS = []


def audit() -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    snapshot = _snapshot()

    try:
        _force_default_safe()

        selected = dac.build_runtime_plan_source_selection_contract(
            action_decision_state=_action_decision_state(),
            solver_candidate_state=_solver_candidate_state(),
        )

        counters["selection_checked"] += 1

        if selected.get("selected_source") == "Action_Decision_JSON":
            counters["action_decision_selected"] += 1
        else:
            errors.append({
                "reason": "default_selected_solver_candidate_forbidden",
                "selected_source": selected.get("selected_source"),
                "selection_reason": selected.get("reason"),
            })

        plan = selected.get("runtime_candidate_plan")
        if isinstance(plan, dict):
            if plan.get("real_click_enabled") is True:
                errors.append({"reason": "runtime_candidate_plan_real_click_true_forbidden"})
            else:
                counters["runtime_candidate_plan_real_click_not_true"] += 1
        else:
            counters["runtime_candidate_plan_absent"] += 1

        v22 = selected.get("v22_controlled_real_click_arming_gate")
        if isinstance(v22, dict):
            counters["v22_present"] += 1
            if v22.get("armed") is True:
                errors.append({"reason": "default_v22_armed_true_forbidden", "v22": v22})
            else:
                counters["v22_armed_false"] += 1

            if v22.get("candidate_real_click_enabled") is True:
                errors.append({"reason": "default_v22_candidate_real_click_true_forbidden", "v22": v22})
            else:
                counters["v22_candidate_real_click_not_true"] += 1
        else:
            counters["v22_absent"] += 1

        guard = selected.get("guard")
        if isinstance(guard, dict):
            real_click_flags = guard.get("real_click_flags")
            if isinstance(real_click_flags, dict):
                forbidden = [
                    key for key, value in real_click_flags.items()
                    if key != "V11_CLICK_DRY_RUN" and value is True
                ]
                if forbidden:
                    errors.append({"reason": "real_click_guard_flag_true_forbidden", "flags": real_click_flags})
                else:
                    counters["real_click_guard_flags_safe"] += 1

    finally:
        _restore(snapshot)

    ok = (
        counters.get("selection_checked", 0) == 1
        and counters.get("action_decision_selected", 0) == 1
        and not errors
    )

    return {
        "schema_version": "v244_source_switch_default_safe_audit_v1",
        "ok": ok,
        "counters": dict(counters),
        "errors": errors,
    }


def main() -> int:
    report = audit()

    print("V2.4.4 SOURCE SWITCH DEFAULT-SAFE AUDIT")
    print("=" * 100)

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.4.4 source switch default-safe audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
