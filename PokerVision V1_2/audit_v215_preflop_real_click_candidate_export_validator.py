from __future__ import annotations

"""
audit_v215_preflop_real_click_candidate_export_validator.py

PokerVision Solver V2.1.5 — validate V2.1.4 preflop real-click candidate export.

Validates reports/v214_preflop_real_click_candidates.json as a strict no-click contract.

Diagnostic-only.
Does not enable or execute real clicks.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


DEFAULT_EXPORT_PATH = Path(
    r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\reports\v214_preflop_real_click_candidates.json"
)

ALLOWED_KINDS = {"simple_preflop_action", "preflop_raise_98_sequence"}
ALLOWED_SIMPLE_ACTIONS = {"fold", "call", "check", "check_fold"}
RAISE_SEQUENCE = ["98%", "Bet/Raise"]


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def validate_export(path: Path = DEFAULT_EXPORT_PATH) -> Dict[str, Any]:
    errors: list[dict[str, Any]] = []
    counters = Counter()
    action_counter = Counter()
    allowed_kind_counter = Counter()

    if not path.exists():
        return {
            "schema_version": "v215_preflop_real_click_candidate_export_validator_v1",
            "ok": False,
            "path": str(path),
            "counters": {},
            "action_counter": {},
            "allowed_kind_counter": {},
            "errors": [{"reason": "export_file_missing", "path": str(path)}],
        }

    payload = _read_json(path)
    if payload is None:
        return {
            "schema_version": "v215_preflop_real_click_candidate_export_validator_v1",
            "ok": False,
            "path": str(path),
            "counters": {},
            "action_counter": {},
            "allowed_kind_counter": {},
            "errors": [{"reason": "export_file_unreadable_or_not_object", "path": str(path)}],
        }

    counters["export_file_present"] += 1

    if payload.get("schema_version") != "v214_preflop_real_click_candidate_export_v1":
        errors.append({"reason": "export_schema_version_mismatch", "value": payload.get("schema_version")})

    if payload.get("ok") is not True:
        errors.append({"reason": "export_ok_not_true", "value": payload.get("ok")})

    if payload.get("diagnostic_only") is not True:
        errors.append({"reason": "export_diagnostic_only_not_true"})

    if payload.get("does_not_enable_real_click") is not True:
        errors.append({"reason": "export_does_not_enable_real_click_not_true"})

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append({"reason": "candidates_missing_or_empty"})
        candidates = []

    counters["candidate_total"] = len(candidates)

    for idx, item in enumerate(candidates):
        if not isinstance(item, dict):
            errors.append({"index": idx, "reason": "candidate_not_object"})
            continue

        counters["candidate_checked"] += 1

        action = str(item.get("planned_action") or "")
        allowed_kind = item.get("allowed_kind")
        target_sequence = item.get("target_sequence") if isinstance(item.get("target_sequence"), list) else []
        v21 = item.get("v21_preflight") if isinstance(item.get("v21_preflight"), dict) else {}

        table_id = str(item.get("table_id") or "")
        decision_context = item.get("decision_context") if isinstance(item.get("decision_context"), dict) else {}
        decision_context_table_id = str(decision_context.get("table_id") or "")

        if not table_id:
            errors.append({"index": idx, "reason": "candidate_table_id_missing"})

        if not decision_context_table_id:
            errors.append({"index": idx, "reason": "candidate_decision_context_table_id_missing"})

        if table_id and decision_context_table_id and table_id != decision_context_table_id:
            errors.append({
                "index": idx,
                "reason": "candidate_table_id_mismatch",
                "table_id": table_id,
                "decision_context_table_id": decision_context_table_id,
            })

        action_counter[action] += 1
        allowed_kind_counter[allowed_kind] += 1

        if item.get("schema_version") != "v214_preflop_real_click_candidate_v1":
            errors.append({"index": idx, "reason": "candidate_schema_version_mismatch"})

        if item.get("diagnostic_only") is not True:
            errors.append({"index": idx, "reason": "candidate_diagnostic_only_not_true"})

        if item.get("does_not_enable_real_click") is not True:
            errors.append({"index": idx, "reason": "candidate_does_not_enable_real_click_not_true"})

        if item.get("real_click_enabled") is not False:
            errors.append({"index": idx, "reason": "candidate_real_click_enabled_not_false", "value": item.get("real_click_enabled")})

        if item.get("dry_run") is not True:
            errors.append({"index": idx, "reason": "candidate_dry_run_not_true", "value": item.get("dry_run")})

        if allowed_kind not in ALLOWED_KINDS:
            errors.append({"index": idx, "reason": "candidate_allowed_kind_unsupported", "value": allowed_kind})

        if allowed_kind == "simple_preflop_action" and action not in ALLOWED_SIMPLE_ACTIONS:
            errors.append({"index": idx, "reason": "simple_action_unsupported", "action": action})

        if allowed_kind == "preflop_raise_98_sequence":
            if action != "bet_raise":
                errors.append({"index": idx, "reason": "raise_candidate_action_not_bet_raise", "action": action})
            if target_sequence != RAISE_SEQUENCE:
                errors.append({"index": idx, "reason": "raise_candidate_sequence_mismatch", "target_sequence": target_sequence})

        if v21.get("ok") is not True or v21.get("allowed") is not True:
            errors.append({"index": idx, "reason": "candidate_v21_preflight_not_ok_or_allowed", "v21": v21})

        if v21.get("real_click_enabled") is not False:
            errors.append({"index": idx, "reason": "candidate_v21_real_click_enabled_not_false", "value": v21.get("real_click_enabled")})

    return {
        "schema_version": "v215_preflop_real_click_candidate_export_validator_v1",
        "ok": not errors,
        "path": str(path),
        "counters": dict(counters),
        "action_counter": dict(action_counter),
        "allowed_kind_counter": dict(allowed_kind_counter),
        "errors": errors,
    }


def main() -> int:
    report = validate_export()

    print("V2.1.5 PREFLOP REAL-CLICK CANDIDATE EXPORT VALIDATOR")
    print("=" * 100)
    print("PATH =", report["path"])

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("ACTION_COUNTER:", report["action_counter"])
    print("ALLOWED_KIND_COUNTER:", report["allowed_kind_counter"])

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:30]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.1.5 preflop real-click candidate export validator")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
