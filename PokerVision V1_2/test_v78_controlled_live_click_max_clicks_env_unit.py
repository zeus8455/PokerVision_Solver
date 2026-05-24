"""
V7.8 controlled live-click max-clicks env override contract.

Goal:
- Default controlled live-click max_clicks_per_run remains safe = 1.
- PowerShell/live launch can safely override it through env:
  POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN=6
- Invalid env values must fall back to safe default = 1.
"""

import os
import importlib

import config


ENV_NAME = "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN"


def _reload_config():
    return importlib.reload(config)


def test_v78_default_max_clicks_remains_one():
    os.environ.pop(ENV_NAME, None)

    cfg = _reload_config()
    snap = cfg.get_v31_controlled_live_click_gate_snapshot()

    assert snap["max_clicks_per_run"] == 1
    assert snap.get("max_clicks_per_run_env_var") == ENV_NAME
    assert snap.get("max_clicks_per_run_env_value") == ""


def test_v78_env_override_allows_six_clicks():
    os.environ[ENV_NAME] = "6"

    cfg = _reload_config()
    snap = cfg.get_v31_controlled_live_click_gate_snapshot()

    assert snap["max_clicks_per_run"] == 6
    assert snap.get("max_clicks_per_run_env_var") == ENV_NAME
    assert snap.get("max_clicks_per_run_env_value") == "6"


def test_v78_invalid_env_override_falls_back_to_one():
    os.environ[ENV_NAME] = "999"

    cfg = _reload_config()
    snap = cfg.get_v31_controlled_live_click_gate_snapshot()

    assert snap["max_clicks_per_run"] == 1
    assert snap.get("max_clicks_per_run_env_value") == "999"


def test_v78_non_integer_env_override_falls_back_to_one():
    os.environ[ENV_NAME] = "abc"

    cfg = _reload_config()
    snap = cfg.get_v31_controlled_live_click_gate_snapshot()

    assert snap["max_clicks_per_run"] == 1
    assert snap.get("max_clicks_per_run_env_value") == "abc"
