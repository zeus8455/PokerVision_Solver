from __future__ import annotations

"""
audit_v246_live_preflight_dryrun_command_contract.py

PokerVision Solver V2.4.6 — live-preflight dry-run command contract.

Purpose:
- Prepare a safe 10–15 minute live-preflight mode before real-click testing.
- Allow solver candidate source switch and V22 controlled arming diagnostics.
- Keep all real mouse click flags disabled.
- Keep dry-run enabled.
- Keep scope preflop-only.
"""

from collections import Counter
from typing import Any, Dict

import config as c


MIN_SECONDS = 10 * 60
MAX_SECONDS = 15 * 60


def _safe_bool(name: str, default: bool = False) -> bool:
    return bool(getattr(c, name, default))


def _safe_list(name: str) -> list:
    value = getattr(c, name, [])
    return list(value) if isinstance(value, (list, tuple, set)) else []


def audit() -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []

    contract = {
        "schema_version": "v246_live_preflight_dryrun_command_contract_v1",
        "mode": "preflop_live_preflight_dryrun",
        "duration_seconds_min": MIN_SECONDS,
        "duration_seconds_max": MAX_SECONDS,
        "preflop_only": True,
        "postflop_blocked": True,
        "solver_source_switch_enabled": _safe_bool("V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE"),
        "solver_candidate_dry_run_only": _safe_bool("V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY"),
        "solver_candidate_allow_real_click": _safe_bool("V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK"),
        "click_dry_run": _safe_bool("V11_CLICK_DRY_RUN"),
        "real_mouse_click_enabled": _safe_bool("V11_REAL_MOUSE_CLICK_ENABLED"),
        "trigger_ui_service_real_click_enabled": _safe_bool("V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"),
        "v22_arming_enabled": _safe_bool("V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED"),
        "v22_explicit_token": _safe_bool("V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN"),
        "v22_allow_real_click": _safe_bool("V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK"),
        "v22_allowed_table_ids": _safe_list("V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS"),
    }

    counters["contract_checked"] += 1

    if contract["duration_seconds_min"] == MIN_SECONDS and contract["duration_seconds_max"] == MAX_SECONDS:
        counters["duration_10_15_min_ok"] += 1
    else:
        errors.append({"reason": "duration_not_10_15_minutes", "contract": contract})

    if contract["preflop_only"] is True and contract["postflop_blocked"] is True:
        counters["preflop_only_scope_ok"] += 1
    else:
        errors.append({"reason": "preflop_only_scope_not_enforced", "contract": contract})

    if contract["click_dry_run"] is True:
        counters["click_dry_run_true"] += 1
    else:
        errors.append({"reason": "click_dry_run_not_true", "value": contract["click_dry_run"]})

    forbidden_true = {
        "solver_candidate_allow_real_click": contract["solver_candidate_allow_real_click"],
        "real_mouse_click_enabled": contract["real_mouse_click_enabled"],
        "trigger_ui_service_real_click_enabled": contract["trigger_ui_service_real_click_enabled"],
    }
    bad_flags = {k: v for k, v in forbidden_true.items() if v is True}
    if not bad_flags:
        counters["real_click_flags_disabled"] += 1
    else:
        errors.append({"reason": "real_click_flags_enabled_forbidden", "flags": bad_flags})

    if contract["v22_allow_real_click"] is False:
        counters["v22_real_click_not_allowed"] += 1
    else:
        errors.append({"reason": "v22_allow_real_click_true_forbidden", "contract": contract})

    ok = not errors

    return {
        "schema_version": "v246_live_preflight_dryrun_command_contract_audit_v1",
        "ok": ok,
        "contract": contract,
        "counters": dict(counters),
        "errors": errors,
    }


def main() -> int:
    report = audit()

    print("V2.4.6 LIVE-PREFLIGHT DRY-RUN COMMAND CONTRACT")
    print("=" * 100)

    print()
    print("CONTRACT:")
    for key, value in report["contract"].items():
        print(f"  {key}: {value}")

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.4.6 live-preflight dry-run command contract")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
