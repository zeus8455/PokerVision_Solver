r"""
test_v40_duplicate_active_hard_stop_unit.py

PokerVision V4.0 — duplicate Active hard-stop before Pending/Decision.

Contract:
- duplicate_active_frame_blocked Active frames are preserved as Dark_JSON audit;
- they must not create Clear_JSON_Pending;
- they must not create Decision_JSON / Action_Decision_JSON / Action_Runtime_Plan_JSON.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from display_analysis_cycle import save_dark_and_clear_table_frame_json


SUPPRESSED_DIRS = (
    "Clear_JSON_Pending",
    "Clear_JSON",
    "Decision_JSON",
    "Action_Decision_JSON",
    "Action_Runtime_Plan_JSON",
)


def _json_files(root: Path, dirname: str) -> list[Path]:
    path = root / dirname
    if not path.exists():
        return []
    return sorted(path.rglob("*.json"))


def test_duplicate_active_hard_stop_saves_dark_json_only() -> None:
    with tempfile.TemporaryDirectory(prefix="pokervision_v40_duplicate_hard_stop_") as tmp:
        cycle_dir = Path(tmp) / "current_cycle"
        state = {
            "schema_version": "test",
            "frame_id": "table_01_hand_01_preflop_02",
            "frame_name": "hand_01_preflop_02",
            "table": {
                "table_id": "table_01",
                "action_event_id": None,
            },
            "runtime_event": {
                "reason": "duplicate_active_frame_blocked",
                "duplicate_of": "evt_table_01_previous",
            },
            "duplicate_active_hard_stop": {
                "schema_version": "duplicate_active_hard_stop_v4_0",
                "status": "DUPLICATE_ACTIVE_HARD_STOP_BEFORE_PENDING_DECISION",
                "reason": "duplicate_active_frame_blocked",
            },
        }

        dark_path, clear_path = save_dark_and_clear_table_frame_json(
            state=state,
            cycle_dir=cycle_dir,
            table_id="table_01",
            hand_id="hand_01",
            frame_name="hand_01_preflop_02",
            active_confirmed=True,
            clear_json_build_allowed=False,
            clear_json_build_block_reason="duplicate_active_frame_blocked",
            clear_json_save_allowed=False,
            click_result=None,
        )

        assert dark_path.exists(), dark_path
        assert clear_path is None

        for dirname in SUPPRESSED_DIRS:
            assert _json_files(cycle_dir, dirname) == [], f"{dirname} must not contain JSON files"

        with dark_path.open("r", encoding="utf-8") as f:
            dark = json.load(f)

        contract = dark.get("clear_json_contract")
        assert isinstance(contract, dict)
        assert contract.get("status") == "skipped"
        assert contract.get("reason") == "duplicate_active_frame_blocked"
        assert contract.get("publication_stage") == "dark_json_only"
        assert contract.get("hard_stop_before_pending_decision") is True
        assert contract.get("pending_path") is None
        assert contract.get("path") is None

        decision_contract = contract.get("decision_json_contract")
        assert isinstance(decision_contract, dict)
        assert decision_contract.get("status") == "not_built_duplicate_active_hard_stop"
        assert decision_contract.get("path") is None

        action_contract = contract.get("action_decision_contract")
        assert isinstance(action_contract, dict)
        assert action_contract.get("status") == "not_built_duplicate_active_hard_stop"
        assert action_contract.get("path") is None
        runtime_contract = action_contract.get("action_runtime_plan_contract")
        assert isinstance(runtime_contract, dict)
        assert runtime_contract.get("status") == "not_built_duplicate_active_hard_stop"
        assert runtime_contract.get("path") is None


def main() -> int:
    test_duplicate_active_hard_stop_saves_dark_json_only()
    print("[OK] test_duplicate_active_hard_stop_saves_dark_json_only")
    print("[RESULT] OK: PokerVision V4.0 duplicate Active hard-stop tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
