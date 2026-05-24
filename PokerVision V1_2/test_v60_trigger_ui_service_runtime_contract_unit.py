from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Callable, Dict, List

import runtime.trigger_ui_service_runtime as rt


def _slot(table_id: str = "table_01") -> Any:
    return SimpleNamespace(
        table_id=table_id,
        bbox=SimpleNamespace(x1=100, y1=200, x2=500, y2=600),
    )


def _state(table_id: str = "table_01", hand_id: str = "hand_01", frame_name: str = "hand_01_preflop") -> Dict[str, Any]:
    return {
        "table": {
            "table_id": table_id,
            "hand_id": hand_id,
            "frame_name": frame_name,
        },
        "trigger_ui": {
            "detected_classes": [],
        },
    }


def _best(class_name: str, bbox_xyxy: List[int] | None = None, confidence: float = 0.95) -> Dict[str, Dict[str, Any]]:
    return {
        class_name: {
            "class_name": class_name,
            "bbox_xyxy": bbox_xyxy or [10, 10, 110, 70],
            "confidence": confidence,
        }
    }


def _configure_safe_dry_run() -> None:
    rt.V11_TRIGGER_UI_SERVICE_CLICK_ENABLED = True
    rt.V11_TRIGGER_UI_SERVICE_DRY_RUN = True
    rt.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False
    rt.V11_TRIGGER_UI_SERVICE_REQUIRE_BUTTON_DETECTION = True
    rt.V11_TRIGGER_UI_SERVICE_SLOT_GUARD_ENABLED = True
    rt.V11_NON_ACTIVE_FOLD_ENABLED = True
    if hasattr(rt, "_SERVICE_EXECUTED_AT"):
        rt._SERVICE_EXECUTED_AT.clear()


def _run(best_by_class: Dict[str, Dict[str, Any]], table_id: str = "table_01") -> Dict[str, Any]:
    _configure_safe_dry_run()
    return rt.run_v11_trigger_ui_service_runtime(
        full_state=_state(table_id=table_id),
        table_roi_image=None,
        slot=_slot(table_id),
        trigger_best_by_class=best_by_class,
    )


def _patch_attr(name: str, value: Any) -> Callable[[], None]:
    old = getattr(rt, name)
    setattr(rt, name, value)

    def restore() -> None:
        setattr(rt, name, old)

    return restore


def test_remove_table_is_detected_only_without_click_plan() -> None:
    report = _run(_best("Remove_Table"))
    service = report["service_click"]

    assert service["status"] == "detected_only", report
    assert service["target_class"] is None, report
    assert service["target_sequence"] == [], report
    assert service["click_points"] == [], report
    assert service["guard_passed"] is False, report
    assert service["frame_finished"] is False, report
    assert service["skip_action_button_runtime"] is False, report
    assert "Remove_Table" in service["message"], report


def test_true_active_fold_is_terminal_confirmation_without_click_plan() -> None:
    report = _run(_best("True_active_fold"))
    service = report["service_click"]

    assert service["status"] == "confirmed", report
    assert service["target_class"] is None, report
    assert service["target_sequence"] == [], report
    assert service["click_points"] == [], report
    assert service["frame_finished"] is True, report
    assert service["skip_action_button_runtime"] is True, report
    assert "True_active_fold" in service["message"], report


def test_simple_service_classes_build_dry_run_click_plan() -> None:
    for class_name in ("Remove_Game", "Exit_cashOut", "1_roll_board"):
        report = _run(_best(class_name))
        service = report["service_click"]

        assert service["status"] == "dry_run", report
        assert service["target_class"] == class_name, report
        assert service["target_sequence"] == [class_name], report
        assert service["guard_passed"] is True, report
        assert service["skip_action_button_runtime"] is False, report
        assert len(service["click_points"]) == 1, report
        assert service["click_points"][0]["inside_slot_bbox"] is True, report


