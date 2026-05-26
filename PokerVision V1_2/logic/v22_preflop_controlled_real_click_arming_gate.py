from __future__ import annotations

"""
logic/v22_preflop_controlled_real_click_arming_gate.py

PokerVision Solver V2.2.0 — controlled preflop real-click arming gate.

Purpose:
- Validate whether a V2.1.4 exported preflop candidate is structurally eligible
  for a future controlled real-click arming stage.
- Does NOT enable real-click.
- Does NOT click.
- Does NOT mutate runtime plans.
"""

from typing import Any, Dict, Mapping


SCHEMA_VERSION = "v22_preflop_controlled_real_click_arming_gate_v1"
STAGE = "v2_2_0_controlled_preflop_real_click_arming_gate_diagnostic_only"

ALLOWED_KINDS = {"simple_preflop_action", "preflop_raise_98_sequence"}
ALLOWED_SIMPLE_ACTIONS = {"fold", "call", "check", "check_fold"}
RAISE_SEQUENCE = ["98%", "Bet/Raise"]


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _fail(reason: str, *, candidate: Mapping[str, Any] | None = None, errors: list[str] | None = None) -> Dict[str, Any]:
    candidate = candidate or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "ok": False,
        "armed": False,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "reason": reason,
        "errors": list(errors or [reason]),
        "candidate_action": candidate.get("planned_action"),
        "candidate_allowed_kind": candidate.get("allowed_kind"),
        "candidate_target_sequence": _as_list(candidate.get("target_sequence")),
        "candidate_real_click_enabled": candidate.get("real_click_enabled"),
    }


def build_v22_preflop_controlled_real_click_arming_gate(
    candidate: Mapping[str, Any] | None,
    *,
    allowed_table_ids: list[str] | None = None,
    required_table_id: str | None = None,
    slot_bbox_guard_ok: bool = True,
    no_repeat_guard_ok: bool = True,
    button_availability_guard_ok: bool = True,
    export_validator_ok: bool = True,
    explicit_controlled_real_click_token: bool = False,
) -> Dict[str, Any]:
    if not isinstance(candidate, Mapping) or not candidate:
        return _fail("candidate_missing", candidate=candidate)

    errors: list[str] = []

    if export_validator_ok is not True:
        errors.append("export_validator_not_ok")

    if explicit_controlled_real_click_token is not True:
        errors.append("explicit_controlled_real_click_token_missing")

    if candidate.get("diagnostic_only") is not True:
        errors.append("candidate_diagnostic_only_not_true")

    if candidate.get("does_not_enable_real_click") is not True:
        errors.append("candidate_does_not_enable_real_click_not_true")

    if candidate.get("real_click_enabled") is not False:
        errors.append("candidate_real_click_enabled_must_be_false_before_arming")

    if candidate.get("dry_run") is not True:
        errors.append("candidate_dry_run_must_be_true_before_arming")

    action = str(candidate.get("planned_action") or "")
    allowed_kind = candidate.get("allowed_kind")
    target_sequence = _as_list(candidate.get("target_sequence"))
    decision_context = _as_dict(candidate.get("decision_context"))
    table_id = str(decision_context.get("table_id") or candidate.get("table_id") or "")

    if allowed_kind not in ALLOWED_KINDS:
        errors.append(f"unsupported_allowed_kind:{allowed_kind}")

    if allowed_kind == "simple_preflop_action" and action not in ALLOWED_SIMPLE_ACTIONS:
        errors.append(f"unsupported_simple_action:{action}")

    if allowed_kind == "preflop_raise_98_sequence":
        if action != "bet_raise":
            errors.append(f"raise_action_must_be_bet_raise:{action}")
        if target_sequence != RAISE_SEQUENCE:
            errors.append(f"raise_sequence_must_be_98_bet_raise:{target_sequence}")

    v21 = _as_dict(candidate.get("v21_preflight"))
    if v21.get("ok") is not True or v21.get("allowed") is not True:
        errors.append("v21_preflight_not_ok_or_allowed")

    if str(v21.get("street") or decision_context.get("street") or "").lower() != "preflop":
        errors.append("street_must_be_preflop")

    if v21.get("real_click_enabled") is not False:
        errors.append("v21_real_click_enabled_must_be_false")

    allowed_table_ids = allowed_table_ids or []
    if required_table_id:
        allowed_table_ids = [required_table_id]

    if allowed_table_ids:
        if not table_id:
            errors.append("table_id_missing")
        elif table_id not in allowed_table_ids:
            errors.append(f"table_id_not_allowed:{table_id}")

    if slot_bbox_guard_ok is not True:
        errors.append("slot_bbox_guard_not_ok")

    if no_repeat_guard_ok is not True:
        errors.append("no_repeat_guard_not_ok")

    if button_availability_guard_ok is not True:
        errors.append("button_availability_guard_not_ok")

    if errors:
        return _fail("v22_arming_gate_blocked", candidate=candidate, errors=errors)

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "ok": True,
        "armed": True,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "reason": "v22_controlled_preflop_candidate_structurally_armable",
        "errors": [],
        "candidate_action": action,
        "candidate_allowed_kind": allowed_kind,
        "candidate_target_sequence": target_sequence,
        "candidate_table_id": table_id,
        "candidate_real_click_enabled": candidate.get("real_click_enabled"),
        "required_table_id": required_table_id,
        "allowed_table_ids": allowed_table_ids,
        "slot_bbox_guard_ok": slot_bbox_guard_ok,
        "no_repeat_guard_ok": no_repeat_guard_ok,
        "button_availability_guard_ok": button_availability_guard_ok,
        "explicit_controlled_real_click_token": explicit_controlled_real_click_token,
    }


def validate_v22_preflop_controlled_real_click_arming_gate_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []

    if not isinstance(report, Mapping):
        return {"ok": False, "errors": ["report_must_be_object"]}

    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_mismatch")

    if report.get("stage") != STAGE:
        errors.append("stage_mismatch")

    if report.get("diagnostic_only") is not True:
        errors.append("diagnostic_only_must_be_true")

    if report.get("does_not_enable_real_click") is not True:
        errors.append("does_not_enable_real_click_must_be_true")

    if report.get("armed") is True and report.get("ok") is not True:
        errors.append("armed_true_requires_ok_true")

    if report.get("candidate_real_click_enabled") is True:
        errors.append("candidate_real_click_enabled_true_forbidden")

    if report.get("armed") is True:
        if report.get("candidate_allowed_kind") not in ALLOWED_KINDS:
            errors.append("armed_candidate_allowed_kind_invalid")
        if report.get("candidate_allowed_kind") == "preflop_raise_98_sequence":
            if report.get("candidate_target_sequence") != RAISE_SEQUENCE:
                errors.append("armed_raise_sequence_invalid")

    return {"ok": not errors, "errors": errors}
