"""
test_runtime_plan_source_selection_unit.py

PokerVision Solver V1.7.1 — tests runtime source selection helper.
"""

from __future__ import annotations

import json
from pathlib import Path

import display_analysis_cycle as dac


CANDIDATE_ROOT = Path(
    r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output\ui_display_cycle\current_cycle\Solver_Action_Decision_Candidate_JSON"
)


def _sample_action_decision_state() -> dict:
    return {
        "schema_version": "action_decision_v1",
        "source": "Decision_JSON",
        "source_decision_frame_id": "unit_frame",
        "status": "ok",
        "action": "fold",
        "size_policy": None,
        "target_button_classes": ["FOLD"],
        "reason": "unit_stub",
        "dry_run_safe": True,
        "solver_stub": True,
        "decision_context": {"street": "preflop", "hero_position": "BB", "source_frame_id": "unit_frame"},
    }


def _load_first_solver_candidate() -> dict:
    files = sorted(CANDIDATE_ROOT.rglob("*.json"))
    assert files, "No solver candidate replay files found."
    return json.loads(files[0].read_text(encoding="utf-8"))


def test_source_selection_defaults_to_action_decision_when_guard_disabled() -> None:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
    }

    try:
        dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = False

        selected = dac.build_runtime_plan_source_selection_contract(
            action_decision_state=_sample_action_decision_state(),
            solver_candidate_state=_load_first_solver_candidate(),
        )

        assert selected["selected_source"] == "Action_Decision_JSON"
        assert selected["reason"] == "v16_switch_disabled"
        assert selected["guard"]["allowed"] is False

    finally:
        for name, value in original.items():
            setattr(dac, name, value)


def test_source_selection_can_select_solver_candidate_in_dry_run_guard_mode() -> None:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    }

    try:
        dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False
        dac.V11_CLICK_DRY_RUN = True
        dac.V11_REAL_MOUSE_CLICK_ENABLED = False
        dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

        selected = dac.build_runtime_plan_source_selection_contract(
            action_decision_state=_sample_action_decision_state(),
            solver_candidate_state=_load_first_solver_candidate(),
        )

        assert selected["selected_source"] == "Solver_Action_Decision_Candidate_JSON"
        assert selected["reason"] == "v17_1_solver_candidate_selected_dry_run_only"
        assert selected["guard"]["allowed"] is True

        plan = selected["runtime_candidate_plan"]
        assert plan["source"] == "Solver_Action_Decision_Candidate_JSON"
        assert plan["solver_stub"] is False
        assert plan["real_click_enabled"] is False
        assert plan["dry_run"] is True

    finally:
        for name, value in original.items():
            setattr(dac, name, value)



def test_source_selection_exposes_v21_preflop_preflight_diagnostics_for_raise() -> None:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    }

    try:
        dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False
        dac.V11_CLICK_DRY_RUN = True
        dac.V11_REAL_MOUSE_CLICK_ENABLED = False
        dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

        solver_candidate_state = {
            "schema_version": "solver_action_decision_candidate_v1",
            "source": "Clear_JSON.engine_decision_preview",
            "source_clear_frame_id": "v211_preflop_raise",
            "status": "ok",
            "action": "raise",
            "size_policy": {"pct": 98},
            "target_button_classes": ["98%", "Bet/Raise"],
            "reason": "preflop:3bet|v211_unit",
            "dry_run_safe": True,
            "solver_stub": False,
            "decision_id": "decision_v211",
            "solver_fingerprint": "fingerprint_v211",
            "decision_context": {
                "street": "preflop",
                "hero_position": "BB",
                "source_frame_id": "v211_preflop_raise",
            },
        }

        selected = dac.build_runtime_plan_source_selection_contract(
            action_decision_state=_sample_action_decision_state(),
            solver_candidate_state=solver_candidate_state,
        )

        plan = selected["runtime_candidate_plan"]
        gate = selected["v21_preflop_real_click_preflight_gate"]
        validation = selected["v21_preflop_real_click_preflight_gate_validation"]

        assert selected["selected_source"] == "Solver_Action_Decision_Candidate_JSON"
        assert plan["planned_action"] == "bet_raise"
        assert plan["target_sequence"] == ["98%", "Bet/Raise"]
        assert plan["real_click_enabled"] is False
        assert gate["ok"] is True
        assert gate["allowed_kind"] == "preflop_raise_98_sequence"
        assert gate["real_click_enabled"] is False
        assert validation["ok"] is True

    finally:
        for name, value in original.items():
            setattr(dac, name, value)

def main() -> None:
    test_source_selection_defaults_to_action_decision_when_guard_disabled()
    test_source_selection_can_select_solver_candidate_in_dry_run_guard_mode()
    test_source_selection_exposes_v21_preflop_preflight_diagnostics_for_raise()
    print("[RESULT] OK: runtime plan source selection unit tests passed.")


if __name__ == "__main__":
    main()
