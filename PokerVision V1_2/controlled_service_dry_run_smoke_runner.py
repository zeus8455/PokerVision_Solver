from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Tuple

from PIL import Image

from runtime.trigger_ui_service_runtime import run_v11_trigger_ui_service_runtime


SCHEMA_VERSION = "controlled_service_dry_run_smoke_runner_v1"

SERVICE_CLASSES = [
    "Exit_cashOut",
    "1_roll_board",
    "Remove_Game",
    "Non_active_fold",
    "True_active_fold",
    "Remove_Table",
]


def _slot(table_id: str = "table_01") -> Any:
    return SimpleNamespace(
        table_id=table_id,
        bbox=SimpleNamespace(x1=100, y1=100, x2=900, y2=700),
    )


def _detection(class_name: str, bbox: Tuple[int, int, int, int] = (120, 120, 220, 170)) -> Dict[str, Any]:
    return {
        "class_name": class_name,
        "confidence": 0.95,
        "bbox_xyxy": list(bbox),
    }


def _state_for(class_name: str) -> Dict[str, Any]:
    detections = [_detection("Remove_Table")]

    if class_name != "Remove_Table":
        detections.insert(0, _detection(class_name))

    detected_classes = [d["class_name"] for d in detections]
    best_by_class = {d["class_name"]: d for d in detections}

    return {
        "frame_id": f"v68_{class_name}",
        "frame_name": f"v68_{class_name}",
        "table_id": "table_01",
        "hand_id": "service_smoke",
        "table": {
            "table_id": "table_01",
            "hand_id": "service_smoke",
            "frame_name": f"v68_{class_name}",
        },
        "trigger_ui": {
            "detected_classes": detected_classes,
            "classes": best_by_class,
            "best_by_class": best_by_class,
        },
    }


def run_case(class_name: str) -> Dict[str, Any]:
    state = _state_for(class_name)

    trigger_best_by_class = state["trigger_ui"]["best_by_class"]

    report = run_v11_trigger_ui_service_runtime(
        full_state=state,
        table_roi_image=Image.new("RGB", (800, 600), (0, 0, 0)),
        slot=_slot("table_01"),
        trigger_best_by_class=trigger_best_by_class,
        cycle_dir=None,
    )

    service = report.get("service_click", {}) if isinstance(report, dict) else {}

    return {
        "class_name": class_name,
        "status": service.get("status"),
        "target_class": service.get("target_class"),
        "target_sequence": service.get("target_sequence"),
        "dry_run": service.get("dry_run"),
        "real_click_enabled": service.get("real_click_enabled"),
        "frame_finished": service.get("frame_finished"),
        "skip_action_button_runtime": service.get("skip_action_button_runtime"),
        "click_points_count": len(service.get("click_points") or []),
        "guard_passed": service.get("guard_passed"),
        "message": service.get("message"),
        "raw": report,
    }


def run_all() -> Dict[str, Any]:
    cases = [run_case(class_name) for class_name in SERVICE_CLASSES]
    errors: List[str] = []

    expected_targets = {
        "Exit_cashOut": "Exit_cashOut",
        "1_roll_board": "1_roll_board",
        "Remove_Game": "Remove_Game",
    }

    by_class = {case["class_name"]: case for case in cases}

    for class_name, target in expected_targets.items():
        case = by_class[class_name]
        if case["status"] != "dry_run":
            errors.append(f"{class_name}: expected dry_run, got {case['status']!r}")
        if case["target_class"] != target:
            errors.append(f"{class_name}: expected target {target!r}, got {case['target_class']!r}")
        if case["target_sequence"] != [target]:
            errors.append(f"{class_name}: unexpected target_sequence {case['target_sequence']!r}")
        if case["click_points_count"] != 1:
            errors.append(f"{class_name}: expected 1 click point, got {case['click_points_count']!r}")
        if case["real_click_enabled"] is not False:
            errors.append(f"{class_name}: real_click_enabled must be false")
        if case["dry_run"] is not True:
            errors.append(f"{class_name}: dry_run must be true")

    non_active = by_class["Non_active_fold"]
    if non_active["status"] != "skipped":
        errors.append(f"Non_active_fold without HERO/death-card match: expected skipped, got {non_active['status']!r}")
    if non_active["target_class"] != "Non_active_fold":
        errors.append(f"Non_active_fold: expected target marker Non_active_fold, got {non_active['target_class']!r}")
    if non_active["click_points_count"] != 0:
        errors.append(f"Non_active_fold without HERO/death-card match: expected 0 click points, got {non_active['click_points_count']!r}")
    if non_active["real_click_enabled"] is not False:
        errors.append("Non_active_fold: real_click_enabled must be false")

    true_active = by_class["True_active_fold"]
    if true_active["status"] != "confirmed":
        errors.append(f"True_active_fold: expected confirmed, got {true_active['status']!r}")
    if true_active["target_class"] not in {None, ""}:
        errors.append(f"True_active_fold: target_class must be empty, got {true_active['target_class']!r}")
    if true_active["click_points_count"] != 0:
        errors.append(f"True_active_fold: expected 0 click points, got {true_active['click_points_count']!r}")
    if true_active["skip_action_button_runtime"] is not True:
        errors.append("True_active_fold: skip_action_button_runtime must be true")

    remove_table = by_class["Remove_Table"]
    if remove_table["status"] != "detected_only":
        errors.append(f"Remove_Table: expected detected_only, got {remove_table['status']!r}")
    if remove_table["target_class"] not in {None, ""}:
        errors.append(f"Remove_Table: target_class must be empty, got {remove_table['target_class']!r}")
    if remove_table["click_points_count"] != 0:
        errors.append(f"Remove_Table: expected 0 click points, got {remove_table['click_points_count']!r}")

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok" if not errors else "fail",
        "errors": errors,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PokerVision V6.8 controlled service dry-run smoke runner.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()

    report = run_all()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for case in report["cases"]:
            print(
                f"{case['class_name']}: status={case['status']} "
                f"target={case['target_class']} points={case['click_points_count']} "
                f"realclick={case['real_click_enabled']}"
            )
        print(f"[RESULT] {'OK' if report['status'] == 'ok' else 'FAIL'}: PokerVision V6.8 controlled service dry-run smoke runner")

    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
