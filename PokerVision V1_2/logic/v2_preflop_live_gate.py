from __future__ import annotations

"""
logic/v2_preflop_live_gate.py

PokerVision Solver V2.0.1 — preflop live-gate audit layer.

Purpose:
- Audit whether Solver_Action_Decision_Candidate_JSON / Solver_Action_Runtime_Plan_Candidate
  is eligible for the future V2 preflop live-click chain.
- Does NOT enable real-click.
- Does NOT modify runtime plan.
- Does NOT replace Action_Runtime_Plan_JSON.
- Does NOT allow postflop/service/unknown clicks.

This is an audit-only gate for the transition from V1.11.1 dry-run source integration
to V2 live-preflop verification.
"""

from typing import Any, Dict, List, Mapping, Optional


SCHEMA_VERSION = "v2_preflop_live_gate_v1"
STAGE = "v2_0_1_preflop_live_gate_audit_only"

SOLVER_RUNTIME_SOURCE = "Solver_Action_Decision_Candidate_JSON"
ACTION_BUTTON_BRANCH = "action_button"

SIMPLE_PREFLOP_ACTIONS = {"fold", "call", "check", "check_fold"}
RAISE_PREFLOP_ACTIONS = {"bet_raise", "raise", "bet"}
ALLOWED_PREFLOP_ACTIONS = SIMPLE_PREFLOP_ACTIONS | RAISE_PREFLOP_ACTIONS

SUPPORTED_SIZE_BUTTONS = {"33%", "50%", "70%", "98%"}
RAISE_BUTTONS = {"Bet/Raise", "Raise"}
SERVICE_BRANCH_NAMES = {"service", "trigger_ui", "unknown"}


def _clean_string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_action(value: Any) -> str:
    text = _clean_string(value).lower().replace("-", "_").replace("/", "_").replace(" ", "_")
    aliases = {
        "checkfold": "check_fold",
        "check_fold": "check_fold",
        "fold": "fold",
        "call": "call",
        "check": "check",
        "bet": "bet_raise",
        "raise": "bet_raise",
        "bet_raise": "bet_raise",
        "betraise": "bet_raise",
        "bet__raise": "bet_raise",
    }
    return aliases.get(text, text)


def _as_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _target_sequence(runtime_candidate_plan: Mapping[str, Any]) -> List[str]:
    seq = runtime_candidate_plan.get("target_sequence")
    if isinstance(seq, list):
        return [_clean_string(x) for x in seq if _clean_string(x)]

    buttons = runtime_candidate_plan.get("target_button_classes")
    if isinstance(buttons, list):
        return [_clean_string(x) for x in buttons if _clean_string(x)]

    return []


def _decision_context(solver_candidate_state: Mapping[str, Any]) -> Dict[str, Any]:
    ctx = solver_candidate_state.get("decision_context")
    return dict(ctx) if isinstance(ctx, dict) else {}


def _candidate_street(solver_candidate_state: Mapping[str, Any]) -> str:
    ctx = _decision_context(solver_candidate_state)
    return _clean_string(ctx.get("street") or "unknown").lower()


def _runtime_branch(runtime_candidate_plan: Mapping[str, Any]) -> str:
    return _clean_string(runtime_candidate_plan.get("runtime_branch") or "unknown").lower()


def _source_label(runtime_candidate_plan: Mapping[str, Any]) -> str:
    return _clean_string(runtime_candidate_plan.get("source") or "")


