from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "controlled_test_click_runner_v1"
FEATURE_VERSION = "controlled_test_click_runner_v2_9"
DEFAULT_TABLE_ID = "table_01"
DEFAULT_MAX_CLICKS_PER_RUN = 1
ALLOWED_ACTIONS = ("fold", "check", "call", "check_fold")
ALLOWED_BUTTONS = ("FOLD", "Check", "Call", "Check/fold")
CONFIRMATION_TOKEN = "TEST_ENVIRONMENT_ONLY"
DETECTED_BUTTON_CONFIRMATION_TOKEN = "DETECTED_BUTTON_ROI_ONLY"


@dataclass(frozen=True)
class TestClickCandidate:
    table_id: str
    action: str
    button: str
    x: int
    y: int
    max_clicks_per_run: int = DEFAULT_MAX_CLICKS_PER_RUN
    source: str = "manual_test_candidate"
    decision_id: str = ""
    source_json_path: str = ""
    roi_guard_ok: bool = False
    inside_slot_bbox: bool = False


def _normalise_action(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace("/", "_")


def _normalise_button(value: str) -> str:
    raw = str(value or "").strip()
    aliases = {
        "fold": "FOLD",
        "check": "Check",
        "call": "Call",
        "check/fold": "Check/fold",
        "check_fold": "Check/fold",
        "check-fold": "Check/fold",
    }
    return aliases.get(raw.lower(), raw)


def _safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else str(value).strip().lower() in {"1", "true", "yes", "ok"}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "PokerVision V2.9 controlled test-environment click runner. "
            "Can click once only when test-environment gates and detected-button ROI audit are explicit."
        )
    )
    parser.add_argument("--table", "--table-id", dest="table_id", default=DEFAULT_TABLE_ID)
    parser.add_argument("--action", default="fold", help="Allowed: fold/check/call/check_fold")
    parser.add_argument("--button", default="FOLD", help="Allowed: FOLD/Check/Call/Check/fold")
    parser.add_argument("--x", type=int, default=None, help="Screen X coordinate for test click.")
    parser.add_argument("--y", type=int, default=None, help="Screen Y coordinate for test click.")
    parser.add_argument("--bbox", default=None, help="Optional bbox x1,y1,x2,y2. Center is used if x/y omitted.")
    parser.add_argument("--max-clicks-per-run", type=int, default=DEFAULT_MAX_CLICKS_PER_RUN)

    parser.add_argument(
        "--from-dark-json",
        default="",
        help="Build the click candidate from a live Dark_JSON action_button click point.",
    )
    parser.add_argument(
        "--latest-dark-json",
        action="store_true",
        help="Find the newest Dark_JSON under --dark-json-root and build candidate from it.",
    )
    parser.add_argument(
        "--dark-json-root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle" / "Dark_JSON"),
        help="Root used by --latest-dark-json.",
    )
    parser.add_argument(
        "--detected-button-candidate",
        action="store_true",
        help="Required for V2.9 detected-button ROI candidates.",
    )
    parser.add_argument(
        "--confirm-detected-button",
        default="",
        help=f"Must equal {DETECTED_BUTTON_CONFIRMATION_TOKEN!r} for detected-button real-click mode.",
    )

    parser.add_argument("--test-environment", action="store_true", help="Required for every ready state.")
    parser.add_argument(
        "--confirm-test-click",
        default="",
        help=f"Must equal {CONFIRMATION_TOKEN!r}.",
    )
    parser.add_argument(
        "--real-test-click",
        action="store_true",
        help="Actually move/click mouse. Requires POKERVISION_TEST_ENVIRONMENT=1.",
    )
    parser.add_argument(
        "--manual-controlled-snapshot",
        action="store_true",
        help="Use the manual controlled table/action/max-click snapshot for legacy V1.6 smoke checks.",
    )
    parser.add_argument(
        "--output",
        default=str(Path("outputs") / "controlled_test_click" / "controlled_test_click_result.json"),
        help="Where to write audit JSON.",
    )
    parser.add_argument("--no-json-print", action="store_true", help="Do not print the final JSON payload.")
    return parser


