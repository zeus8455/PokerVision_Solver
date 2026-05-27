from __future__ import annotations

"""
test_v240_controlled_armed_source_switch_unit.py

PokerVision Solver V2.4.0 — controlled armed source switch contract.

Purpose:
- Prove Solver_Action_Decision_Candidate_JSON can be selected only in guarded dry-run mode.
- Prove selected runtime candidate may carry v22 armed=True diagnostics.
- Prove real_click_enabled remains False.
"""

import display_analysis_cycle as dac


def _action_decision_state() -> dict:
    return {
        "source": "Action_Decision_JSON",
        "planned_action": "fold",
        "target_sequence": ["FOLD"],
        "real_click_enabled": False,
        "dry_run": True,
    }


def _solver_candidate_state() -> dict:
    return {
        "schema_version": "solver_action_decision_candidate_v1",
        "source": "Clear_JSON.engine_decision_preview",
        "source_clear_frame_id": "table_01_hand_01_preflop_01",
        "status": "ok",
        "reason": "v240_controlled_armed_source_switch_synthetic_candidate",
        "decision_id": "v240_decision_1",
        "solver_fingerprint": "v240_fp_1",
        "action": "fold",
        "planned_action": "fold",
        "target_button_classes": ["FOLD"],
        "target_sequence": ["FOLD"],
        "target_sequences": [["FOLD"]],
        "real_click_enabled": False,
        "dry_run": True,
        "dry_run_safe": True,
        "solver_stub": False,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "allowed_kind": "simple_preflop_action",
        "table_id": "table_01",
        "decision_context": {
            "street": "preflop",
            "table_id": "table_01",
            "engine_action": "fold",
        },
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": "simple_preflop_action",
            "street": "preflop",
            "real_click_enabled": False,
        },
        "size_policy": {
            "kind": "none",
        },
    }


def test_controlled_armed_candidate_can_be_selected_but_no_real_click() -> None:
    original = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK,
        "V11_CLICK_DRY_RUN": dac.V11_CLICK_DRY_RUN,
        "V11_REAL_MOUSE_CLICK_ENABLED": dac.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED": getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED", None),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN": getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN", None),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK": getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK", None),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS": list(getattr(dac, "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS", [])),
    }

    try:
        dac.V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY = True
        dac.V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK = False

        dac.V11_CLICK_DRY_RUN = True
        dac.V11_REAL_MOUSE_CLICK_ENABLED = False
        dac.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED = False

        dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED = True
        dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN = True
        dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK = True
        dac.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS = ["table_01"]

        selected = dac.build_runtime_plan_source_selection_contract(
            action_decision_state=_action_decision_state(),
            solver_candidate_state=_solver_candidate_state(),
        )

        assert selected["selected_source"] == "Solver_Action_Decision_Candidate_JSON"
        assert selected["guard"]["allowed"] is True

        plan = selected["runtime_candidate_plan"]
        assert plan["source"] == "Solver_Action_Decision_Candidate_JSON"
        assert plan["dry_run"] is True
        assert plan["real_click_enabled"] is False

        v22 = selected["v22_controlled_real_click_arming_gate"]
        assert v22["armed"] is True
        assert v22["diagnostic_only"] is True
        assert v22["does_not_enable_real_click"] is True
        assert v22["candidate_real_click_enabled"] is False

    finally:
        for name, value in original.items():
            if value is None and hasattr(dac, name):
                delattr(dac, name)
            else:
                setattr(dac, name, value)


def test_default_config_does_not_arm_candidate() -> None:
    selected = dac.build_runtime_plan_source_selection_contract(
        action_decision_state=_action_decision_state(),
        solver_candidate_state=_solver_candidate_state(),
    )

    v22 = selected.get("v22_controlled_real_click_arming_gate")
    if isinstance(v22, dict):
        assert v22.get("armed") is False

    assert selected.get("selected_source") in {
        "Action_Decision_JSON",
        "Solver_Action_Decision_Candidate_JSON",
    }


def run_all() -> None:
    tests = [
        test_controlled_armed_candidate_can_be_selected_but_no_real_click,
        test_default_config_does_not_arm_candidate,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.4.0 controlled armed source switch unit tests passed.")


if __name__ == "__main__":
    run_all()
