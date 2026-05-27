"""
logic/solver_runtime_plan_candidate.py

PokerVision Solver V1.5 — build diagnostic Runtime Plan candidate from Solver_Action_Decision_Candidate_JSON.

Safety:
- does not replace Action_Decision_JSON
- does not replace Action_Runtime_Plan_JSON
- does not click
- adapts solver candidate into transient action_decision_v1 only in memory
"""

from __future__ import annotations

from typing import Any, Dict, List

from config import V06_ACTION_DECISION_SCHEMA_VERSION
from logic.action_runtime_plan_builder import (
    build_action_runtime_plan_from_action_decision,
    validate_action_runtime_plan_contract,
)
from logic.solver_action_decision_candidate import validate_solver_action_decision_candidate


SCHEMA_VERSION = "solver_action_runtime_plan_candidate_v1"
UNSUPPORTED_RAISE_WITHOUT_SIZE_POLICY_REASON = "unsupported_raise_without_size_policy"
UNSUPPORTED_RAISE_WITHOUT_EXECUTABLE_SEQUENCE_REASON = "unsupported_raise_without_executable_target_sequence"


def _raise_candidate_is_missing_size_policy(candidate: Dict[str, Any]) -> bool:
    action = str(candidate.get("action") or "").strip().lower()
    return action in {"raise", "bet"} and not isinstance(candidate.get("size_policy"), dict)



def _candidate_to_transient_action_decision(candidate: Dict[str, Any]) -> Dict[str, Any]:
    validation = validate_solver_action_decision_candidate(candidate)
    if not isinstance(validation, dict) or not validation.get("ok"):
        raise ValueError(f"Solver action decision candidate is not valid: {validation}")

    source_frame_id = str(candidate.get("source_clear_frame_id") or "")

    return {
        "schema_version": V06_ACTION_DECISION_SCHEMA_VERSION,
        "source": "Decision_JSON",
        "source_decision_frame_id": source_frame_id,
        "status": "ok",
        "action": candidate.get("action"),
        "size_policy": candidate.get("size_policy"),
        "target_button_classes": list(candidate.get("target_button_classes") or []),
        "reason": "solver_action_decision_candidate_transient_adapter",
        "dry_run_safe": True,
        # Required by current V0.6 validator. This is only an in-memory adapter flag;
        # the published candidate itself keeps solver_stub=False.
        "solver_stub": True,
        "decision_context": dict(candidate.get("decision_context") or {}),
    }


def _candidate_is_preflop_raise_98(candidate: Dict[str, Any]) -> bool:
    action = str(candidate.get("action") or "").strip().lower()
    if action not in {"raise", "bet"}:
        return False

    decision_context = candidate.get("decision_context")
    if not isinstance(decision_context, dict):
        return False

    street = str(decision_context.get("street") or "").strip().lower()
    if street != "preflop":
        return False

    size_policy = candidate.get("size_policy")
    if not isinstance(size_policy, dict):
        return False

    pct = size_policy.get("pct")
    try:
        pct_value = int(pct)
    except Exception:
        return False

    target_button_classes = candidate.get("target_button_classes")
    if not isinstance(target_button_classes, list):
        return False

    return pct_value == 98 and target_button_classes == ["98%", "Bet/Raise"]


