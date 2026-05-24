from __future__ import annotations

import display_analysis_cycle as dac


def _report(status: str, *, frame_finished: bool = False, skip_action: bool = False) -> dict:
    return {
        "service_click": {
            "status": status,
            "frame_finished": frame_finished,
            "skip_action_button_runtime": skip_action,
        }
    }


def test_service_action_statuses_stop_poker_branch() -> None:
    assert dac._should_service_stop_poker_branch(_report("dry_run")) is True
    assert dac._should_service_stop_poker_branch(_report("clicked")) is True
    assert dac._should_service_stop_poker_branch(_report("confirmed")) is True


def test_service_flags_stop_poker_branch() -> None:
    assert dac._should_service_stop_poker_branch(_report("skipped", frame_finished=True)) is True
    assert dac._should_service_stop_poker_branch(_report("skipped", skip_action=True)) is True


def test_passive_or_failed_service_does_not_stop_poker_branch() -> None:
    assert dac._should_service_stop_poker_branch(_report("skipped")) is False
    assert dac._should_service_stop_poker_branch(_report("detected_only")) is False
    assert dac._should_service_stop_poker_branch(_report("blocked")) is False
    assert dac._should_service_stop_poker_branch(_report("error")) is False
    assert dac._should_service_stop_poker_branch({}) is False


def main() -> int:
    test_service_action_statuses_stop_poker_branch()
    test_service_flags_stop_poker_branch()
    test_passive_or_failed_service_does_not_stop_poker_branch()
    print("[RESULT] OK: PokerVision V7.0 service-first stop-policy unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
