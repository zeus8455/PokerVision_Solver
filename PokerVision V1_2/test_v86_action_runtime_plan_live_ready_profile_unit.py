"""
V8.6 Action_Runtime_Plan must follow V8.1 live-ready profile.

Goal:
- Safe-default runtime plan remains dry-run / no real click.
- V8.1 controlled Action_Button profile makes Action_Runtime_Plan live-ready:
  dry_run_required=False
  real_click_enabled=True
- Service branch and raise branch stay disabled elsewhere by readiness/preflight.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


SNAPSHOT_CODE = r'''
import json
import config
from logic.action_runtime_plan_builder import (
    build_action_runtime_plan_from_action_decision,
    validate_action_runtime_plan_contract,
)

action_decision = {
    "schema_version": "action_decision_v1",
    "source": "Decision_JSON",
    "status": "ok",
    "source_decision_frame_id": "frame_v86_test",
    "action": "fold",
    "reason": "v86_unit_test_fold",
    "size_policy": {},
    "target_button_classes": ["FOLD"],
    "dry_run_safe": True,
    "solver_stub": True,
    "decision_context": {"table_id": "table_01"},
}

plan = build_action_runtime_plan_from_action_decision(action_decision)
validation = validate_action_runtime_plan_contract(plan)

print(json.dumps({
    "config": {
        "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": config.V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE,
        "V09_REAL_CLICK_MASTER_ARMED": config.V09_REAL_CLICK_MASTER_ARMED,
        "V11_REAL_MOUSE_CLICK_ENABLED": config.V11_REAL_MOUSE_CLICK_ENABLED,
        "V11_CLICK_DRY_RUN": config.V11_CLICK_DRY_RUN,
    },
    "plan": {
        "dry_run_required": plan.get("dry_run_required"),
        "real_click_enabled": plan.get("real_click_enabled"),
        "dry_run": plan.get("dry_run"),
        "runtime_branch": plan.get("runtime_branch"),
        "planned_action": plan.get("planned_action"),
    },
    "validation": validation,
}, sort_keys=True))
'''


def _run_snapshot(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    for key in [
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE",
        "POKERVISION_CONTROLLED_LIVE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN",
        "POKERVISION_CONTROLLED_LIVE_TEST_SCOPE",
    ]:
        merged.pop(key, None)
    merged.update(env)

    return subprocess.run(
        [sys.executable, "-c", SNAPSHOT_CODE],
        cwd=str(ROOT),
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_v86_action_runtime_plan_safe_default_stays_dry_run():
    proc = _run_snapshot({})
    assert proc.returncode == 0, proc.stdout
    assert '"V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": true' in proc.stdout
    assert '"dry_run_required": true' in proc.stdout
    assert '"real_click_enabled": false' in proc.stdout
    assert '"ok": true' in proc.stdout


def test_v86_action_runtime_plan_live_ready_profile_enables_real_click_plan():
    proc = _run_snapshot({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
    })

    assert proc.returncode == 0, proc.stdout
    assert '"V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": false' in proc.stdout
    assert '"V09_REAL_CLICK_MASTER_ARMED": true' in proc.stdout
    assert '"V11_REAL_MOUSE_CLICK_ENABLED": true' in proc.stdout
    assert '"V11_CLICK_DRY_RUN": false' in proc.stdout

    assert '"dry_run_required": false' in proc.stdout
    assert '"real_click_enabled": true' in proc.stdout
    assert '"dry_run": false' in proc.stdout
    assert '"runtime_branch": "action_button"' in proc.stdout
    assert '"ok": true' in proc.stdout
