from __future__ import annotations

from display_analysis_cycle import _is_v31_confirmed_real_click_for_final_publication


def _state(*, gate_status="CONTROLLED_LIVE_CLICK_GATE_PASSED", success_status="CONTROLLED_LIVE_CLICK_SUCCESS_RECORDED", roi_ok=True, inside=True):
    return {
        "runtime_action": {
            "action_button": {
                "controlled_live_click_gate": {
                    "schema_version": "controlled_live_click_gate_v3_1",
                    "status": gate_status,
                    "scope_passed": gate_status == "CONTROLLED_LIVE_CLICK_GATE_PASSED",
                    "full_screen_search_blocked": True,
                },
                "controlled_live_click_success": {
                    "schema_version": "controlled_live_click_gate_v3_1",
                    "status": success_status,
                    "decision_id": "decision_1",
                },
                "action_button_slot_roi_guard": {
                    "schema_version": "action_button_slot_roi_runtime_audit_v2_6",
                    "ok": roi_ok,
                    "full_screen_search_blocked": True,
                },
                "click_points": [
                    {"class_name": "FOLD", "inside_slot_bbox": inside},
                ],
            }
        }
    }


def _clicked():
    return {
        "status": "clicked",
        "branch": "action_button",
        "action": "fold",
        "dry_run": False,
        "real_click_enabled": True,
        "guard_passed": True,
        "decision_id": "decision_1",
    }


def test_v31_confirmed_real_click_allows_final_publication_override():
    assert _is_v31_confirmed_real_click_for_final_publication(
        state=_state(),
        click_result=_clicked(),
    ) is True
    print("[OK] test_v31_confirmed_real_click_allows_final_publication_override")


def test_dry_run_does_not_use_real_click_override():
    click = _clicked()
    click["dry_run"] = True
    assert _is_v31_confirmed_real_click_for_final_publication(
        state=_state(),
        click_result=click,
    ) is False
    print("[OK] test_dry_run_does_not_use_real_click_override")


def test_blocked_gate_does_not_use_override():
    assert _is_v31_confirmed_real_click_for_final_publication(
        state=_state(gate_status="CONTROLLED_LIVE_CLICK_GATE_BLOCKED"),
        click_result=_clicked(),
    ) is False
    print("[OK] test_blocked_gate_does_not_use_override")


def test_outside_slot_does_not_use_override():
    assert _is_v31_confirmed_real_click_for_final_publication(
        state=_state(inside=False),
        click_result=_clicked(),
    ) is False
    print("[OK] test_outside_slot_does_not_use_override")


def main() -> int:
    tests = [
        test_v31_confirmed_real_click_allows_final_publication_override,
        test_dry_run_does_not_use_real_click_override,
        test_blocked_gate_does_not_use_override,
        test_outside_slot_does_not_use_override,
    ]
    for test in tests:
        test()
    print("[RESULT] OK: PokerVision V3.3 final Clear_JSON real-click publication tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