def test_bunny_probability_pass_builds_dry_run_click_plan() -> None:
    restore_random = _patch_attr("random", SimpleNamespace(random=lambda: 0.0, randint=lambda a, b: a))
    try:
        report = _run(_best("Bunny"))
    finally:
        restore_random()

    service = report["service_click"]
    assert service["status"] == "dry_run", report
    assert service["target_class"] == "Bunny", report
    assert service["guard_passed"] is True, report
    assert len(service["click_points"]) == 1, report


def test_bunny_probability_fail_skips_without_click_plan() -> None:
    restore_random = _patch_attr("random", SimpleNamespace(random=lambda: 1.0, randint=lambda a, b: a))
    try:
        report = _run(_best("Bunny"))
    finally:
        restore_random()

    service = report["service_click"]
    assert service["status"] == "skipped", report
    assert service["target_class"] == "Bunny", report
    assert service["click_points"] == [], report
    assert service["guard_passed"] is False, report
    assert "probability gate did not pass" in service["message"], report


def test_non_active_fold_death_card_match_builds_dry_run_and_skips_action_runtime() -> None:
    restore_extract = _patch_attr("_extract_hero_cards_from_state", lambda full_state: ["A_spades", "2_clubs"])
    restore_death = _patch_attr(
        "check_hero_cards_in_death_range",
        lambda hero_cards: {
            "status": "ok",
            "hero_cards": list(hero_cards),
            "hand_key": "A2o",
            "matched": True,
            "message": "Hero hand is inside death-card range.",
        },
    )
    try:
        report = _run(_best("Non_active_fold"))
    finally:
        restore_death()
        restore_extract()

    service = report["service_click"]
    death = report["death_card"]

    assert service["status"] == "dry_run", report
    assert service["target_class"] == "Non_active_fold", report
    assert service["skip_action_button_runtime"] is True, report
    assert service["guard_passed"] is True, report
    assert len(service["click_points"]) == 1, report
    assert death["matched"] is True, report
    assert death["hand_key"] == "A2o", report


def test_non_active_fold_death_card_no_match_skips_without_click_plan() -> None:
    restore_extract = _patch_attr("_extract_hero_cards_from_state", lambda full_state: ["K_spades", "Q_clubs"])
    restore_death = _patch_attr(
        "check_hero_cards_in_death_range",
        lambda hero_cards: {
            "status": "ok",
            "hero_cards": list(hero_cards),
            "hand_key": "KQo",
            "matched": False,
            "message": "Hero hand is not inside death-card range.",
        },
    )
    try:
        report = _run(_best("Non_active_fold"))
    finally:
        restore_death()
        restore_extract()

    service = report["service_click"]
    death = report["death_card"]

    assert service["status"] == "skipped", report
    assert service["target_class"] == "Non_active_fold", report
    assert service["skip_action_button_runtime"] is False, report
    assert service["click_points"] == [], report
    assert service["guard_passed"] is False, report
    assert death["matched"] is False, report


def test_service_click_point_outside_slot_is_blocked() -> None:
    report = _run(_best("Remove_Game", bbox_xyxy=[900, 900, 980, 960]))
    service = report["service_click"]

    assert service["status"] == "blocked", report
    assert service["target_class"] == "Remove_Game", report
    assert service["guard_passed"] is False, report
    assert len(service["click_points"]) == 1, report
    assert service["click_points"][0]["inside_slot_bbox"] is False, report
    assert "outside current slot_bbox" in service["message"], report


def main() -> int:
    tests = [
        test_remove_table_is_detected_only_without_click_plan,
        test_true_active_fold_is_terminal_confirmation_without_click_plan,
        test_simple_service_classes_build_dry_run_click_plan,
        test_bunny_probability_pass_builds_dry_run_click_plan,
        test_bunny_probability_fail_skips_without_click_plan,
        test_non_active_fold_death_card_match_builds_dry_run_and_skips_action_runtime,
        test_non_active_fold_death_card_no_match_skips_without_click_plan,
        test_service_click_point_outside_slot_is_blocked,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: PokerVision V6.0 Trigger_UI service runtime contract tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
