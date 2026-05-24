"""
V8.0 controlled live preflight contract.

Goal:
- Provide a dedicated pre-live safety preflight before launching main.py.
- The preflight must validate V31 controlled-live env, table scope, max-click override,
  real-click readiness, service real-click block, simple actions only, and raise branch block.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "controlled_live_preflight.py"


def _run_preflight(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged.update(env)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_v80_preflight_blocks_without_controlled_env():
    proc = _run_preflight({})

    assert proc.returncode == 2
    assert "CONTROLLED_LIVE_PREFLIGHT_BLOCKED" in proc.stdout
    assert "missing_controlled_live_click_env" in proc.stdout


def test_v80_preflight_blocks_six_table_profile_until_real_click_readiness_enabled():
    proc = _run_preflight({
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01,table_02,table_03,table_04,table_05,table_06",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "6",
    })

    assert proc.returncode == 2, proc.stdout
    assert "CONTROLLED_LIVE_PREFLIGHT_BLOCKED" in proc.stdout
    assert "real_click_readiness_not_ready" in proc.stdout
    assert "table_01,table_02,table_03,table_04,table_05,table_06" in proc.stdout
    assert "max_clicks_per_run=6" in proc.stdout
    assert "service_real_click_disabled=True" in proc.stdout
    assert "raise_branch_enabled=False" in proc.stdout


def test_v80_preflight_blocks_invalid_max_clicks():
    proc = _run_preflight({
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01,table_02,table_03,table_04",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "1",
    })

    assert proc.returncode == 2
    assert "CONTROLLED_LIVE_PREFLIGHT_BLOCKED" in proc.stdout
    assert "max_clicks_must_be_4_to_6_for_multi_table_live" in proc.stdout
