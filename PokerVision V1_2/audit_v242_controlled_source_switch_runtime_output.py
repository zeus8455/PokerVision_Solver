from __future__ import annotations

"""
audit_v242_controlled_source_switch_runtime_output.py

PokerVision Solver V2.4.2 — controlled source switch runtime output audit.

Purpose:
- Build a runtime source-selection contract with controlled config enabled.
- Confirm Solver_Action_Decision_Candidate_JSON is selected.
- Confirm V22 arming diagnostic is armed=True.
- Confirm no real-click is enabled.
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


def _enable_controlled_dryrun_source_switch() -> None:
    dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
    dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
    dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False

    dac.V11_CLICK_DRY_RUN = True
    dac.V11_REAL_MOUSE_CLICK_ENABLED = False
    dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED = True
    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN = True
    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK = True
    dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS = ["table_01"]


def audit() -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    snapshot = _snapshot()

    try:
        _enable_controlled_dryrun_source_switch()

        selected = dac.build_runtime_plan_source_selection_contract(
            action_decision_state=_action_decision_state(),
            solver_candidate_state=_solver_candidate_state(),
        )

        counters["selection_checked"] += 1

        if selected.get("selected_source") == "Solver_Action_Decision_Candidate_JSON":
            counters["solver_candidate_selected"] += 1
        else:
            errors.append({
                "reason": "solver_candidate_not_selected",
                "selected_source": selected.get("selected_source"),
                "selection_reason": selected.get("reason"),
                "message": selected.get("message"),
            })

        guard = selected.get("guard")
        if isinstance(guard, dict) and guard.get("allowed") is True:
            counters["guard_allowed"] += 1
        else:
            errors.append({"reason": "guard_not_allowed", "guard": guard})

        plan = selected.get("runtime_candidate_plan")
        if isinstance(plan, dict):
            counters["runtime_candidate_plan_present"] += 1

            if plan.get("dry_run") is True:
                counters["plan_dry_run_true"] += 1
            else:
                errors.append({"reason": "plan_dry_run_not_true", "value": plan.get("dry_run")})

            if plan.get("real_click_enabled") is False:
                counters["plan_real_click_false"] += 1
            else:
                errors.append({"reason": "plan_real_click_not_false", "value": plan.get("real_click_enabled")})

            if plan.get("source") == "Solver_Action_Decision_Candidate_JSON":
                counters["plan_source_solver_candidate"] += 1
            else:
                errors.append({"reason": "plan_source_wrong", "source": plan.get("source")})
        else:
            errors.append({"reason": "runtime_candidate_plan_missing"})

        v22 = selected.get("v22_controlled_real_click_arming_gate")
        if isinstance(v22, dict):
            counters["v22_present"] += 1

            if v22.get("armed") is True:
                counters["v22_armed_true"] += 1
            else:
                errors.append({"reason": "v22_not_armed", "v22": v22})

            if v22.get("diagnostic_only") is True:
                counters["v22_diagnostic_only_true"] += 1
            else:
                errors.append({"reason": "v22_diagnostic_only_not_true", "v22": v22})

            if v22.get("does_not_enable_real_click") is True:
                counters["v22_does_not_enable_real_click_true"] += 1
            else:
                errors.append({"reason": "v22_does_not_enable_real_click_not_true", "v22": v22})

            if v22.get("candidate_real_click_enabled") is False:
                counters["v22_candidate_real_click_false"] += 1
            else:
                errors.append({"reason": "v22_candidate_real_click_not_false", "v22": v22})
        else:
            errors.append({"reason": "v22_missing"})

    finally:
        _restore(snapshot)

    ok = (
        counters.get("solver_candidate_selected", 0) == 1
        and counters.get("v22_armed_true", 0) == 1
        and counters.get("plan_real_click_false", 0) == 1
        and counters.get("v22_candidate_real_click_false", 0) == 1
        and not errors
    )

    return {
        "schema_version": "v242_controlled_source_switch_runtime_output_audit_v1",
        "ok": ok,
        "counters": dict(counters),
        "errors": errors,
    }


def main() -> int:
    report = audit()

    print("V2.4.2 CONTROLLED SOURCE SWITCH RUNTIME OUTPUT AUDIT")
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
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.4.2 controlled source switch runtime output audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
