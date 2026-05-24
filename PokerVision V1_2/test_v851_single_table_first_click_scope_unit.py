"""
V8.5.1 single-table first-click preflight scope contract.

Goal:
- Default V8.0/V8.4 preflight remains strict for table_01..table_06 and max_clicks 4..6.
- A separate explicit test scope may allow the first safe live-click rehearsal:
  table_01 + max_clicks_per_run=1.
"""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "controlled_live_preflight.py"


def _run_preflight(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
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
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_v851_single_table_first_click_scope_allows_table_01_one_click():
    proc = _run_preflight({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "1",
        "POKERVISION_CONTROLLED_LIVE_TEST_SCOPE": "V8_5_SINGLE_TABLE_FIRST_CLICK",
    })

    assert proc.returncode == 0, proc.stdout
    assert "CONTROLLED_LIVE_PREFLIGHT_READY" in proc.stdout
    assert "blockers=none" in proc.stdout
    assert "table_ids=table_01" in proc.stdout
    assert "max_clicks_per_run=1" in proc.stdout
    assert "test_scope=V8_5_SINGLE_TABLE_FIRST_CLICK" in proc.stdout


def test_v851_single_table_one_click_still_blocked_without_explicit_scope():
    proc = _run_preflight({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "1",
    })

    assert proc.returncode == 2
    assert "CONTROLLED_LIVE_PREFLIGHT_BLOCKED" in proc.stdout
    assert "table_ids_must_be_table_01_to_table_06" in proc.stdout
    assert "max_clicks_must_be_4_to_6_for_multi_table_live" in proc.stdout



def test_v852_single_table_first_click_scope_allows_table_02_one_click():
    proc = _run_preflight({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_02",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "1",
        "POKERVISION_CONTROLLED_LIVE_TEST_SCOPE": "V8_5_SINGLE_TABLE_FIRST_CLICK",
    })

    assert proc.returncode == 0, proc.stdout
    assert "CONTROLLED_LIVE_PREFLIGHT_READY" in proc.stdout
    assert "blockers=none" in proc.stdout
    assert "table_ids=table_02" in proc.stdout
    assert "max_clicks_per_run=1" in proc.stdout
    assert "test_scope=V8_5_SINGLE_TABLE_FIRST_CLICK" in proc.stdout


def test_v852_single_table_first_click_scope_blocks_multiple_tables():
    proc = _run_preflight({
        "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
        "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
        "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": "table_01,table_02",
        "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "1",
        "POKERVISION_CONTROLLED_LIVE_TEST_SCOPE": "V8_5_SINGLE_TABLE_FIRST_CLICK",
    })

    assert proc.returncode == 2
    assert "CONTROLLED_LIVE_PREFLIGHT_BLOCKED" in proc.stdout
    assert "single_table_first_click_scope_requires_exactly_one_table" in proc.stdout
