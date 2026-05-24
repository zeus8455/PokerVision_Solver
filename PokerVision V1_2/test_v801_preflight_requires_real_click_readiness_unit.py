"""
V8.0.1 controlled live preflight must require real-click readiness.

The V31 env/scope may be valid, but preflight must still block if config is in
safe no-click mode:
- V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE=True
- V09_REAL_CLICK_MASTER_ARMED=False
- V11_REAL_MOUSE_CLICK_ENABLED=False
- V11_CLICK_DRY_RUN=True
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "controlled_live_preflight.py"


def test_v801_valid_v31_env_still_blocks_when_real_click_readiness_false():
    env = os.environ.copy()
    env.update({
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01,table_02,table_03,table_04,table_05,table_06",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "6",
    })

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    assert proc.returncode == 2
    assert "CONTROLLED_LIVE_PREFLIGHT_BLOCKED" in proc.stdout
    assert "real_click_readiness_not_ready" in proc.stdout
    assert '"real_click_ready": false' in proc.stdout
