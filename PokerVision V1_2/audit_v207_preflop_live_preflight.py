from __future__ import annotations

"""
audit_v207_preflop_live_preflight.py

PokerVision Solver V2.0.7 — diagnostic-only preflop live preflight audit.

This script does not modify JSON files and does not click.
It audits replay output readiness for a future preflop-only real-click gate.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import config as c


DEFAULT_ROOT = Path(r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output")


REAL_CLICK_FLAG_NAMES = [
    "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE",
    "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY",
    "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK",
    "V11_CLICK_DRY_RUN",
    "V11_REAL_MOUSE_CLICK_ENABLED",
    "V11_TRIGGER_UI_SERVICE_DRY_RUN",
    "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED",
    "V09_REAL_CLICK_MASTER_ARMED",
    "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE",
]


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _iter_json_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return root.rglob("*.json")


def _street(payload: Dict[str, Any]) -> str | None:
    board = payload.get("board") if isinstance(payload.get("board"), dict) else {}
    value = board.get("street")
    return str(value).lower() if value else None


def _frame_id(payload: Dict[str, Any]) -> str:
    return str(payload.get("frame_id") or "")


def _is_clear_like(payload: Dict[str, Any]) -> bool:
    return isinstance(payload.get("board"), dict) and isinstance(payload.get("players"), dict)


def _runtime_action_from_clear(payload: Dict[str, Any]) -> str | None:
    preview = payload.get("engine_decision_preview")
    if isinstance(preview, dict):
        action = preview.get("engine_action")
        if action:
            return str(action)
    return None


def _node_type(payload: Dict[str, Any]) -> str | None:
    ctx = payload.get("engine_context")
    if isinstance(ctx, dict):
        value = ctx.get("node_type")
        return str(value) if value is not None else None
    return None


def _inference_source(payload: Dict[str, Any]) -> str | None:
    ctx = payload.get("engine_context")
    if not isinstance(ctx, dict):
        return None
    meta = ctx.get("meta")
    if not isinstance(meta, dict):
        return None
    value = meta.get("inference_source")
    return str(value) if value is not None else None


def _action_history(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    ctx = payload.get("engine_context")
    if not isinstance(ctx, dict):
        return []
    history = ctx.get("action_history")
    return [x for x in history if isinstance(x, dict)] if isinstance(history, list) else []


def _classify_preflop_raise(payload: Dict[str, Any]) -> str:
    node = _node_type(payload)
    history = _action_history(payload)
    preview = payload.get("engine_decision_preview") if isinstance(payload.get("engine_decision_preview"), dict) else {}
    reason = str(preview.get("reason") or "").lower()

    actions = [str(x.get("action") or "").lower() for x in history]

    if node == "cold_4bet" or "cold_4bet" in actions:
        return "cold_4bet"
    if node == "facing_limp":
        return "iso_raise_candidate"
    if "preflop:3bet" in reason or "3bet" in actions:
        return "threebet_candidate"
    if "open_raise" in actions:
        return "open_raise_or_vs_open"
    return "unknown_raise"


def _safe_config_report() -> Tuple[Dict[str, Any], List[str]]:
    flags = {name: getattr(c, name, None) for name in REAL_CLICK_FLAG_NAMES}
    errors: List[str] = []

    expected = {
        "V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE": True,
        "V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY": True,
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": False,
        "V11_CLICK_DRY_RUN": True,
        "V11_REAL_MOUSE_CLICK_ENABLED": False,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
        "V09_REAL_CLICK_MASTER_ARMED": False,
        "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": True,
    }

    for name, expected_value in expected.items():
        actual = flags.get(name)
        if actual is not expected_value:
            errors.append(f"{name} expected {expected_value!r}, got {actual!r}")

    return flags, errors


def audit(root: Path = DEFAULT_ROOT) -> Dict[str, Any]:
    config_flags, config_errors = _safe_config_report()

    counters = Counter()
    node_counter = Counter()
    inference_counter = Counter()
    action_counter = Counter()
    raise_class_counter = Counter()
    examples = defaultdict(list)
    errors: List[str] = []

    for path in _iter_json_files(root):
        if "Clear_JSON_Pending" in path.parts:
            counters["pending_clear_json_skipped"] += 1
            continue

        payload = _read_json(path)
        if not payload or not _is_clear_like(payload):
            continue

        counters["clear_like_json"] += 1

        street = _street(payload)
        frame_id = _frame_id(payload)

        if street == "preflop":
            counters["preflop_clear_like"] += 1

            ctx = payload.get("engine_context")
            preview = payload.get("engine_decision_preview")

            if not isinstance(ctx, dict):
                counters["preflop_missing_engine_context"] += 1
                errors.append(f"{frame_id}: missing engine_context: {path}")
                continue

            if not isinstance(preview, dict):
                counters["preflop_missing_engine_decision_preview"] += 1
                errors.append(f"{frame_id}: missing engine_decision_preview: {path}")
                continue

            node = _node_type(payload)
            source = _inference_source(payload)
            action = _runtime_action_from_clear(payload)

            node_counter[node] += 1
            inference_counter[source] += 1
            action_counter[action] += 1

            if source != "preflop_action_model_builder":
                counters["preflop_bad_or_missing_inference_source"] += 1
                errors.append(f"{frame_id}: bad inference_source={source!r}: {path}")

            if action in {"raise", "bet", "bet_raise"}:
                raise_class = _classify_preflop_raise(payload)
                raise_class_counter[raise_class] += 1
                if len(examples[raise_class]) < 5:
                    examples[raise_class].append({
                        "frame_id": frame_id,
                        "path": str(path),
                        "node_type": node,
                        "action": action,
                        "history": _action_history(payload),
                    })

        elif street in {"flop", "turn", "river"}:
            counters["postflop_clear_like"] += 1
        else:
            counters["service_or_unknown_clear_like"] += 1

    return {
        "root": str(root),
        "config_flags": config_flags,
        "config_errors": config_errors,
        "counters": dict(counters),
        "node_counter": dict(node_counter),
        "inference_counter": dict(inference_counter),
        "action_counter": dict(action_counter),
        "raise_class_counter": dict(raise_class_counter),
        "raise_examples": dict(examples),
        "errors": errors,
        "ok": not config_errors and not errors,
    }


def main() -> None:
    report = audit()

    print("V2.0.7 PREFLOP LIVE PREFLIGHT AUDIT")
    print("=" * 100)

    print()
    print("CONFIG_FLAGS:")
    for name, value in report["config_flags"].items():
        print(f"  {name} = {value!r}")

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("NODE_COUNTER:", report["node_counter"])
    print("INFERENCE_COUNTER:", report["inference_counter"])
    print("ACTION_COUNTER:", report["action_counter"])
    print("RAISE_CLASS_COUNTER:", report["raise_class_counter"])

    print()
    print("RAISE_EXAMPLES:")
    for key, rows in report["raise_examples"].items():
        print(f"  {key}:")
        for row in rows:
            print(f"    - frame_id={row['frame_id']} node={row['node_type']} action={row['action']}")
            print(f"      history={row['history']}")
            print(f"      path={row['path']}")

    if report["config_errors"]:
        print()
        print("CONFIG_ERRORS:")
        for err in report["config_errors"]:
            print("  -", err)

    if report["errors"]:
        print()
        print("ERRORS:")
        for err in report["errors"][:50]:
            print("  -", err)
        if len(report["errors"]) > 50:
            print(f"  ... {len(report['errors']) - 50} more")

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.0.7 preflop live preflight audit")


if __name__ == "__main__":
    main()

