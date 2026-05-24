from logic.controlled_real_click_scope import (
    ControlledRealClickScope,
    ControlledRealClickScopeConfig,
    ControlledRealClickScopeRequest,
)


def _request(**overrides):
    payload = {
        "table_id": "table_01",
        "runtime_branch": "action_button",
        "action": "fold",
        "decision_id": "decision_001",
        "target_button_class": "FOLD",
        "target_sequence": ["FOLD", "Check/fold"],
        "dry_run": False,
        "real_click_enabled": True,
    }
    payload.update(overrides)
    return ControlledRealClickScopeRequest(**payload)


def test_dry_run_path_is_allowed_and_does_not_consume_real_click_limit():
    scope = ControlledRealClickScope()
    result = scope.evaluate(_request(dry_run=True, real_click_enabled=False))
    assert result["status"] == "allowed"
    assert result["reason"] == "dry_run_or_no_real_click_requested"
    assert scope.executed_real_clicks_count == 0


def test_first_simple_action_button_real_click_is_allowed():
    scope = ControlledRealClickScope()
    result = scope.evaluate(_request())
    assert result["status"] == "allowed"
    assert result["scope_passed"] is True
    assert result["reason"] == "controlled_scope_passed"


def test_wrong_table_is_blocked_in_test_mode():
    scope = ControlledRealClickScope()
    result = scope.evaluate(_request(table_id="table_02"))
    assert result["status"] == "blocked"
    assert result["reason"] == "wrong_table_id"


def test_service_branch_is_blocked():
    scope = ControlledRealClickScope()
    result = scope.evaluate(_request(runtime_branch="trigger_ui_service"))
    assert result["status"] == "blocked"
    assert result["reason"] in {"non_action_button_branch", "service_branch_disabled"}


def test_raise_or_size_button_is_blocked():
    scope = ControlledRealClickScope()
    result = scope.evaluate(
        _request(
            action="raise",
            target_button_class="98%",
            target_sequence=["98%", "Bet/Raise"],
        )
    )
    assert result["status"] == "blocked"
    assert result["reason"] in {"non_simple_action_blocked", "raise_or_size_branch_blocked"}


def test_decision_id_repeat_is_blocked_after_record_success():
    scope = ControlledRealClickScope()
    first = scope.evaluate(_request(decision_id="decision_repeat"))
    assert first["status"] == "allowed"
    scope.record_success("decision_repeat")
    second = scope.evaluate(_request(decision_id="decision_repeat"))
    assert second["status"] == "blocked"
    assert second["reason"] == "decision_id_already_executed_in_scope"


def test_max_real_clicks_per_run_blocks_second_click():
    scope = ControlledRealClickScope(
        ControlledRealClickScopeConfig(max_real_clicks_per_run=1)
    )
    assert scope.evaluate(_request(decision_id="decision_a"))["status"] == "allowed"
    scope.record_success("decision_a")
    result = scope.evaluate(_request(decision_id="decision_b"))
    assert result["status"] == "blocked"
    assert result["reason"] == "max_real_clicks_per_run_reached"