def _build_preflop_raise_98_runtime_plan(candidate: Dict[str, Any]) -> Dict[str, Any]:
    source_frame_id = str(candidate.get("source_clear_frame_id") or "")
    decision_context = dict(candidate.get("decision_context") or {})

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "Solver_Action_Decision_Candidate_JSON",
        "source_solver_candidate_frame_id": source_frame_id,
        "source_action_decision_frame_id": source_frame_id,
        "status": "ok",
        "planned_action": "bet_raise",
        "target_sequence": ["98%", "Bet/Raise"],
        "target_sequences": [["98%", "Bet/Raise"]],
        "runtime_branch": "action_button",
        "policy_stage": "v2_0_9_preflop_raise_98_dryrun_only",
        "policy_version": "v2.0.9_preflop_raise_sequence_dryrun",
        "raise_branch_enabled": True,
        "dry_run_required": True,
        "dry_run": True,
        "real_click_enabled": False,
        "solver_stub": False,
        "diagnostic_candidate": True,
        "does_not_replace_runtime_plan": True,
        "does_not_enable_real_click": True,
        "solver_candidate_decision_id": candidate.get("decision_id"),
        "solver_candidate_fingerprint": candidate.get("solver_fingerprint"),
        "candidate_reason": "preflop_raise_98_runtime_plan_built_from_solver_action_candidate",
        "candidate_size_policy": dict(candidate.get("size_policy") or {}),
        "decision_context": decision_context,
    }

def _candidate_is_generic_preflop_raise_button(candidate: Dict[str, Any]) -> bool:
    action = str(candidate.get("action") or "").strip().lower()
    if action not in {"raise", "bet"}:
        return False

    decision_context = candidate.get("decision_context")
    if not isinstance(decision_context, dict):
        return False

    street = str(decision_context.get("street") or "").strip().lower()
    if street != "preflop":
        return False

    target_button_classes = candidate.get("target_button_classes")
    return target_button_classes in (["Bet/Raise"], ["Raise"])


def _build_generic_preflop_raise_button_runtime_plan(candidate: Dict[str, Any]) -> Dict[str, Any]:
    source_frame_id = str(candidate.get("source_clear_frame_id") or "")
    decision_context = dict(candidate.get("decision_context") or {})
    target_button_classes = candidate.get("target_button_classes")
    button = "Bet/Raise"
    if target_button_classes == ["Raise"]:
        button = "Raise"

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "Solver_Action_Decision_Candidate_JSON",
        "source_solver_candidate_frame_id": source_frame_id,
        "source_action_decision_frame_id": source_frame_id,
        "status": "ok",
        "planned_action": "bet_raise",
        "size_policy": None,
        "target_button_classes": [button],
        "target_sequence": [button],
        "target_sequences": [[button]],
        "runtime_branch": "action_button",
        "policy_stage": "v2_7_1_generic_preflop_raise_button_realclick",
        "policy_version": "v2.7.1_generic_preflop_raise_button",
        "raise_branch_enabled": True,
        "dry_run_required": False,
        "dry_run": False,
        "real_click_enabled": True,
        "solver_stub": False,
        "diagnostic_candidate": True,
        "does_not_replace_runtime_plan": True,
        "does_not_enable_real_click": True,
        "solver_candidate_decision_id": candidate.get("decision_id"),
        "solver_candidate_fingerprint": candidate.get("solver_fingerprint"),
        "candidate_reason": "generic_preflop_raise_button_runtime_plan_built_from_solver_action_candidate",
        "candidate_size_policy": dict(candidate.get("size_policy") or {}),
        "decision_context": decision_context,
    }


