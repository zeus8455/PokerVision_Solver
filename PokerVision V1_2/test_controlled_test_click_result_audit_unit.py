#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from controlled_test_click_result_audit import audit_controlled_test_click_result


def _valid_result():
    return {
        "schema_version": "controlled_test_click_runner_v1",
        "ready": True,
        "status": "CONTROLLED_TEST_CLICK_READY",
        "blockers": [],
        "test_environment": True,
        "manual_controlled_snapshot": True,
        "real_test_click_requested": True,
        "click_execution": "clicked_in_test_environment",
        "allowed_actions": ["fold", "check", "call", "check_fold"],
        "allowed_buttons": ["FOLD", "Check", "Call", "Check/fold"],
        "candidate": {
            "table_id": "table_01",
            "action": "fold",
            "button": "FOLD",
            "x": 100,
            "y": 100,
            "max_clicks_per_run": 1,
            "source": "manual_test_candidate",
        },
        "clicked": True,
        "click_result": {
            "backend": "pyautogui",
            "clicked": True,
            "x": 100,
            "y": 100,
        },
    }


def test_valid_controlled_test_click_result_passes():
    audit = audit_controlled_test_click_result(_valid_result())
    assert audit["ok"] is True
    assert audit["status"] == "CONTROLLED_TEST_CLICK_AUDIT_OK"
    assert audit["errors"] == []


def test_dry_run_candidate_is_rejected():
    data = _valid_result()
    data["real_test_click_requested"] = False
    data["click_execution"] = "dry_run_candidate_recorded"
    data["clicked"] = False
    data.pop("click_result", None)

    audit = audit_controlled_test_click_result(data)
    assert audit["ok"] is False
    assert "real_test_click_requested_must_be_true" in audit["errors"]
    assert "click_execution_must_be_clicked_in_test_environment" in audit["errors"]
    assert "clicked_must_be_true" in audit["errors"]


def test_wrong_table_is_rejected():
    data = _valid_result()
    data["candidate"]["table_id"] = "table_02"

    audit = audit_controlled_test_click_result(data)
    assert audit["ok"] is False
    assert "candidate_table_id_must_be_table_01" in audit["errors"]


def test_raise_button_is_rejected():
    data = _valid_result()
    data["candidate"]["action"] = "raise"
    data["candidate"]["button"] = "Raise"

    audit = audit_controlled_test_click_result(data)
    assert audit["ok"] is False
    assert "candidate_action_must_be_allowed_simple_action" in audit["errors"]
    assert "candidate_button_must_be_allowed_simple_button" in audit["errors"]


def test_coordinate_mismatch_is_rejected():
    data = _valid_result()
    data["click_result"]["x"] = 101

    audit = audit_controlled_test_click_result(data)
    assert audit["ok"] is False
    assert "click_result_coordinates_must_match_candidate" in audit["errors"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("[RESULT] OK: V1.7 controlled test-click result audit unit tests passed.")
