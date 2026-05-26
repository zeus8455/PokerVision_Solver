from __future__ import annotations

"""
audit_v221_preflop_arming_gate_export_audit.py

PokerVision Solver V2.2.1 — audit V2.2 arming gate over V2.1.4 exported candidates.

Modes:
1) no explicit controlled token -> every candidate must be blocked.
2) synthetic explicit token + guards OK -> every valid exported candidate must be armed.

Diagnostic-only.
Does not enable real-click.
Does not execute clicks.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from logic.v22_preflop_controlled_real_click_arming_gate import (
    build_v22_preflop_controlled_real_click_arming_gate,
    validate_v22_preflop_controlled_real_click_arming_gate_report,
)


EXPORT_PATH = Path(
    r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\reports\v214_preflop_real_click_candidates.json"
)


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _infer_table_id_from_candidate(candidate: Dict[str, Any]) -> str:
    ctx = candidate.get("decision_context") if isinstance(candidate.get("decision_context"), dict) else {}
    table_id = str(ctx.get("table_id") or candidate.get("table_id") or "")
    if table_id:
        return table_id

    source_path = str(candidate.get("source_runtime_plan_path") or "")
    parts = source_path.replace("\\", "/").split("/")
    for part in parts:
        if part.startswith("table_"):
            return part

    return ""


def audit(path: Path = EXPORT_PATH) -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []

    payload = _read_json(path)
    if payload is None:
        return {
            "schema_version": "v221_preflop_arming_gate_export_audit_v1",
            "ok": False,
            "path": str(path),
            "counters": {},
            "errors": [{"reason": "export_missing_or_unreadable", "path": str(path)}],
            "examples": [],
        }

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        candidates = []

    counters["candidate_total"] = len(candidates)

    for idx, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            counters["candidate_not_object"] += 1
            errors.append({"index": idx, "reason": "candidate_not_object"})
            continue

        counters["candidate_checked"] += 1

        candidate_for_gate = dict(candidate)
        decision_context = candidate_for_gate.get("decision_context") if isinstance(candidate_for_gate.get("decision_context"), dict) else {}
        decision_context = dict(decision_context)

        inferred_table_id = _infer_table_id_from_candidate(candidate_for_gate)
        if inferred_table_id and not decision_context.get("table_id"):
            decision_context["table_id"] = inferred_table_id
            candidate_for_gate["decision_context"] = decision_context
            counters["table_id_enriched_from_source_path_total"] += 1

        resolved_table_id = str(decision_context.get("table_id") or "")
        if resolved_table_id:
            counters["table_id_resolved_total"] += 1
        else:
            counters["table_id_missing_for_synthetic_arming_total"] += 1

        no_token_report = build_v22_preflop_controlled_real_click_arming_gate(
            candidate_for_gate,
            required_table_id="table_01",
            slot_bbox_guard_ok=True,
            no_repeat_guard_ok=True,
            button_availability_guard_ok=True,
            export_validator_ok=True,
            explicit_controlled_real_click_token=False,
        )
        no_token_validation = validate_v22_preflop_controlled_real_click_arming_gate_report(no_token_report)

        if no_token_report.get("armed") is False and "explicit_controlled_real_click_token_missing" in (no_token_report.get("errors") or []):
            counters["blocked_without_token_total"] += 1
        else:
            errors.append({
                "index": idx,
                "reason": "candidate_not_blocked_without_explicit_token",
                "report": no_token_report,
            })

        if no_token_validation.get("ok") is not True:
            errors.append({
                "index": idx,
                "reason": "no_token_report_validation_failed",
                "validation": no_token_validation,
            })

        token_report = build_v22_preflop_controlled_real_click_arming_gate(
            candidate_for_gate,
            required_table_id="table_01",
            slot_bbox_guard_ok=True,
            no_repeat_guard_ok=True,
            button_availability_guard_ok=True,
            export_validator_ok=True,
            explicit_controlled_real_click_token=True,
        )
        token_validation = validate_v22_preflop_controlled_real_click_arming_gate_report(token_report)

        if token_report.get("armed") is True and token_report.get("ok") is True:
            counters["armed_with_synthetic_token_total"] += 1
        elif not resolved_table_id and "table_id_missing" in (token_report.get("errors") or []):
            counters["blocked_with_synthetic_token_due_to_missing_table_id_total"] += 1
        else:
            errors.append({
                "index": idx,
                "reason": "candidate_not_armed_with_synthetic_token",
                "report": token_report,
            })

        if token_validation.get("ok") is not True:
            errors.append({
                "index": idx,
                "reason": "token_report_validation_failed",
                "validation": token_validation,
            })

        if token_report.get("candidate_real_click_enabled") is True:
            errors.append({
                "index": idx,
                "reason": "armed_report_candidate_real_click_enabled_true_forbidden",
                "report": token_report,
            })

        if len(examples) < 20:
            examples.append({
                "index": idx,
                "action": candidate.get("planned_action"),
                "allowed_kind": candidate.get("allowed_kind"),
                "target_sequence": candidate.get("target_sequence"),
                "no_token_armed": no_token_report.get("armed"),
                "no_token_errors": no_token_report.get("errors"),
                "token_armed": token_report.get("armed"),
                "token_reason": token_report.get("reason"),
                "candidate_real_click_enabled": token_report.get("candidate_real_click_enabled"),
            })

    ok = (
        counters.get("candidate_total", 0) > 0
        and counters.get("candidate_checked", 0) == counters.get("candidate_total", 0)
        and counters.get("blocked_without_token_total", 0) == counters.get("candidate_total", 0)
        and counters.get("armed_with_synthetic_token_total", 0) == counters.get("table_id_resolved_total", 0)
        and counters.get("blocked_with_synthetic_token_due_to_missing_table_id_total", 0) == counters.get("table_id_missing_for_synthetic_arming_total", 0)
        and not errors
    )

    return {
        "schema_version": "v221_preflop_arming_gate_export_audit_v1",
        "ok": ok,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "path": str(path),
        "counters": dict(counters),
        "errors": errors,
        "examples": examples,
    }


def main() -> int:
    report = audit()

    print("V2.2.1 PREFLOP ARMING GATE EXPORT AUDIT")
    print("=" * 100)
    print("PATH =", report["path"])

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("EXAMPLES:")
    for item in report["examples"][:20]:
        print(
            f"  idx={item['index']} action={item['action']} kind={item['allowed_kind']} "
            f"seq={item['target_sequence']} no_token_armed={item['no_token_armed']} "
            f"token_armed={item['token_armed']} real_click={item['candidate_real_click_enabled']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:30]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.2.1 preflop arming gate export audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
