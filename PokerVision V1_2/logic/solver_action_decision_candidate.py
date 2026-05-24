"""
logic/solver_action_decision_candidate.py

PokerVision Solver V1.4 — build Action_Decision-compatible candidate from Clear_JSON.engine_decision_preview.

This module is diagnostic/safe:
- does not replace current Action_Decision_JSON
- does not create runtime plan
- does not click
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "solver_action_decision_candidate_v1"

VALID_CANDIDATE_ACTIONS = {"fold", "check", "call", "check_fold", "raise", "bet"}


def _normalize_action(action: Any) -> str:
    value = str(action or "").strip().lower()
    aliases = {
        "check/fold": "check_fold",
        "check-fold": "check_fold",
        "all_in": "raise",
        "all-in": "raise",
        "3bet": "raise",
        "4bet": "raise",
        "5bet": "raise",
        "iso_raise": "raise",
    }
    value = aliases.get(value, value)
    if value == "bet":
        return "raise"
    return value


def _normalize_size_policy(size_pct: Any) -> Optional[Dict[str, Any]]:
    if size_pct is None:
        return None

    try:
        value = int(float(size_pct))
    except (TypeError, ValueError):
        return None

    if value not in {33, 50, 70, 98}:
        return {"kind": "pct", "value": value, "supported_by_first_runtime_stage": False}

    return {"kind": "pct", "value": value, "supported_by_first_runtime_stage": True}


def _target_buttons_for_action(action: str, size_policy: Optional[Dict[str, Any]]) -> List[str]:
    if action == "fold":
        return ["FOLD"]
    if action == "check":
        return ["Check"]
    if action == "call":
        return ["Call"]
    if action == "check_fold":
        return ["Check", "Check/fold", "FOLD"]
    if action in {"raise", "bet"}:
        buttons: List[str] = []
        if isinstance(size_policy, dict):
            value = str(size_policy.get("value") or "").strip()
            if value in {"33", "50", "70", "98"}:
                buttons.append(f"{value}%")
        buttons.append("Bet/Raise")
        return buttons
    return ["FOLD"]


def build_solver_action_decision_candidate_from_clear_json(clear_json: Dict[str, Any]) -> Dict[str, Any]:
    """Build a safe Action_Decision-compatible candidate from Clear_JSON solver preview."""
    if not isinstance(clear_json, dict):
        raise ValueError("Clear_JSON must be an object.")

    frame_id = str(clear_json.get("frame_id") or "")
    board = clear_json.get("board") if isinstance(clear_json.get("board"), dict) else {}
    players = clear_json.get("players") if isinstance(clear_json.get("players"), dict) else {}

    engine_preview = clear_json.get("engine_decision_preview")
    if not isinstance(engine_preview, dict):
        raise ValueError("Clear_JSON has no engine_decision_preview object.")

    raw_action = engine_preview.get("engine_action")
    action = _normalize_action(raw_action)
    if action not in VALID_CANDIDATE_ACTIONS:
        raise ValueError(f"Unsupported solver engine_action for candidate: {raw_action!r}")

    size_policy = _normalize_size_policy(engine_preview.get("size_pct"))

    hero_position = ""
    for pos, payload in players.items():
        if isinstance(payload, dict) and payload.get("hero") is True:
            hero_position = str(pos)
            break

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "Clear_JSON.engine_decision_preview",
        "source_clear_frame_id": frame_id,
        "status": "ok",
        "action": action,
        "size_policy": size_policy,
        "target_button_classes": _target_buttons_for_action(action, size_policy),
        "reason": "from_engine_decision_preview",
        "dry_run_safe": True,
        "solver_stub": False,
        "decision_id": engine_preview.get("decision_id"),
        "solver_fingerprint": engine_preview.get("solver_fingerprint"),
        "decision_context": {
            "street": str(board.get("street") or "unknown"),
            "hero_position": hero_position,
            "source_frame_id": frame_id,
            "engine_action": raw_action,
        },
    }


def validate_solver_action_decision_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if not isinstance(candidate, dict):
        return {"ok": False, "errors": ["candidate must be an object."], "warnings": []}

    required = {
        "schema_version",
        "source",
        "source_clear_frame_id",
        "status",
        "action",
        "size_policy",
        "target_button_classes",
        "reason",
        "dry_run_safe",
        "solver_stub",
        "decision_context",
    }

    missing = sorted(required - set(candidate.keys()))
    if missing:
        errors.append(f"candidate missing required keys: {missing}")

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
    }
    leaked = sorted(forbidden & set(candidate.keys()))
    if leaked:
        errors.append(f"candidate has forbidden technical keys: {leaked}")

    if candidate.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version mismatch: {candidate.get('schema_version')!r}")
    if candidate.get("source") != "Clear_JSON.engine_decision_preview":
        errors.append("source must be Clear_JSON.engine_decision_preview.")
    if candidate.get("status") != "ok":
        errors.append("status must be ok.")
    if candidate.get("action") not in VALID_CANDIDATE_ACTIONS:
        errors.append(f"invalid action: {candidate.get('action')!r}")
    if not isinstance(candidate.get("target_button_classes"), list) or not candidate.get("target_button_classes"):
        errors.append("target_button_classes must be a non-empty list.")
    if candidate.get("dry_run_safe") is not True:
        errors.append("dry_run_safe must be True.")
    if candidate.get("solver_stub") is not False:
        errors.append("solver_stub must be False for solver candidate.")
    if not isinstance(candidate.get("decision_context"), dict):
        errors.append("decision_context must be an object.")

    return {"ok": not errors, "errors": errors, "warnings": warnings}
