from __future__ import annotations

"""
test_v208_preflop_runtime_raise_mapping_synthetic_unit.py

PokerVision Solver V2.0.8 — synthetic tests for preflop solver runtime raise mapping.

This test does not enable real-click.
It documents current safety behavior before preflop-only raise runtime enablement.
"""

from logic.solver_runtime_plan_candidate import (
    UNSUPPORTED_RAISE_WITHOUT_EXECUTABLE_SEQUENCE_REASON,
    UNSUPPORTED_RAISE_WITHOUT_SIZE_POLICY_REASON,
    build_solver_action_runtime_plan_candidate,
    validate_solver_action_runtime_plan_candidate,
)


def _candidate(action: str, *, size_policy=None, target_button_classes=None, reason="v208_synthetic"):
    if target_button_classes is None:
        if action == "fold":
            target_button_classes = ["FOLD"]
        elif action == "call":
            target_button_classes = ["Call"]
        elif action == "check":
            target_button_classes = ["Check"]
        elif action == "raise":
            target_button_classes = ["98%", "Bet/Raise"]
        else:
            target_button_classes = ["FOLD"]

    return {
        "schema_version": "solver_action_decision_candidate_v1",
        "source": "Clear_JSON.engine_decision_preview",
        "source_clear_frame_id": f"v208_{action}_synthetic",
        "status": "ok",
        "action": action,
        "size_policy": size_policy,
        "target_button_classes": list(target_button_classes),
        "reason": reason,
        "dry_run_safe": True,
        "solver_stub": False,
        "decision_id": f"decision_v208_{action}",
        "solver_fingerprint": f"fingerprint_v208_{action}",
        "decision_context": {
            "street": "preflop",
            "hero_position": "BB",
            "source_frame_id": f"v208_{action}_synthetic",
        },
    }


def test_fold_call_check_solver_candidates_build_runtime_plans():
    for action, expected_sequence in [
        ("fold", ["FOLD"]),
        ("call", ["Call"]),
        ("check", ["Check"]),
    ]:
        plan = build_solver_action_runtime_plan_candidate(_candidate(action))
        validation = validate_solver_action_runtime_plan_candidate(plan)

        assert validation["ok"], validation
        assert plan["status"] == "ok"
        assert plan["planned_action"] == action
        assert plan["target_sequence"] == expected_sequence
        assert plan["dry_run"] is True
        assert plan["real_click_enabled"] is False
        assert plan["does_not_enable_real_click"] is True


def test_preflop_raise_without_size_policy_is_rejected():
    try:
        build_solver_action_runtime_plan_candidate(
            _candidate(
                "raise",
                size_policy=None,
                reason="preflop:3bet|v208_missing_size_policy",
            )
        )
    except ValueError as exc:
        assert str(exc) == UNSUPPORTED_RAISE_WITHOUT_SIZE_POLICY_REASON
    else:
        raise AssertionError("raise without size_policy must be rejected")


def test_preflop_raise_with_size_policy_is_still_blocked_by_current_runtime_policy():
    try:
        build_solver_action_runtime_plan_candidate(
            _candidate(
                "raise",
                size_policy={"pct": 98},
                target_button_classes=["98%", "Bet/Raise"],
                reason="preflop:3bet|v208_size_policy_present",
            )
        )
    except ValueError as exc:
        assert str(exc) == UNSUPPORTED_RAISE_WITHOUT_EXECUTABLE_SEQUENCE_REASON
    else:
        raise AssertionError("raise with size_policy must remain blocked until preflop-only raise gate")


def main() -> None:
    tests = [
        test_fold_call_check_solver_candidates_build_runtime_plans,
        test_preflop_raise_without_size_policy_is_rejected,
        test_preflop_raise_with_size_policy_is_still_blocked_by_current_runtime_policy,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.0.8 preflop runtime raise mapping synthetic safety tests passed.")


if __name__ == "__main__":
    main()