def _size_policy(solver_candidate_state: Mapping[str, Any], runtime_candidate_plan: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    value = solver_candidate_state.get("size_policy")
    if isinstance(value, dict):
        return dict(value)

    value = runtime_candidate_plan.get("size_policy")
    if isinstance(value, dict):
        return dict(value)

    return None


def _blocked(
    *,
    reason: str,
    message: str,
    solver_candidate_state: Mapping[str, Any],
    runtime_candidate_plan: Mapping[str, Any],
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ctx = _decision_context(solver_candidate_state)
    action = _normalize_action(
        runtime_candidate_plan.get("planned_action")
        or solver_candidate_state.get("action")
        or ctx.get("engine_action")
    )
    target_sequence = _target_sequence(runtime_candidate_plan)

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "ok": False,
        "real_click_eligible": False,
        "must_remain_dry_run": True,
        "reason": reason,
        "message": message,
        "source": _source_label(runtime_candidate_plan),
        "expected_source": SOLVER_RUNTIME_SOURCE,
        "street": _candidate_street(solver_candidate_state),
        "runtime_branch": _runtime_branch(runtime_candidate_plan),
        "action": action,
        "target_sequence": target_sequence,
        "target_sequences": _as_list(runtime_candidate_plan.get("target_sequences")),
        "dry_run": bool(runtime_candidate_plan.get("dry_run", True)),
        "real_click_enabled": bool(runtime_candidate_plan.get("real_click_enabled", False)),
        "decision_id": solver_candidate_state.get("decision_id") or runtime_candidate_plan.get("solver_candidate_decision_id"),
        "solver_fingerprint": solver_candidate_state.get("solver_fingerprint") or runtime_candidate_plan.get("solver_candidate_fingerprint"),
        "audit_only": True,
    }
    if extra:
        payload.update(extra)
    return payload


def build_v2_preflop_live_gate(
    *,
    solver_candidate_state: Optional[Mapping[str, Any]],
    runtime_candidate_plan: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Return V2 preflop live-gate audit result.

    This function intentionally never enables real-click.
    It only describes whether the selected solver candidate is structurally eligible
    for a future V2 preflop-only live-click stage.
    """

    if not isinstance(solver_candidate_state, Mapping) or not solver_candidate_state:
        return _blocked(
            reason="solver_candidate_state_missing",
            message="V2 preflop gate requires Solver_Action_Decision_Candidate_JSON state.",
            solver_candidate_state={},
            runtime_candidate_plan=runtime_candidate_plan or {},
        )

    if not isinstance(runtime_candidate_plan, Mapping) or not runtime_candidate_plan:
        return _blocked(
            reason="runtime_candidate_plan_missing",
            message="V2 preflop gate requires Solver_Action_Runtime_Plan_Candidate state.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan={},
        )

    source = _source_label(runtime_candidate_plan)
    if source != SOLVER_RUNTIME_SOURCE:
        return _blocked(
            reason="non_solver_runtime_source_blocked",
            message="V2 preflop gate only accepts Solver_Action_Decision_Candidate_JSON runtime source.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    street = _candidate_street(solver_candidate_state)
    if street != "preflop":
        return _blocked(
            reason="non_preflop_blocked",
            message="V2 live-click eligibility is blocked outside preflop.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    branch = _runtime_branch(runtime_candidate_plan)
    if branch != ACTION_BUTTON_BRANCH:
        return _blocked(
            reason="non_action_button_branch_blocked",
            message="V2 preflop gate only allows the Action_Button_Detector branch.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    if branch in SERVICE_BRANCH_NAMES:
        return _blocked(
            reason="service_or_unknown_branch_blocked",
            message="Service/unknown real-click branches are forbidden in V2 preflop gate.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    action = _normalize_action(runtime_candidate_plan.get("planned_action") or solver_candidate_state.get("action"))
    if action not in ALLOWED_PREFLOP_ACTIONS:
        return _blocked(
            reason="unsupported_preflop_action_blocked",
            message=f"Unsupported V2 preflop action: {action!r}.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    target_sequence = _target_sequence(runtime_candidate_plan)
    if not target_sequence:
        return _blocked(
            reason="empty_target_sequence_blocked",
            message="V2 preflop gate requires a non-empty target_sequence.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    if bool(runtime_candidate_plan.get("real_click_enabled", False)):
        return _blocked(
            reason="real_click_enabled_must_remain_false",
            message="V2.0.1 is audit-only. runtime_candidate_plan.real_click_enabled must remain False.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    if not bool(runtime_candidate_plan.get("dry_run", True)):
        return _blocked(
            reason="dry_run_must_remain_true",
            message="V2.0.1 is audit-only. runtime_candidate_plan.dry_run must remain True.",
            solver_candidate_state=solver_candidate_state,
            runtime_candidate_plan=runtime_candidate_plan,
        )

    size_policy = _size_policy(solver_candidate_state, runtime_candidate_plan)
    is_raise = action in {"bet_raise", "raise", "bet"}

    if is_raise:
        has_raise_button = any(btn in RAISE_BUTTONS for btn in target_sequence)
        if not has_raise_button:
            return _blocked(
                reason="raise_without_raise_button_blocked",
                message="V2 preflop raise audit requires Bet/Raise or Raise in target_sequence.",
                solver_candidate_state=solver_candidate_state,
                runtime_candidate_plan=runtime_candidate_plan,
            )

        # Open raise may be Bet/Raise only. Iso/3bet should be 98% -> Bet/Raise.
        has_size_button = any(btn in SUPPORTED_SIZE_BUTTONS for btn in target_sequence)
        reason = (
            "v2_preflop_raise_with_size_audit_only_real_click_not_enabled"
            if has_size_button
            else "v2_preflop_open_raise_audit_only_real_click_not_enabled"
        )

        return {
            "schema_version": SCHEMA_VERSION,
            "stage": STAGE,
            "ok": True,
            "real_click_eligible": False,
            "must_remain_dry_run": True,
            "reason": reason,
            "message": "V2 preflop raise candidate is structurally eligible for audit, but real-click remains disabled.",
            "source": source,
            "street": street,
            "runtime_branch": branch,
            "action": "bet_raise",
            "size_policy": size_policy,
            "target_sequence": target_sequence,
            "target_sequences": _as_list(runtime_candidate_plan.get("target_sequences")),
            "dry_run": bool(runtime_candidate_plan.get("dry_run", True)),
            "real_click_enabled": bool(runtime_candidate_plan.get("real_click_enabled", False)),
            "decision_id": solver_candidate_state.get("decision_id") or runtime_candidate_plan.get("solver_candidate_decision_id"),
            "solver_fingerprint": solver_candidate_state.get("solver_fingerprint") or runtime_candidate_plan.get("solver_candidate_fingerprint"),
            "audit_only": True,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "ok": True,
        "real_click_eligible": False,
        "must_remain_dry_run": True,
        "reason": "v2_preflop_simple_action_audit_only",
        "message": "V2 preflop simple action candidate is structurally eligible for audit, but real-click remains disabled.",
        "source": source,
        "street": street,
        "runtime_branch": branch,
        "action": action,
        "size_policy": size_policy,
        "target_sequence": target_sequence,
        "target_sequences": _as_list(runtime_candidate_plan.get("target_sequences")),
        "dry_run": bool(runtime_candidate_plan.get("dry_run", True)),
        "real_click_enabled": bool(runtime_candidate_plan.get("real_click_enabled", False)),
        "decision_id": solver_candidate_state.get("decision_id") or runtime_candidate_plan.get("solver_candidate_decision_id"),
        "solver_fingerprint": solver_candidate_state.get("solver_fingerprint") or runtime_candidate_plan.get("solver_candidate_fingerprint"),
        "audit_only": True,
    }


def validate_v2_preflop_live_gate_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(report, Mapping):
        return {"ok": False, "errors": ["V2 preflop live gate report must be an object."], "warnings": []}

    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {report.get('schema_version')!r}")

    if report.get("stage") != STAGE:
        errors.append(f"stage mismatch: {report.get('stage')!r}")

    if report.get("real_click_eligible") is not False:
        errors.append("V2.0.1 audit-only gate must keep real_click_eligible=False.")

    if report.get("must_remain_dry_run") is not True:
        errors.append("V2.0.1 audit-only gate must keep must_remain_dry_run=True.")

    if report.get("real_click_enabled") is True:
        errors.append("V2.0.1 audit-only gate must not accept real_click_enabled=True.")

    if report.get("dry_run") is False:
        errors.append("V2.0.1 audit-only gate must not accept dry_run=False.")

    if report.get("ok") is True:
        if report.get("street") != "preflop":
            errors.append("ok=True requires street='preflop'.")
        if report.get("source") != SOLVER_RUNTIME_SOURCE:
            errors.append(f"ok=True requires source={SOLVER_RUNTIME_SOURCE!r}.")
        if report.get("runtime_branch") != ACTION_BUTTON_BRANCH:
            errors.append(f"ok=True requires runtime_branch={ACTION_BUTTON_BRANCH!r}.")
        if report.get("action") not in {"fold", "call", "check", "check_fold", "bet_raise"}:
            errors.append(f"ok=True has unsupported action: {report.get('action')!r}")
        if not isinstance(report.get("target_sequence"), list) or not report.get("target_sequence"):
            errors.append("ok=True requires non-empty target_sequence.")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