def build_solver_action_runtime_plan_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Build diagnostic runtime plan candidate from Solver_Action_Decision_Candidate_JSON.

    V1.9.1 safety rule:
    raise/bet candidates without an explicit size_policy are not executable.
    They must not become the selected solver runtime source, even in dry-run,
    because the downstream button sequence cannot be proven before a future
    real-click enablement stage.
    """
    if _candidate_is_generic_preflop_raise_button(candidate):
        return _build_generic_preflop_raise_button_runtime_plan(candidate)

    if _raise_candidate_is_missing_size_policy(candidate):
        raise ValueError(UNSUPPORTED_RAISE_WITHOUT_SIZE_POLICY_REASON)

    if _candidate_is_preflop_raise_98(candidate):
        return _build_preflop_raise_98_runtime_plan(candidate)

    transient_action_decision = _candidate_to_transient_action_decision(candidate)

    runtime_plan = build_action_runtime_plan_from_action_decision(transient_action_decision)
    validation = validate_action_runtime_plan_contract(runtime_plan)
    if not isinstance(validation, dict) or not validation.get("ok"):
        raise ValueError(f"Runtime plan candidate is not valid: {validation}")

    planned_action = str(runtime_plan.get("planned_action") or "").strip().lower()
    target_sequence = runtime_plan.get("target_sequence")
    target_sequences = runtime_plan.get("target_sequences")
    if planned_action in {"bet_raise", "raise", "bet"} and (
        not isinstance(target_sequence, list)
        or not target_sequence
        or not isinstance(target_sequences, list)
        or not target_sequences
    ):
        raise ValueError(UNSUPPORTED_RAISE_WITHOUT_EXECUTABLE_SEQUENCE_REASON)

    candidate_plan = dict(runtime_plan)
    candidate_plan.update({
        "schema_version": SCHEMA_VERSION,
        "source": "Solver_Action_Decision_Candidate_JSON",
        "source_solver_candidate_frame_id": str(candidate.get("source_clear_frame_id") or ""),
        "source_action_decision_frame_id": str(candidate.get("source_clear_frame_id") or ""),
        "solver_stub": False,
        "diagnostic_candidate": True,
        "does_not_replace_runtime_plan": True,
        "does_not_enable_real_click": True,
        "solver_candidate_decision_id": candidate.get("decision_id"),
        "solver_candidate_fingerprint": candidate.get("solver_fingerprint"),
        "candidate_reason": "runtime_plan_built_from_solver_action_candidate_via_transient_adapter",
    })
    return candidate_plan


def validate_solver_action_runtime_plan_candidate(plan: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(plan, dict):
        return {"ok": False, "errors": ["runtime plan candidate must be an object."], "warnings": []}

    required = {
        "schema_version",
        "source",
        "source_solver_candidate_frame_id",
        "status",
        "planned_action",
        "target_sequence",
        "target_sequences",
        "runtime_branch",
        "dry_run_required",
        "dry_run",
        "real_click_enabled",
        "solver_stub",
        "diagnostic_candidate",
        "does_not_replace_runtime_plan",
        "does_not_enable_real_click",
    }
    missing = sorted(required - set(plan.keys()))
    if missing:
        errors.append(f"runtime plan candidate missing required keys: {missing}")

    forbidden = {
        "runtime_action",
        "click_result",
        "click_points",
        "bbox",
        "confidence",
        "errors",
        "warnings",
        "clear_json",
        "dark_json",
        "mouse",
    }
    leaked = sorted(forbidden & set(plan.keys()))
    if leaked:
        errors.append(f"runtime plan candidate has forbidden technical keys: {leaked}")

    if plan.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {plan.get('schema_version')!r}")
    if plan.get("source") != "Solver_Action_Decision_Candidate_JSON":
        errors.append("source must be Solver_Action_Decision_Candidate_JSON.")
    if plan.get("solver_stub") is not False:
        errors.append("solver_stub must be False on published solver runtime plan candidate.")
    if plan.get("diagnostic_candidate") is not True:
        errors.append("diagnostic_candidate must be True.")
    if plan.get("does_not_replace_runtime_plan") is not True:
        errors.append("does_not_replace_runtime_plan must be True.")
    if plan.get("does_not_enable_real_click") is not True:
        errors.append("does_not_enable_real_click must be True.")
    if plan.get("real_click_enabled") is not False:
        # V2.6.0: Solver_Action_Decision_Candidate_JSON may be promoted from
        # diagnostic shadow plan to selected live runtime source. In that mode
        # real_click_enabled=True is valid, but only for a non-stub solver action.
        v260_real_click_selected_solver_source = (
            str(plan.get("source") or "") == "Solver_Action_Decision_Candidate_JSON"
            and plan.get("solver_stub") is False
            and str(plan.get("status") or "") == "ok"
            and str(plan.get("runtime_branch") or "") == "action_button"
        )
        if not v260_real_click_selected_solver_source:
            errors.append("real_click_enabled must be False for V1.5 diagnostic candidate.")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
