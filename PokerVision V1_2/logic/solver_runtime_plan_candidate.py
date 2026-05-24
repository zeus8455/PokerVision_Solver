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


def build_solver_action_runtime_plan_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Build diagnostic runtime plan candidate from Solver_Action_Decision_Candidate_JSON."""
    transient_action_decision = _candidate_to_transient_action_decision(candidate)

    runtime_plan = build_action_runtime_plan_from_action_decision(transient_action_decision)
    validation = validate_action_runtime_plan_contract(runtime_plan)
    if not isinstance(validation, dict) or not validation.get("ok"):
        raise ValueError(f"Runtime plan candidate is not valid: {validation}")

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
        errors.append("real_click_enabled must be False for V1.5 diagnostic candidate.")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
