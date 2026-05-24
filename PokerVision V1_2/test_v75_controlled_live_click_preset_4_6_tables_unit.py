from __future__ import annotations

from logic.real_click_readiness import validate_real_click_readiness


ALLOWED_TABLES_6 = [
    "table_01",
    "table_02",
    "table_03",
    "table_04",
    "table_05",
    "table_06",
]

ALLOWED_ACTIONS = ["fold", "check", "call", "check_fold"]
ALLOWED_BUTTONS = ["FOLD", "Check", "Call", "Check/fold"]


def _controlled_snapshot(*, allowed_tables=None, max_clicks: int = 6) -> dict:
    if allowed_tables is None:
        allowed_tables = list(ALLOWED_TABLES_6)

    return {
        "V10_REAL_CLICK_READINESS_SCHEMA_VERSION": "real_click_readiness_v1",
        "V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED": True,
        "V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG": True,
        "V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY": True,
        "V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED": True,
        "V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED": True,
        "V10_REAL_CLICK_REQUIRE_MASTER_ARMED": True,
        "V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED": True,
        "V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED": True,
        "V09_CLICK_EXECUTION_GUARD_ENABLED": True,
        "V09_REAL_CLICK_MASTER_ARMED": True,
        "V09_REQUIRE_SLOT_BOUNDARY_GUARD": True,
        "V09_REQUIRE_NO_REPEAT_DECISION_GUARD": True,
        "V09_REQUIRE_BUTTON_AVAILABILITY_GUARD": True,
        "V09_REQUIRE_ACTION_RUNTIME_PLAN_SOURCE": "Action_Runtime_Plan_JSON",
        "V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK": True,
        "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": False,
        "V11_REAL_MOUSE_CLICK_ENABLED": True,
        "V11_CLICK_DRY_RUN": False,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
        "V11_TRIGGER_UI_SERVICE_DRY_RUN": True,

        # V7.5 review-only preset fields. They do not mutate config.py.
        "V75_CONTROLLED_LIVE_CLICK_PRESET_AVAILABLE": True,
        "V75_CONTROLLED_LIVE_CLICK_TABLE_IDS": list(allowed_tables),
        "V75_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": max_clicks,
        "V75_CONTROLLED_LIVE_CLICK_ACTION_BUTTON_ONLY": True,
        "V75_CONTROLLED_LIVE_CLICK_SERVICE_BRANCH_DISABLED": True,
        "V75_CONTROLLED_LIVE_CLICK_RAISE_BRANCH_ENABLED": False,
        "V75_CONTROLLED_LIVE_CLICK_REQUIRE_SCOPE_AUDIT": True,
        "V75_CONTROLLED_LIVE_CLICK_ALLOWED_ACTIONS": list(ALLOWED_ACTIONS),
        "V75_CONTROLLED_LIVE_CLICK_ALLOWED_BUTTONS": list(ALLOWED_BUTTONS),
    }


def _evaluate_v75_scope(snapshot: dict) -> dict:
    readiness = validate_real_click_readiness(snapshot)
    errors = []

    tables = list(snapshot.get("V75_CONTROLLED_LIVE_CLICK_TABLE_IDS") or [])
    max_clicks = int(snapshot.get("V75_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN") or -1)

    if tables != ALLOWED_TABLES_6:
        errors.append("allowed_tables_must_be_table_01_to_table_06")
    if not (4 <= max_clicks <= 6):
        errors.append("max_clicks_per_run_must_be_4_to_6")
    if snapshot.get("V75_CONTROLLED_LIVE_CLICK_ALLOWED_ACTIONS") != ALLOWED_ACTIONS:
        errors.append("allowed_actions_must_be_fold_check_call_check_fold")
    if snapshot.get("V75_CONTROLLED_LIVE_CLICK_ALLOWED_BUTTONS") != ALLOWED_BUTTONS:
        errors.append("allowed_buttons_must_be_FOLD_Check_Call_CheckFold")
    if snapshot.get("V75_CONTROLLED_LIVE_CLICK_ACTION_BUTTON_ONLY") is not True:
        errors.append("action_button_only_must_be_true")
    if snapshot.get("V75_CONTROLLED_LIVE_CLICK_SERVICE_BRANCH_DISABLED") is not True:
        errors.append("service_branch_disabled_must_be_true")
    if snapshot.get("V75_CONTROLLED_LIVE_CLICK_RAISE_BRANCH_ENABLED") is not False:
        errors.append("raise_branch_enabled_must_be_false")
    if snapshot.get("V75_CONTROLLED_LIVE_CLICK_REQUIRE_SCOPE_AUDIT") is not True:
        errors.append("scope_audit_must_be_required")

    ready = bool(readiness.real_click_ready and not readiness.errors and not errors)

    return {
        "ready": ready,
        "readiness_status": readiness.status,
        "readiness_errors": list(readiness.errors),
        "scope_errors": errors,
        "tables": tables,
        "max_clicks_per_run": max_clicks,
    }


def test_v75_six_table_controlled_live_click_preset_is_ready() -> None:
    snapshot = _controlled_snapshot()
    report = _evaluate_v75_scope(snapshot)

    assert report["ready"] is True, report
    assert report["readiness_status"] == "ready_for_controlled_real_click"
    assert report["scope_errors"] == []
    assert report["tables"] == ALLOWED_TABLES_6
    assert report["max_clicks_per_run"] == 6


def test_v75_four_click_lower_bound_is_allowed() -> None:
    snapshot = _controlled_snapshot(max_clicks=4)
    report = _evaluate_v75_scope(snapshot)

    assert report["ready"] is True, report
    assert report["max_clicks_per_run"] == 4


def test_v75_three_click_limit_is_blocked() -> None:
    snapshot = _controlled_snapshot(max_clicks=3)
    report = _evaluate_v75_scope(snapshot)

    assert report["ready"] is False
    assert "max_clicks_per_run_must_be_4_to_6" in report["scope_errors"]


def test_v75_missing_table_is_blocked() -> None:
    snapshot = _controlled_snapshot(allowed_tables=ALLOWED_TABLES_6[:5])
    report = _evaluate_v75_scope(snapshot)

    assert report["ready"] is False
    assert "allowed_tables_must_be_table_01_to_table_06" in report["scope_errors"]


def test_v75_service_real_click_is_blocked() -> None:
    snapshot = _controlled_snapshot()
    snapshot["V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"] = True
    snapshot["V11_TRIGGER_UI_SERVICE_DRY_RUN"] = False

    report = _evaluate_v75_scope(snapshot)

    assert report["ready"] is False
    assert "service_real_click_disabled" in report["readiness_errors"]
    assert "service_dry_run_enabled" in report["readiness_errors"]


def test_v75_raise_branch_is_blocked() -> None:
    snapshot = _controlled_snapshot()
    snapshot["V75_CONTROLLED_LIVE_CLICK_RAISE_BRANCH_ENABLED"] = True

    report = _evaluate_v75_scope(snapshot)

    assert report["ready"] is False
    assert "raise_branch_enabled_must_be_false" in report["scope_errors"]


def main() -> int:
    tests = [
        test_v75_six_table_controlled_live_click_preset_is_ready,
        test_v75_four_click_lower_bound_is_allowed,
        test_v75_three_click_limit_is_blocked,
        test_v75_missing_table_is_blocked,
        test_v75_service_real_click_is_blocked,
        test_v75_raise_branch_is_blocked,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V7.5 controlled live-click preset 4-6 table tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