def parse_bbox_center(raw_bbox: Optional[str]) -> Tuple[Optional[int], Optional[int], List[str]]:
    if not raw_bbox:
        return None, None, []
    parts = [p.strip() for p in str(raw_bbox).replace(";", ",").split(",") if p.strip()]
    if len(parts) != 4:
        return None, None, ["invalid_bbox_format_expected_x1_y1_x2_y2"]
    values = [_safe_int(p) for p in parts]
    if any(v is None for v in values):
        return None, None, ["invalid_bbox_contains_non_integer"]
    x1, y1, x2, y2 = values  # type: ignore[misc]
    if x2 <= x1 or y2 <= y1:
        return None, None, ["invalid_bbox_geometry"]
    return int((x1 + x2) / 2), int((y1 + y2) / 2), []


def _load_json_file(path: Path) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return None, [f"dark_json_read_failed:{type(exc).__name__}:{exc}"]
    if not isinstance(payload, dict):
        return None, ["dark_json_root_must_be_object"]
    return payload, []


def _find_latest_dark_json(root: Path) -> Tuple[Optional[Path], List[str]]:
    if not root.exists():
        return None, [f"dark_json_root_not_found:{root}"]
    candidates = [p for p in root.rglob("*.dark.json") if p.is_file()]
    if not candidates:
        return None, [f"dark_json_not_found_under:{root}"]
    return max(candidates, key=lambda p: p.stat().st_mtime), []


