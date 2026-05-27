from __future__ import annotations

"""
audit_v238_config_driven_arming_activation.py

PokerVision Solver V2.3.8 — config-driven synthetic arming activation audit.

Purpose:
- Prove config flags control V22 arming activation.
- Default config keeps arming blocked.
- Controlled-on config can produce armed=True for a valid preflop candidate.
- Real-click is still not enabled by this diagnostic arming gate.
"""

from collections import Counter
from typing import Any, Dict

import config as c

from logic.v22_preflop_controlled_real_click_arming_gate import (
    build_v22_preflop_controlled_real_click_arming_gate,
    validate_v22_preflop_controlled_real_click_arming_gate_report,
)


def _candidate() -> Dict[str, Any]:
    return {
        "source": "Solver_Action_Decision_Candidate_JSON",
        "runtime_branch": "action_button",
        "planned_action": "bet_raise",
        "target_sequence": ["98%", "Bet/Raise"],
        "real_click_enabled": False,
        "dry_run": True,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "allowed_kind": "preflop_raise_98_sequence",
        "table_id": "table_01",
        "decision_context": {
            "street": "preflop",
            "table_id": "table_01",
        },
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": "preflop_raise_98_sequence",
            "street": "preflop",
            "real_click_enabled": False,
        },
    }


def _explicit_token_from_config() -> bool:
    return (
        bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED)
        and bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN)
        and bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK)
    )


def _report_from_config() -> Dict[str, Any]:
    return build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(),
        allowed_table_ids=list(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS),
        slot_bbox_guard_ok=bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_SLOT_GUARD),
        no_repeat_guard_ok=bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_NO_REPEAT_GUARD),
        button_availability_guard_ok=bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_BUTTON_AVAILABILITY),
        export_validator_ok=bool(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_EXPORT_VALIDATOR),
        explicit_controlled_real_click_token=_explicit_token_from_config(),
    )


def _snapshot() -> Dict[str, Any]:
    return {
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS": list(c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_SLOT_GUARD": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_SLOT_GUARD,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_NO_REPEAT_GUARD": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_NO_REPEAT_GUARD,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_BUTTON_AVAILABILITY": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_BUTTON_AVAILABILITY,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_EXPORT_VALIDATOR": c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_EXPORT_VALIDATOR,
    }


def _restore(snapshot: Dict[str, Any]) -> None:
    for name, value in snapshot.items():
        setattr(c, name, value)


def _set_default_safe() -> None:
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED = False
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN = False
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK = False
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS = []


def _set_controlled_on() -> None:
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED = True
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN = True
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK = True
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS = ["table_01"]
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_SLOT_GUARD = True
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_NO_REPEAT_GUARD = True
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_BUTTON_AVAILABILITY = True
    c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_EXPORT_VALIDATOR = True


def audit() -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    original = _snapshot()

    try:
        _set_default_safe()
        default_report = _report_from_config()
        counters["default_checked"] += 1
        if default_report.get("armed") is False and default_report.get("ok") is False:
            counters["default_blocked"] += 1
        else:
            errors.append({"reason": "default_config_did_not_block", "report": default_report})

        _set_controlled_on()
        controlled_report = _report_from_config()
        controlled_validation = validate_v22_preflop_controlled_real_click_arming_gate_report(controlled_report)

        counters["controlled_checked"] += 1
        if controlled_validation.get("ok") is True:
            counters["controlled_validation_ok"] += 1
        else:
            errors.append({"reason": "controlled_validation_failed", "validation": controlled_validation})

        if controlled_report.get("armed") is True and controlled_report.get("ok") is True:
            counters["controlled_armed_true"] += 1
        else:
            errors.append({"reason": "controlled_config_not_armed", "report": controlled_report})

        if controlled_report.get("does_not_enable_real_click") is True:
            counters["does_not_enable_real_click_true"] += 1
        else:
            errors.append({"reason": "does_not_enable_real_click_not_true", "report": controlled_report})

        if controlled_report.get("candidate_real_click_enabled") is False:
            counters["candidate_real_click_false"] += 1
        else:
            errors.append({"reason": "candidate_real_click_not_false", "report": controlled_report})

        c.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN = False
        missing_token_report = _report_from_config()
        counters["missing_token_checked"] += 1
        if missing_token_report.get("armed") is False:
            counters["missing_token_blocked"] += 1
        else:
            errors.append({"reason": "missing_token_did_not_block", "report": missing_token_report})

        examples.extend([
            {
                "mode": "default_safe",
                "armed": default_report.get("armed"),
                "ok": default_report.get("ok"),
                "reason": default_report.get("reason"),
                "candidate_real_click_enabled": default_report.get("candidate_real_click_enabled"),
            },
            {
                "mode": "controlled_on",
                "armed": controlled_report.get("armed"),
                "ok": controlled_report.get("ok"),
                "reason": controlled_report.get("reason"),
                "candidate_real_click_enabled": controlled_report.get("candidate_real_click_enabled"),
            },
            {
                "mode": "missing_token",
                "armed": missing_token_report.get("armed"),
                "ok": missing_token_report.get("ok"),
                "reason": missing_token_report.get("reason"),
                "candidate_real_click_enabled": missing_token_report.get("candidate_real_click_enabled"),
            },
        ])

    finally:
        _restore(original)

    ok = (
        counters.get("default_blocked", 0) == 1
        and counters.get("controlled_armed_true", 0) == 1
        and counters.get("candidate_real_click_false", 0) == 1
        and counters.get("missing_token_blocked", 0) == 1
        and not errors
    )

    return {
        "schema_version": "v238_config_driven_arming_activation_audit_v1",
        "ok": ok,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "counters": dict(counters),
        "errors": errors,
        "examples": examples,
    }


def main() -> int:
    report = audit()

    print("V2.3.8 CONFIG-DRIVEN ARMING ACTIVATION AUDIT")
    print("=" * 100)

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("EXAMPLES:")
    for item in report["examples"]:
        print(
            f"  mode={item['mode']} armed={item['armed']} ok={item['ok']} "
            f"candidate_real_click={item['candidate_real_click_enabled']} reason={item['reason']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.3.8 config-driven arming activation audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
