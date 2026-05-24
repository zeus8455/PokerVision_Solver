"""
test_action_runtime_plan_builder_unit.py
Unit tests for PokerVision V1.1.2 Action_Runtime_Plan_JSON builder with Action_Button_Runtime_Policy.
"""
from __future__ import annotations

from logic.action_runtime_plan_builder import (
    build_action_runtime_plan_from_action_decision,
    validate_action_runtime_plan_contract,
)


def _sample_action_decision(action: str = "fold", target_button_classes=None, size_policy=None) -> dict:
    if target_button_classes is None:
        if action == "fold":
            target_button_classes = ["FOLD"]
        elif action == "check":
            target_button_classes = ["Check"]
        elif action == "call":
            target_button_classes = ["Call"]
        elif action == "check_fold":
            target_button_classes = ["Check/fold"]
        elif action in {"raise", "bet"}:
            target_button_classes = ["98%", "Bet/Raise"]
        else:
            target_button_classes = ["FOLD"]
    return {
        "schema_version": "action_decision_v1",
        "source": "Decision_JSON",
        "source_decision_frame_id": "table_01_hand_01_preflop_01",
        "status": "ok",
        "action": action,
        "size_policy": size_policy,
        "target_button_classes": list(target_button_classes),
        "reason": "v06_stub_default_action",
        "dry_run_safe": True,
        "solver_stub": True,
        "decision_context": {
            "street": "preflop",
            "hero_position": "BB",
            "source_frame_id": "table_01_hand_01_preflop_01",
        },
    }


def _assert_valid(plan: dict) -> None:
    validation = validate_action_runtime_plan_contract(plan)
    assert validation["ok"], validation


def test_runtime_plan_built_from_action_decision_only() -> None:
    plan = build_action_runtime_plan_from_action_decision(_sample_action_decision("fold"))
    _assert_valid(plan)
    assert plan["source"] == "Action_Decision_JSON"
    assert plan["planned_action"] == "fold"
    assert plan["status"] == "ok"
    assert plan["policy_stage"] == "v1_1_simple_buttons_only"
    assert plan["policy_version"] == "v1.1.1_action_button_runtime_policy"
    assert plan["raise_branch_enabled"] is False
    assert plan["target_sequence"] == ["FOLD"]
    assert plan["target_sequences"] == [["FOLD"], ["Check/fold"]]
    assert plan["action_button_policy"]["ok"] is True
    assert plan["runtime_branch"] == "action_button"
    assert plan["real_click_enabled"] is False
    forbidden = {"runtime_action", "click_result", "click_points", "bbox", "confidence", "mouse"}
    assert not (forbidden & set(plan.keys()))


def test_check_plan_uses_policy_fallback() -> None:
    plan = build_action_runtime_plan_from_action_decision(_sample_action_decision("check"))
    _assert_valid(plan)
    assert plan["planned_action"] == "check"
    assert plan["target_sequence"] == ["Check"]
    assert plan["target_sequences"] == [["Check"], ["Check/fold"]]


def test_call_plan_uses_policy() -> None:
    plan = build_action_runtime_plan_from_action_decision(_sample_action_decision("call"))
    _assert_valid(plan)
    assert plan["planned_action"] == "call"
    assert plan["target_sequence"] == ["Call"]
    assert plan["target_sequences"] == [["Call"]]


def test_check_fold_plan_uses_safe_order() -> None:
    plan = build_action_runtime_plan_from_action_decision(_sample_action_decision("check_fold"))
    _assert_valid(plan)
    assert plan["planned_action"] == "check_fold"
    assert plan["target_sequence"] == ["Check"]
    assert plan["target_sequences"] == [["Check"], ["Check/fold"], ["FOLD"]]


def test_raise_branch_is_blocked_for_first_real_click_stage() -> None:
    plan = build_action_runtime_plan_from_action_decision(_sample_action_decision("raise", target_button_classes=["98%", "Bet/Raise"], size_policy={"pct": 98}))
    validation = validate_action_runtime_plan_contract(plan)
    assert validation["ok"], validation
    assert plan["status"] == "blocked"
    assert plan["planned_action"] == "bet_raise"
    assert plan["raise_branch_enabled"] is False
    assert plan["target_sequence"] == []
    assert plan["target_sequences"] == []
    assert plan["blocked_reason"] == "bet_raise_branch_disabled_for_v1_1_first_real_click_stage"
    assert plan["action_button_policy"]["ok"] is False


def test_invalid_action_decision_is_rejected() -> None:
    bad = _sample_action_decision("fold")
    bad["source"] = "Dark_JSON"
    try:
        build_action_runtime_plan_from_action_decision(bad)
    except ValueError as exc:
        assert "Action_Decision_JSON is not valid" in str(exc)
    else:
        raise AssertionError("invalid Action_Decision_JSON was accepted")


def test_runtime_plan_rejects_pollution() -> None:
    plan = build_action_runtime_plan_from_action_decision(_sample_action_decision("fold"))
    plan["click_points"] = [{"x": 1, "y": 2}]
    validation = validate_action_runtime_plan_contract(plan)
    assert not validation["ok"]
    assert any("forbidden" in msg for msg in validation["errors"])


def main() -> None:
    tests = [
        test_runtime_plan_built_from_action_decision_only,
        test_check_plan_uses_policy_fallback,
        test_call_plan_uses_policy,
        test_check_fold_plan_uses_safe_order,
        test_raise_branch_is_blocked_for_first_real_click_stage,
        test_invalid_action_decision_is_rejected,
        test_runtime_plan_rejects_pollution,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Action_Runtime_Plan_JSON unit tests passed.")


if __name__ == "__main__":
    main()
