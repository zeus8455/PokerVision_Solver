from __future__ import annotations

"""
audit_v236_preflop_arming_runtime_diagnostic_activation.py

PokerVision Solver V2.3.6 — runtime-like diagnostic activation audit.

Purpose:
- Build synthetic runtime-like preflop candidates.
- Activate V22 arming with explicit controlled token.
- Prove armed=True is possible only as diagnostic arming.
- Prove arming does not enable real-click/click execution.
"""

from collections import Counter
from typing import Any, Dict

from logic.v22_preflop_controlled_real_click_arming_gate import (
    build_v22_preflop_controlled_real_click_arming_gate,
    validate_v22_preflop_controlled_real_click_arming_gate_report,
)


def _candidate(*, action: str, target_sequence: list[str], allowed_kind: str, table_id: str = "table_01") -> Dict[str, Any]:
    return {
        "source": "Solver_Action_Decision_Candidate_JSON",
        "runtime_branch": "action_button",
        "planned_action": action,
        "target_sequence": target_sequence,
        "real_click_enabled": False,
        "dry_run": True,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "allowed_kind": allowed_kind,
        "table_id": table_id,
        "decision_context": {
            "street": "preflop",
            "table_id": table_id,
        },
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": allowed_kind,
            "street": "preflop",
            "real_click_enabled": False,
        },
    }


def _build_report(candidate: Dict[str, Any], *, token: bool = True) -> Dict[str, Any]:
    return build_v22_preflop_controlled_real_click_arming_gate(
        candidate,
        allowed_table_ids=["table_01"],
        slot_bbox_guard_ok=True,
        no_repeat_guard_ok=True,
        button_availability_guard_ok=True,
        export_validator_ok=True,
        explicit_controlled_real_click_token=token,
    )


def audit() -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []

    candidates = [
        _candidate(action="fold", target_sequence=["FOLD"], allowed_kind="simple_preflop_action"),
        _candidate(action="call", target_sequence=["Call"], allowed_kind="simple_preflop_action"),
        _candidate(action="bet_raise", target_sequence=["98%", "Bet/Raise"], allowed_kind="preflop_raise_98_sequence"),
    ]

    for idx, candidate in enumerate(candidates):
        report = _build_report(candidate, token=True)
        validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

        counters["candidate_checked"] += 1

        if validation.get("ok") is True:
            counters["validation_ok"] += 1
        else:
            errors.append({"idx": idx, "reason": "validation_failed", "validation": validation})

        if report.get("ok") is True:
            counters["report_ok"] += 1
        else:
            errors.append({"idx": idx, "reason": "report_not_ok", "report": report})

        if report.get("armed") is True:
            counters["armed_true"] += 1
        else:
            errors.append({"idx": idx, "reason": "armed_not_true", "report": report})

        if report.get("diagnostic_only") is True:
            counters["diagnostic_only_true"] += 1
        else:
            errors.append({"idx": idx, "reason": "diagnostic_only_not_true"})

        if report.get("does_not_enable_real_click") is True:
            counters["does_not_enable_real_click_true"] += 1
        else:
            errors.append({"idx": idx, "reason": "does_not_enable_real_click_not_true"})

        if report.get("candidate_real_click_enabled") is True:
            counters["candidate_real_click_enabled_true"] += 1
            errors.append({"idx": idx, "reason": "candidate_real_click_enabled_true_forbidden"})

        examples.append({
            "idx": idx,
            "action": candidate.get("planned_action"),
            "sequence": candidate.get("target_sequence"),
            "allowed_kind": candidate.get("allowed_kind"),
            "armed": report.get("armed"),
            "diagnostic_only": report.get("diagnostic_only"),
            "does_not_enable_real_click": report.get("does_not_enable_real_click"),
            "candidate_real_click_enabled": report.get("candidate_real_click_enabled"),
            "reason": report.get("reason"),
        })

    blocked = _build_report(candidates[0], token=False)
    counters["missing_token_checked"] += 1
    if blocked.get("armed") is False and blocked.get("ok") is False:
        counters["missing_token_blocked"] += 1
    else:
        errors.append({"reason": "missing_token_did_not_block", "report": blocked})

    ok = (
        counters.get("candidate_checked", 0) == 3
        and counters.get("armed_true", 0) == 3
        and counters.get("candidate_real_click_enabled_true", 0) == 0
        and counters.get("missing_token_blocked", 0) == 1
        and not errors
    )

    return {
        "schema_version": "v236_preflop_arming_runtime_diagnostic_activation_audit_v1",
        "ok": ok,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "counters": dict(counters),
        "errors": errors,
        "examples": examples,
        "missing_token_report": blocked,
    }


def main() -> int:
    report = audit()

    print("V2.3.6 PREFLOP ARMING RUNTIME DIAGNOSTIC ACTIVATION AUDIT")
    print("=" * 100)

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("EXAMPLES:")
    for item in report["examples"]:
        print(
            f"  idx={item['idx']} action={item['action']} kind={item['allowed_kind']} "
            f"seq={item['sequence']} armed={item['armed']} "
            f"candidate_real_click={item['candidate_real_click_enabled']} "
            f"reason={item['reason']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.3.6 preflop arming runtime diagnostic activation audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