def _dict_at(payload: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return {}
        cur = cur.get(key)
    return cur if isinstance(cur, dict) else {}


def _list_at(payload: Dict[str, Any], *keys: str) -> List[Any]:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return []
        cur = cur.get(key)
    return cur if isinstance(cur, list) else []


def _extract_detected_button_candidate_from_dark_json(path: Path) -> Tuple[Optional[TestClickCandidate], List[str], Dict[str, Any]]:
    dark, errors = _load_json_file(path)
    if dark is None:
        return None, errors, {"source_json_path": str(path)}

    runtime_action = _dict_at(dark, "runtime_action")
    action_button = _dict_at(runtime_action, "action_button")
    roi_guard = _dict_at(action_button, "action_button_slot_roi_guard")
    click_points = _list_at(action_button, "click_points")

    blockers: List[str] = []
    audit: Dict[str, Any] = {
        "source_json_path": str(path),
        "runtime_action_present": bool(runtime_action),
        "action_button_present": bool(action_button),
        "roi_guard_present": bool(roi_guard),
        "click_points_count": len(click_points),
        "roi_guard_status": roi_guard.get("status"),
        "roi_guard_ok": bool(roi_guard.get("ok")) if roi_guard else False,
        "full_screen_search_blocked": bool(roi_guard.get("full_screen_search_blocked")) if roi_guard else False,
        "audit_exposure_version": roi_guard.get("audit_exposure_version") if roi_guard else None,
    }

    if not action_button:
        blockers.append("runtime_action_action_button_missing")
    if not roi_guard:
        blockers.append("action_button_slot_roi_guard_missing")
    else:
        if not bool(roi_guard.get("ok")):
            blockers.append("action_button_slot_roi_guard_not_ok")
        if not bool(roi_guard.get("full_screen_search_blocked")):
            blockers.append("full_screen_search_not_confirmed_blocked")
        if str(roi_guard.get("detector_input_scope") or "") != "table_roi":
            blockers.append("detector_input_scope_must_be_table_roi")
    if not click_points:
        blockers.append("no_action_button_click_points_in_dark_json")

    point: Dict[str, Any] = {}
    for item in click_points:
        if isinstance(item, dict):
            button = _normalise_button(str(item.get("class_name") or ""))
            if button in ALLOWED_BUTTONS:
                point = item
                break
    if click_points and not point:
        blockers.append("no_allowed_simple_button_click_point_found")

    global_point = point.get("global_click_point") if isinstance(point.get("global_click_point"), dict) else {}
    x = _safe_int(global_point.get("x"))
    y = _safe_int(global_point.get("y"))
    if point and (x is None or y is None):
        blockers.append("missing_global_click_point_xy")
    if point and not bool(point.get("inside_slot_bbox", False)):
        blockers.append("click_point_not_inside_slot_bbox")

    table_id = (
        str(_dict_at(dark, "table").get("table_id") or roi_guard.get("table_id") or DEFAULT_TABLE_ID).strip()
    )
    action = _normalise_action(
        str(
            action_button.get("solver_action")
            or action_button.get("action")
            or _dict_at(runtime_action, "click").get("action")
            or "fold"
        )
    )
    button = _normalise_button(str(point.get("class_name") or "")) if point else ""
    decision_id = str(
        action_button.get("decision_id")
        or _dict_at(runtime_action, "click").get("decision_id")
        or _dict_at(dark, "action_event_gate").get("action_event_id")
        or ""
    )

    candidate = None
    if not blockers and x is not None and y is not None:
        candidate = TestClickCandidate(
            table_id=table_id,
            action=action,
            button=button,
            x=int(x),
            y=int(y),
            max_clicks_per_run=DEFAULT_MAX_CLICKS_PER_RUN,
            source="detected_action_button_dark_json",
            decision_id=decision_id,
            source_json_path=str(path),
            roi_guard_ok=True,
            inside_slot_bbox=True,
        )

    audit.update(
        {
            "selected_button": button,
            "selected_action": action,
            "selected_x": x,
            "selected_y": y,
            "selected_table_id": table_id,
            "selected_decision_id": decision_id,
            "blockers": list(blockers),
        }
    )
    return candidate, blockers, audit


def _resolve_dark_json_path_from_args(args: argparse.Namespace) -> Tuple[Optional[Path], List[str]]:
    from_dark_json = str(getattr(args, "from_dark_json", "") or "").strip()
    if from_dark_json:
        return Path(from_dark_json), []
    if bool(getattr(args, "latest_dark_json", False)):
        return _find_latest_dark_json(Path(str(getattr(args, "dark_json_root", "") or "")))
    return None, []


def build_candidate_from_args(args: argparse.Namespace) -> Tuple[Optional[TestClickCandidate], List[str]]:
    candidate, errors, _audit = build_candidate_and_audit_from_args(args)
    return candidate, errors


def build_candidate_and_audit_from_args(args: argparse.Namespace) -> Tuple[Optional[TestClickCandidate], List[str], Dict[str, Any]]:
    dark_json_path, path_errors = _resolve_dark_json_path_from_args(args)
    if path_errors:
        return None, path_errors, {"source": "dark_json_path_resolution", "blockers": path_errors}

    if dark_json_path is not None:
        candidate, candidate_errors, audit = _extract_detected_button_candidate_from_dark_json(dark_json_path)
        candidate_errors = list(candidate_errors)

        if not bool(getattr(args, "detected_button_candidate", False)):
            candidate_errors.append("detected_button_candidate_flag_required")
        if str(getattr(args, "confirm_detected_button", "") or "").strip() != DETECTED_BUTTON_CONFIRMATION_TOKEN:
            candidate_errors.append("confirm_detected_button_token_required")
        if candidate is not None and candidate.table_id != str(getattr(args, "table_id", DEFAULT_TABLE_ID) or DEFAULT_TABLE_ID):
            candidate_errors.append("candidate_table_id_must_match_requested_table")

        audit["blockers"] = list(dict.fromkeys([str(x) for x in candidate_errors]))
        return (candidate if not candidate_errors else None), audit["blockers"], audit

    blockers: List[str] = []
    table_id = str(getattr(args, "table_id", "") or "").strip()
    action = _normalise_action(getattr(args, "action", ""))
    button = _normalise_button(getattr(args, "button", ""))
    max_clicks = _safe_int(getattr(args, "max_clicks_per_run", None), DEFAULT_MAX_CLICKS_PER_RUN)

    x = getattr(args, "x", None)
    y = getattr(args, "y", None)
    if x is None or y is None:
        bx, by, bbox_errors = parse_bbox_center(getattr(args, "bbox", None))
        blockers.extend(bbox_errors)
        if x is None:
            x = bx
        if y is None:
            y = by

    x = _safe_int(x)
    y = _safe_int(y)

    if not table_id:
        blockers.append("missing_table_id")
    if action not in ALLOWED_ACTIONS:
        blockers.append("action_not_allowed_for_controlled_test_click")
    if button not in ALLOWED_BUTTONS:
        blockers.append("button_not_allowed_for_controlled_test_click")
    if max_clicks != DEFAULT_MAX_CLICKS_PER_RUN:
        blockers.append("max_clicks_per_run_must_be_1")
    if x is None or y is None:
        blockers.append("missing_click_coordinates")
    elif x < 0 or y < 0:
        blockers.append("click_coordinates_must_be_non_negative")

    audit = {
        "source": "manual_test_candidate",
        "blockers": list(blockers),
    }
    if blockers:
        return None, blockers, audit

    return TestClickCandidate(
        table_id=table_id,
        action=action,
        button=button,
        x=int(x),
        y=int(y),
        max_clicks_per_run=int(max_clicks),
        source="manual_test_candidate",
    ), [], audit



def _candidate_to_json(candidate: Optional[TestClickCandidate]) -> Optional[Dict[str, Any]]:
    if candidate is None:
        return None
    payload = asdict(candidate)
    if candidate.source == "manual_test_candidate":
        return {
            "table_id": payload["table_id"],
            "action": payload["action"],
            "button": payload["button"],
            "x": payload["x"],
            "y": payload["y"],
            "max_clicks_per_run": payload["max_clicks_per_run"],
            "source": payload["source"],
        }
    return payload


def validate_v16_test_click_scope(
    args: argparse.Namespace,
    candidate: Optional[TestClickCandidate],
    candidate_errors: Iterable[str],
    environ: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    env = dict(os.environ if environ is None else environ)
    blockers: List[str] = list(candidate_errors)

    test_environment = bool(getattr(args, "test_environment", False))
    confirmation = str(getattr(args, "confirm_test_click", "") or "").strip()
    real_test_click = bool(getattr(args, "real_test_click", False))
    manual_snapshot = bool(getattr(args, "manual_controlled_snapshot", False))
    detected_button_candidate = bool(getattr(args, "detected_button_candidate", False))

    if not test_environment:
        blockers.append("test_environment_flag_required")
    if confirmation != CONFIRMATION_TOKEN:
        blockers.append("confirm_test_click_token_required")

    if candidate is not None:
        if candidate.table_id != DEFAULT_TABLE_ID:
            blockers.append("controlled_table_must_be_table_01")
        if candidate.max_clicks_per_run != DEFAULT_MAX_CLICKS_PER_RUN:
            blockers.append("max_clicks_per_run_must_be_1")
        if candidate.action not in ALLOWED_ACTIONS:
            blockers.append("action_not_allowed_for_controlled_test_click")
        if candidate.button not in ALLOWED_BUTTONS:
            blockers.append("button_not_allowed_for_controlled_test_click")
        if candidate.source == "detected_action_button_dark_json":
            if not candidate.roi_guard_ok:
                blockers.append("detected_button_roi_guard_must_be_ok")
            if not candidate.inside_slot_bbox:
                blockers.append("detected_button_click_point_must_be_inside_slot")
            if not candidate.decision_id:
                blockers.append("detected_button_decision_id_required")

    if real_test_click and env.get("POKERVISION_TEST_ENVIRONMENT") != "1":
        blockers.append("env_POKERVISION_TEST_ENVIRONMENT_must_equal_1_for_real_test_click")

    # Legacy V1.6 path still requires a manual snapshot. V2.9 detected-button
    # path requires the detected-button flags instead and never allows service/UI clicks.
    if candidate is not None and candidate.source == "detected_action_button_dark_json":
        if not detected_button_candidate:
            blockers.append("detected_button_candidate_flag_required")
    elif not manual_snapshot:
        blockers.append("manual_controlled_snapshot_required_for_manual_candidate")

    ready = len(blockers) == 0
    status = "CONTROLLED_TEST_CLICK_READY" if ready else "CONTROLLED_TEST_CLICK_BLOCKED"

    return {
        "schema_version": SCHEMA_VERSION,
        "feature_version": FEATURE_VERSION,
        "ready": ready,
        "status": status,
        "blockers": list(dict.fromkeys(str(x) for x in blockers)),
        "test_environment": test_environment,
        "manual_controlled_snapshot": manual_snapshot,
        "detected_button_candidate": detected_button_candidate,
        "real_test_click_requested": real_test_click,
        "click_execution": "not_started",
        "allowed_actions": list(ALLOWED_ACTIONS),
        "allowed_buttons": list(ALLOWED_BUTTONS),
        "candidate": _candidate_to_json(candidate),
        "max_clicks_per_run": DEFAULT_MAX_CLICKS_PER_RUN,
    }


def _default_pyautogui_click(x: int, y: int) -> Dict[str, Any]:
    import pyautogui  # type: ignore

    pyautogui.moveTo(x, y, duration=0.18)
    pyautogui.click(x=x, y=y)
    return {"backend": "pyautogui", "clicked": True, "x": x, "y": y}


def execute_test_click_candidate(
    args: argparse.Namespace,
    click_executor: Optional[Callable[[int, int], Dict[str, Any]]] = None,
    environ: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    candidate, candidate_errors, candidate_audit = build_candidate_and_audit_from_args(args)
    result = validate_v16_test_click_scope(args, candidate, candidate_errors, environ=environ)

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    result["created_at_local"] = timestamp
    result["candidate_build_audit"] = candidate_audit
    result["controlled_detected_button_click_audit"] = {
        "schema_version": "controlled_detected_button_click_v2_9",
        "enabled": True,
        "source": (candidate.source if candidate is not None else candidate_audit.get("source")),
        "max_clicks_per_run": DEFAULT_MAX_CLICKS_PER_RUN,
        "service_click_disabled": True,
        "raise_or_size_buttons_disabled": True,
        "full_screen_search_blocked_required": True,
        "roi_guard_ok_required": True,
        "allowed_buttons": list(ALLOWED_BUTTONS),
    }

    if not result["ready"]:
        result["click_execution"] = "blocked"
        result["clicked"] = False
        return result

    if not bool(getattr(args, "real_test_click", False)):
        result["click_execution"] = "dry_run_candidate_recorded"
        result["clicked"] = False
        return result

    assert candidate is not None
    executor = click_executor or _default_pyautogui_click
    try:
        click_result = executor(candidate.x, candidate.y)
        result["click_execution"] = "clicked_in_test_environment"
        result["clicked"] = True
        result["click_result"] = click_result
    except Exception as exc:
        result["ready"] = False
        result["status"] = "CONTROLLED_TEST_CLICK_FAILED"
        result["click_execution"] = "failed"
        result["clicked"] = False
        result["blockers"] = list(result.get("blockers", [])) + [f"click_executor_failed:{type(exc).__name__}:{exc}"]
    return result


def write_result_json(result: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    result = execute_test_click_candidate(args)
    output_path = Path(getattr(args, "output", "outputs/controlled_test_click/controlled_test_click_result.json"))
    write_result_json(result, output_path)

    blockers = result.get("blockers") or []
    print(f"CONTROLLED_TEST_CLICK_READY = {str(bool(result.get('ready'))).lower()}")
    print(f"CONTROLLED_TEST_CLICK_STATUS = {result.get('status')}")
    print("CONTROLLED_TEST_CLICK_BLOCKERS = " + ("none" if not blockers else ",".join(map(str, blockers))))
    print(f"CONTROLLED_TEST_CLICK_EXECUTION = {result.get('click_execution')}")
    print(f"CONTROLLED_TEST_CLICK_RESULT_JSON = {output_path}")

    if not getattr(args, "no_json_print", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))

    return 0 if bool(result.get("ready")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
