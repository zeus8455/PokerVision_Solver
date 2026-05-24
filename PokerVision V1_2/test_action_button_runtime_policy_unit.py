"""Unit tests for logic/action_button_runtime_policy.py."""
from __future__ import annotations

from logic.action_button_runtime_policy import (
    build_controlled_target_sequences,
    canonical_button_class,
    resolve_action_button_runtime_policy,
)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_class_aliases() -> None:
    _assert(canonical_button_class("fold") == "FOLD", "fold alias failed")
    _assert(canonical_button_class("CHECK_FOLD") == "Check/fold", "check/fold alias failed")
    _assert(canonical_button_class("raise") == "Bet/Raise", "raise alias failed")


def test_fold_policy_uses_safe_fallback() -> None:
    sequences = build_controlled_target_sequences("fold")
    _assert(sequences == [["FOLD"], ["Check/fold"]], f"unexpected fold sequences: {sequences}")


def test_fold_selects_fold_when_available() -> None:
    result = resolve_action_button_runtime_policy(action="fold", detected_classes=["FOLD", "Check/fold"])
    _assert(result["ok"] is True, f"fold should be allowed: {result}")
    _assert(result["selected_sequence"] == ["FOLD"], f"wrong selected fold seq: {result}")


def test_fold_falls_back_to_check_fold() -> None:
    result = resolve_action_button_runtime_policy(action="fold", detected_classes=["Check/fold", "Call"])
    _assert(result["ok"] is True, f"fold fallback should be allowed: {result}")
    _assert(result["selected_sequence"] == ["Check/fold"], f"wrong fallback seq: {result}")


def test_check_policy() -> None:
    result = resolve_action_button_runtime_policy(action="check", detected_classes=["Check"])
    _assert(result["ok"] is True, f"check should be allowed: {result}")
    _assert(result["selected_sequence"] == ["Check"], f"wrong check seq: {result}")


def test_check_falls_back_to_check_fold() -> None:
    result = resolve_action_button_runtime_policy(action="check", detected_classes=["Check/fold"])
    _assert(result["ok"] is True, f"check fallback should be allowed: {result}")
    _assert(result["selected_sequence"] == ["Check/fold"], f"wrong check fallback: {result}")



def test_check_fold_prefers_check_when_available() -> None:
    result = resolve_action_button_runtime_policy(action="check_fold", detected_classes=["Check", "Check/fold", "FOLD"])
    _assert(result["ok"] is True, f"check_fold should prefer check: {result}")
    _assert(result["selected_sequence"] == ["Check"], f"wrong check_fold primary: {result}")


def test_check_fold_falls_back_to_check_fold_when_check_missing() -> None:
    result = resolve_action_button_runtime_policy(action="check_fold", detected_classes=["Check/fold", "FOLD"])
    _assert(result["ok"] is True, f"check_fold should fall back to Check/fold: {result}")
    _assert(result["selected_sequence"] == ["Check/fold"], f"wrong check_fold fallback: {result}")


def test_check_fold_falls_back_to_fold_when_only_fold_available() -> None:
    result = resolve_action_button_runtime_policy(action="check_fold", detected_classes=["FOLD"])
    _assert(result["ok"] is True, f"check_fold should fall back to FOLD: {result}")
    _assert(result["selected_sequence"] == ["FOLD"], f"wrong check_fold final fallback: {result}")


def test_call_policy() -> None:
    result = resolve_action_button_runtime_policy(action="call", detected_classes=["Call"])
    _assert(result["ok"] is True, f"call should be allowed: {result}")
    _assert(result["selected_sequence"] == ["Call"], f"wrong call seq: {result}")


def test_missing_button_blocks() -> None:
    result = resolve_action_button_runtime_policy(action="call", detected_classes=["FOLD"])
    _assert(result["ok"] is False, "call without Call button must block")
    _assert(result["blocked_reason"] == "required_action_button_sequence_not_detected", f"wrong reason: {result}")


def test_bet_raise_branch_disabled_for_first_real_click_stage() -> None:
    result = resolve_action_button_runtime_policy(action="raise", detected_classes=["98%", "Bet/Raise"], real_click_enabled=True)
    _assert(result["ok"] is False, "raise branch must be disabled in V1.1.1")
    _assert(
        result["blocked_reason"] == "bet_raise_branch_disabled_for_v1_1_first_real_click_stage",
        f"wrong raise block reason: {result}",
    )


def test_plan_mode_without_detector_result() -> None:
    result = resolve_action_button_runtime_policy(action="fold", detected_classes=None)
    _assert(result["ok"] is True, f"plan mode should be ok: {result}")
    _assert(result["selected_sequence"] == ["FOLD"], f"plan mode selected wrong seq: {result}")
    _assert(result["real_click_allowed"] is False, "plan mode must not claim real-click allowed")


def main() -> int:
    tests = [
        test_class_aliases,
        test_fold_policy_uses_safe_fallback,
        test_fold_selects_fold_when_available,
        test_fold_falls_back_to_check_fold,
        test_check_policy,
        test_check_falls_back_to_check_fold,
        test_check_fold_prefers_check_when_available,
        test_check_fold_falls_back_to_check_fold_when_check_missing,
        test_check_fold_falls_back_to_fold_when_only_fold_available,
        test_call_policy,
        test_missing_button_blocks,
        test_bet_raise_branch_disabled_for_first_real_click_stage,
        test_plan_mode_without_detector_result,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Action button runtime policy unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
