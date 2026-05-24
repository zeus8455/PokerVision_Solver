from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
REPORT_PATH = REPO_ROOT / "Script_Test_PokerVision_All_files" / "Test_Replay_Output" / "reports" / "image_replay_report.json"


EXPECTED_SERVICE_TARGETS: Dict[str, str] = {
    "hand_10.png": "Exit_cashOut",
    "hand_11.png": "1_roll_board",
    "hand_13.png": "Remove_Game",
    "hand_14.png": "Non_active_fold",
}


def _run_replay_real_service_dry_run() -> None:
    cmd = [
        sys.executable,
        str(ROOT / "test_image_replay_cycle_v12.py"),
        "--real-service-dry-run",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT))
    assert proc.returncode == 0, f"real-service dry-run replay failed with rc={proc.returncode}"


def _load_report() -> Dict[str, Any]:
    assert REPORT_PATH.exists(), f"missing replay report: {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_real_service_dry_run_targets_are_expected() -> None:
    _run_replay_real_service_dry_run()
    report = _load_report()

    assert int(report.get("errors_total", -1)) == 0, report
    assert int(report.get("runtime_real_click_enabled_total", -1)) == 0, report
    assert int(report.get("runtime_click_points_total", -1)) == 4, report

    results = {item.get("image_name"): item for item in report.get("results", [])}
    for image_name, expected_target in EXPECTED_SERVICE_TARGETS.items():
        item = results.get(image_name)
        assert item, f"missing replay result for {image_name}"

        extracted = item.get("extracted") or {}
        assert item.get("status") == "ok", item
        assert extracted.get("runtime_service_status") == "dry_run", item
        assert extracted.get("runtime_service_target_class") == expected_target, item
        assert extracted.get("runtime_service_target_sequence") == [expected_target], item
        assert extracted.get("runtime_service_dry_run") is True, item
        assert extracted.get("runtime_service_real_click_enabled") is False, item
        assert extracted.get("runtime_service_click_points_count") == 1, item

        trigger_classes = extracted.get("runtime_trigger_classes") or []
        assert "Remove_Table" in trigger_classes, item
        assert extracted.get("runtime_service_target_class") != "Remove_Table", item

    non_active_fold = results["hand_14.png"]["extracted"]
    assert non_active_fold.get("runtime_service_skip_action_button_runtime") is True, non_active_fold


    true_active_fold = results["hand_15.png"]["extracted"]
    assert true_active_fold.get("runtime_service_status") == "confirmed", true_active_fold
    assert true_active_fold.get("runtime_service_target_class") in {None, ""}, true_active_fold
    assert true_active_fold.get("runtime_service_click_points_count") == 0, true_active_fold
    assert true_active_fold.get("runtime_service_skip_action_button_runtime") is True, true_active_fold

    for image_name in ["hand_10.png", "hand_11.png", "hand_13.png", "hand_14.png", "hand_15.png"]:
        extracted = results[image_name].get("extracted") or {}
        assert not extracted.get("decision_json_path"), (image_name, extracted)
        assert not extracted.get("action_decision_json_path"), (image_name, extracted)
        assert not extracted.get("action_runtime_plan_json_path"), (image_name, extracted)
        assert extracted.get("runtime_action_button_status") == "skipped", (image_name, extracted)
        assert extracted.get("runtime_action_button_click_points_count") == 0, (image_name, extracted)


def main() -> int:
    test_real_service_dry_run_targets_are_expected()
    print("[RESULT] OK: PokerVision V6.6 real service dry-run replay contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
