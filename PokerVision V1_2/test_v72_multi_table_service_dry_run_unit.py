from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, Tuple

from PIL import Image

from runtime.trigger_ui_service_runtime import run_v11_trigger_ui_service_runtime


def _slot(table_id: str) -> Any:
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


def _state_for(*, table_id: str, class_name: str) -> Dict[str, Any]:
    detections = [_detection("Remove_Table")]
    if class_name != "Remove_Table":
        detections.insert(0, _detection(class_name))

    detected_classes = [d["class_name"] for d in detections]
    best_by_class = {d["class_name"]: d for d in detections}

    return {
        "frame_id": f"v72_{table_id}_{class_name}",
        "frame_name": f"v72_{table_id}_{class_name}",
        "table_id": table_id,
        "hand_id": f"{table_id}_service_smoke",
        "table": {
            "table_id": table_id,
            "hand_id": f"{table_id}_service_smoke",
            "frame_name": f"v72_{table_id}_{class_name}",
        },
        "trigger_ui": {
            "detected_classes": detected_classes,
            "classes": best_by_class,
            "best_by_class": best_by_class,
        },
    }


def _run_service_case(*, table_id: str, class_name: str) -> Dict[str, Any]:
    state = _state_for(table_id=table_id, class_name=class_name)
    report = run_v11_trigger_ui_service_runtime(
        full_state=state,
        table_roi_image=Image.new("RGB", (800, 600), (0, 0, 0)),
        slot=_slot(table_id),
        trigger_best_by_class=state["trigger_ui"]["best_by_class"],
        cycle_dir=None,
    )
    service = report.get("service_click", {}) if isinstance(report, dict) else {}
    return {
        "table_id": table_id,
        "class_name": class_name,
        "status": service.get("status"),
        "target_class": service.get("target_class"),
        "target_sequence": service.get("target_sequence"),
        "dry_run": service.get("dry_run"),
        "real_click_enabled": service.get("real_click_enabled"),
        "frame_finished": service.get("frame_finished"),
        "skip_action_button_runtime": service.get("skip_action_button_runtime"),
        "click_points_count": len(service.get("click_points") or []),
        "raw": report,
    }


def test_multi_table_service_dry_run_contract() -> None:
    cases = [
        _run_service_case(table_id="table_01", class_name="Exit_cashOut"),
        _run_service_case(table_id="table_02", class_name="1_roll_board"),
        _run_service_case(table_id="table_03", class_name="Remove_Game"),
        _run_service_case(table_id="table_04", class_name="Non_active_fold"),
        _run_service_case(table_id="table_05", class_name="True_active_fold"),
        _run_service_case(table_id="table_06", class_name="Remove_Table"),
    ]

    by_table = {case["table_id"]: case for case in cases}

    assert by_table["table_01"]["status"] == "dry_run"
    assert by_table["table_01"]["target_class"] == "Exit_cashOut"
    assert by_table["table_01"]["click_points_count"] == 1

    assert by_table["table_02"]["status"] == "dry_run"
    assert by_table["table_02"]["target_class"] == "1_roll_board"
    assert by_table["table_02"]["click_points_count"] == 1

    assert by_table["table_03"]["status"] == "dry_run"
    assert by_table["table_03"]["target_class"] == "Remove_Game"
    assert by_table["table_03"]["click_points_count"] == 1

    # Without HERO/death-card proof Non_active_fold is only a marker, not a click.
    assert by_table["table_04"]["status"] == "skipped"
    assert by_table["table_04"]["target_class"] == "Non_active_fold"
    assert by_table["table_04"]["click_points_count"] == 0

    assert by_table["table_05"]["status"] == "confirmed"
    assert by_table["table_05"]["target_class"] in {None, ""}
    assert by_table["table_05"]["click_points_count"] == 0
    assert by_table["table_05"]["skip_action_button_runtime"] is True

    assert by_table["table_06"]["status"] == "detected_only"
    assert by_table["table_06"]["target_class"] in {None, ""}
    assert by_table["table_06"]["click_points_count"] == 0

    for case in cases:
        assert case["table_id"].startswith("table_")
        assert case["real_click_enabled"] is False, case


def main() -> int:
    test_multi_table_service_dry_run_contract()
    print("[RESULT] OK: PokerVision V7.2 multi-table service dry-run contract tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
