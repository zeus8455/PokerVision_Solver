from __future__ import annotations

import controlled_service_dry_run_smoke_runner as runner


def test_controlled_service_dry_run_smoke_runner() -> None:
    report = runner.run_all()
    assert report["status"] == "ok", report
    assert not report["errors"], report

    by_class = {case["class_name"]: case for case in report["cases"]}

    assert by_class["Exit_cashOut"]["target_class"] == "Exit_cashOut"
    assert by_class["1_roll_board"]["target_class"] == "1_roll_board"
    assert by_class["Remove_Game"]["target_class"] == "Remove_Game"
    assert by_class["Non_active_fold"]["target_class"] == "Non_active_fold"
    assert by_class["Non_active_fold"]["status"] == "skipped"
    assert by_class["Non_active_fold"]["click_points_count"] == 0

    assert by_class["True_active_fold"]["status"] == "confirmed"
    assert by_class["True_active_fold"]["click_points_count"] == 0
    assert by_class["True_active_fold"]["skip_action_button_runtime"] is True

    assert by_class["Remove_Table"]["status"] == "detected_only"
    assert by_class["Remove_Table"]["click_points_count"] == 0

    for case in report["cases"]:
        assert case["real_click_enabled"] is False, case


def main() -> int:
    test_controlled_service_dry_run_smoke_runner()
    print("[RESULT] OK: PokerVision V6.8 controlled service dry-run smoke runner unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
