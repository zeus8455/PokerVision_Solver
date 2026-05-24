"""
V8.3 main.py startup-audit-only contract.

Goal:
- main.py must support a safe startup audit mode.
- The mode validates controlled live readiness and prints startup config.
- The mode must not launch the live UI/runtime loop.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "main.py"


def test_v83_main_startup_audit_only_exits_without_live_ui():
    env = os.environ.copy()
    env.update({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01,table_02,table_03,table_04,table_05,table_06",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "6",
    })

    proc = subprocess.run(
        [sys.executable, str(MAIN), "--startup-audit-only"],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=20,
    )

    assert proc.returncode == 0, proc.stdout
    assert "[V83_STARTUP_AUDIT_ONLY] enabled=True" in proc.stdout
    assert "[V10_REAL_CLICK_READINESS] status=ready_for_controlled_real_click" in proc.stdout
    assert "[ACTION_REAL_CLICK] enabled=True, dry_run=False" in proc.stdout
    assert "[SERVICE_REAL_CLICK] enabled=False, dry_run=True" in proc.stdout
    assert "launch_live_ui" not in proc.stdout
