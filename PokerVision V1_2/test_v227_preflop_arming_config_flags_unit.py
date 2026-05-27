from __future__ import annotations

"""
test_v227_preflop_arming_config_flags_unit.py

PokerVision Solver V2.2.7 — config flags for controlled preflop arming.

Default must remain safe:
- arming disabled
- explicit token disabled
- real-click disabled
- no allowed tables
- preflop-only scope enabled
- all guard requirements enabled
"""

import config as c


def test_v227_default_config_is_safe_no_click() -> None:
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ARMING_ENABLED is False
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_EXPLICIT_TOKEN is False
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK is False
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOWED_TABLE_IDS == []

    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_PREFLOP_ONLY is True
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_SLOT_GUARD is True
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_NO_REPEAT_GUARD is True
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_BUTTON_AVAILABILITY is True
    assert c.V22_CONTROLLED_PREFLOP_REAL_CLICK_REQUIRE_EXPORT_VALIDATOR is True


def run_all() -> None:
    test_v227_default_config_is_safe_no_click()
    print("[RESULT] OK: V2.2.7 preflop arming config flags default-safe tests passed.")


if __name__ == "__main__":
    run_all()
