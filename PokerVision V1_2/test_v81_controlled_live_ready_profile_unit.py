"""
V8.1 controlled live-ready profile switch contract.

Goal:
- Safe default must remain no-click.
- A single explicit env profile may switch config into controlled Action_Button live-ready mode.
- The profile must not enable Trigger_UI service real-clicks.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _run_config_snapshot(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)

    code = r'''
import json
import config
from logic.real_click_readiness import validate_real_click_readiness

payload = {
    "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": config.V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE,
    "V09_REAL_CLICK_MASTER_ARMED": config.V09_REAL_CLICK_MASTER_ARMED,
    "V11_REAL_MOUSE_CLICK_ENABLED": config.V11_REAL_MOUSE_CLICK_ENABLED,
    "V11_CLICK_DRY_RUN": config.V11_CLICK_DRY_RUN,
    "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": config.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    "V11_TRIGGER_UI_SERVICE_DRY_RUN": config.V11_TRIGGER_UI_SERVICE_DRY_RUN,
    "readiness": validate_real_click_readiness(config).to_dict(),
}
print(json.dumps(payload, sort_keys=True))
'''
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_v81_default_config_remains_safe_no_click():
    proc = _run_config_snapshot({})
    assert proc.returncode == 0, proc.stdout
    assert '"V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": true' in proc.stdout
    assert '"V09_REAL_CLICK_MASTER_ARMED": false' in proc.stdout
    assert '"real_click_ready": false' in proc.stdout


def test_v81_controlled_live_ready_profile_enables_real_click_readiness():
    proc = _run_config_snapshot({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
    })

    assert proc.returncode == 0, proc.stdout
    assert '"V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": false' in proc.stdout
    assert '"V09_REAL_CLICK_MASTER_ARMED": true' in proc.stdout
    assert '"V11_REAL_MOUSE_CLICK_ENABLED": true' in proc.stdout
    assert '"V11_CLICK_DRY_RUN": false' in proc.stdout
    assert '"V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": false' in proc.stdout
    assert '"V11_TRIGGER_UI_SERVICE_DRY_RUN": true' in proc.stdout
    assert '"real_click_ready": true' in proc.stdout
