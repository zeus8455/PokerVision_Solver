from __future__ import annotations

"""
logic/v21_preflop_real_click_preflight_gate.py

PokerVision Solver V2.1.0 — preflop-only real-click preflight gate.

Diagnostic validator only.
It does not enable real-click and does not execute clicks.
"""

from typing import Any, Dict, List


ALLOWED_SIMPLE_PREFLOP_ACTIONS = {"fold", "call", "check", "check_fold"}
ALLOWED_PREFLOP_RAISE_SEQUENCE = ["98%", "Bet/Raise"]


def _lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _decision_context(runtime_plan: Dict[str, Any]) -> Dict[str, Any]:
    ctx = runtime_plan.get("decision_context")
    return ctx if isinstance(ctx, dict) else {}


def _target_sequence(runtime_plan: Dict[str, Any]) -> List[str]:
    seq = runtime_plan.get("target_sequence")
    return [str(x) for x in seq] if isinstance(seq, list) else []


def build_v21_preflop_real_click_preflight_gate(runtime_plan: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(runtime_plan, dict):
        return {
            "ok": False,
            "allowed": False,
            "reason": "runtime_plan_must_be_object",
            "errors": ["runtime_plan must be a dict."],
        }

    errors: List[str] = []
    warnings: List[str] = []

    ctx = _decision_context(runtime_plan)
    street = _lower(ctx.get("street"))
    action = _lower(runtime_plan.get("planned_action"))
    source = str(runtime_plan.get("source") or "")
    target_sequence = _target_sequence(runtime_plan)

    dry_run = bool(runtime_plan.get("dry_run"))
    real_click_enabled = bool(runtime_plan.get("real_click_enabled"))
    does_not_enable_real_click = bool(runtime_plan.get("does_not_enable_real_click"))

    if street != "preflop":
        errors.append(f"street must be preflop, got {street!r}")

    if real_click_enabled is True:
        errors.append("real_click_enabled must remain False during V2.1.0 preflight.")

    if dry_run is not True:
        errors.append("dry_run must be True during V2.1.0 preflight.")

    if does_not_enable_real_click is not True:
        errors.append("does_not_enable_real_click must be True.")

    if not target_sequence:
        errors.append("target_sequence must be non-empty.")

    allowed_kind = None

    if action in ALLOWED_SIMPLE_PREFLOP_ACTIONS:
        allowed_kind = "simple_preflop_action"
    elif action in {"bet_raise", "raise", "bet"}:
        if source != "Solver_Action_Decision_Candidate_JSON":
            errors.append("preflop raise preflight requires Solver_Action_Decision_Candidate_JSON source.")
        if target_sequence != ALLOWED_PREFLOP_RAISE_SEQUENCE:
            errors.append(
                f"preflop raise target_sequence must be {ALLOWED_PREFLOP_RAISE_SEQUENCE!r}, got {target_sequence!r}"
            )
        allowed_kind = "preflop_raise_98_sequence"
    else:
        errors.append(f"unsupported planned_action for V2.1.0 preflop preflight: {action!r}")

    ok = not errors

    return {
        "schema_version": "v21_preflop_real_click_preflight_gate_v1",
        "ok": ok,
        "allowed": ok,
        "reason": "v21_preflop_real_click_preflight_allowed" if ok else "v21_preflop_real_click_preflight_blocked",
        "allowed_kind": allowed_kind if ok else None,
        "street": street,
        "planned_action": action,
        "source": source,
        "target_sequence": target_sequence,
        "dry_run": dry_run,
        "real_click_enabled": real_click_enabled,
        "does_not_enable_real_click": does_not_enable_real_click,
        "errors": errors,
        "warnings": warnings,
    }


def validate_v21_preflop_real_click_preflight_gate_report(report: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(report, dict):
        return {"ok": False, "errors": ["report must be a dict."], "warnings": []}

    required = {
        "schema_version",
        "ok",
        "allowed",
        "reason",
        "street",
        "planned_action",
        "target_sequence",
        "dry_run",
        "real_click_enabled",
        "does_not_enable_real_click",
        "errors",
        "warnings",
    }

    missing = sorted(required - set(report.keys()))
    if missing:
        errors.append(f"missing required keys: {missing}")

    if report.get("schema_version") != "v21_preflop_real_click_preflight_gate_v1":
        errors.append(f"schema_version mismatch: {report.get('schema_version')!r}")

    if report.get("real_click_enabled") is True:
        errors.append("V2.1.0 preflight report must not allow real_click_enabled=True.")

    if report.get("ok") != report.get("allowed"):
        errors.append("ok and allowed must match.")

    report_errors = report.get("errors")
    if report.get("ok") is True and report_errors:
        errors.append("ok report must not contain errors.")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
