from __future__ import annotations

import display_analysis_cycle as dac

from logic.decision_json_builder import build_decision_json_from_clear_state, validate_decision_json_contract
from logic.action_decision_stub import build_action_decision_from_decision_json, validate_action_decision_contract
from logic.action_runtime_plan_builder import build_action_runtime_plan_from_action_decision, validate_action_runtime_plan_contract


def _service_report(status: str = "skipped") -> dict:
    return {
        "service_click": {
            "status": status,
            "target_class": None,
            "target_sequence": [],
            "frame_finished": False,
            "skip_action_button_runtime": False,
            "click_points": [],
            "dry_run": True,
            "real_click_enabled": False,
        }
    }


def _clear_state(table_id: str, action: str = "fold") -> dict:
    return {
        "frame_id": f"{table_id}_hand_01_preflop_01",
        "board": {"cards": [], "street": "preflop"},
        "Total_pot": 4.0,
        "players": {
            "BB": {
                "hero": True,
                "cards": ["Q_spades", "3_diamonds"],
                "stack": 59.0,
                "fold": False,
                "chips": 1.0,
            },
            "SB": {"stack": 155.0, "fold": True, "chips": 0.5},
            "CO": {"stack": 119.0, "fold": False, "chips": 2.5},
        },
    }


def _active_branch_pipeline(table_id: str, action: str = "fold") -> dict:
    service_report = _service_report("skipped")
    assert dac._should_service_stop_poker_branch(service_report) is False

    clear_state = _clear_state(table_id, action=action)

    decision_json = build_decision_json_from_clear_state(clear_state)
    decision_validation = validate_decision_json_contract(decision_json)
    assert decision_validation["ok"], decision_validation

    action_decision = build_action_decision_from_decision_json(decision_json)
    action_validation = validate_action_decision_contract(action_decision)
    assert action_validation["ok"], action_validation

    # Current stub can default to fold; for V7.3 we validate the produced safe plan,
    # not solver quality.
    runtime_plan = build_action_runtime_plan_from_action_decision(action_decision)
    runtime_validation = validate_action_runtime_plan_contract(runtime_plan)
    assert runtime_validation["ok"], runtime_validation

    return {
        "table_id": table_id,
        "service_stops": False,
        "decision_json": decision_json,
        "action_decision": action_decision,
        "runtime_plan": runtime_plan,
    }


def test_active_branch_builds_decision_action_runtime_plan_for_four_tables() -> None:
    results = {
        table_id: _active_branch_pipeline(table_id)
        for table_id in ["table_01", "table_02", "table_03", "table_04"]
    }

    for table_id, result in results.items():
        assert result["table_id"] == table_id
        assert result["service_stops"] is False

        decision = result["decision_json"]
        assert decision["source"] == "Clear_JSON"
        assert decision["source_frame_id"].startswith(table_id)
        assert decision["street"] == "preflop"

        action_decision = result["action_decision"]
        assert action_decision["source"] == "Decision_JSON"
        assert action_decision["source_decision_frame_id"].startswith(table_id)
        assert action_decision["dry_run_safe"] is True

        runtime_plan = result["runtime_plan"]
        assert runtime_plan["source"] == "Action_Decision_JSON"
        assert runtime_plan["runtime_branch"] == "action_button"
        assert runtime_plan["real_click_enabled"] is False
        assert runtime_plan["target_sequence"]
        assert runtime_plan["raise_branch_enabled"] is False


def test_service_stop_blocks_active_branch_contract() -> None:
    service_report = {
        "service_click": {
            "status": "dry_run",
            "target_class": "Exit_cashOut",
            "target_sequence": ["Exit_cashOut"],
            "frame_finished": False,
            "skip_action_button_runtime": False,
            "click_points": [{"class_name": "Exit_cashOut"}],
            "dry_run": True,
            "real_click_enabled": False,
        }
    }

    assert dac._should_service_stop_poker_branch(service_report) is True


def main() -> int:
    test_active_branch_builds_decision_action_runtime_plan_for_four_tables()
    print("[OK] test_active_branch_builds_decision_action_runtime_plan_for_four_tables")
    test_service_stop_blocks_active_branch_contract()
    print("[OK] test_service_stop_blocks_active_branch_contract")
    print("[RESULT] OK: PokerVision V7.3 active branch multi-table dry-run contract tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
