r"""
test_image_replay_cycle_v12.py

PokerVision Core V0.6 — safe image replay tester + Dark_JSON/Clear_JSON/Decision_JSON audit.

Назначение:
- Берёт заранее подготовленные PNG/JPG из:
  C:\PokerVision_Clear_Programing\Script_Test_PokerVision_All_files\Test_image_6slot_display
- Сортирует их как timeline раздач: hand_N → street → state_index.
- Прогоняет каждую картинку через текущий detector pipeline проекта.
- НЕ использует Test_JSON_6slot_display.
- НЕ выполняет реальные клики.
- НЕ отправляет действие в solver/action-button runtime.
- Пишет результаты только в:
  C:\PokerVision_Clear_Programing\Script_Test_PokerVision_All_files\Test_Replay_Output
- Проверяет новый контракт:
  Dark_JSON = полный технический state; Clear_JSON = минимальный poker-state.
- Проверяет Recovery audit:
  recovery block exists for Active frames; chips recovery is disabled; restored players keep chips=false.
- Проверяет Decision_JSON audit:
  Decision_JSON exists for every valid Clear_JSON candidate and is built only from Clear_JSON.
- Проверяет Runtime audit:
  runtime_action/runtime_event остаются только в Dark_JSON; replay не допускает реальные клики.

Запуск:
  cd "C:\PokerVision_Clear_Programing\PokerVision V1_2"
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe .\test_image_replay_cycle_v12.py

Быстрая проверка порядка без моделей:
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe .\test_image_replay_cycle_v12.py --list-only
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from PIL import Image
except Exception as exc:
    raise RuntimeError("Pillow is required. Install: pip install pillow") from exc


STREET_ORDER: Dict[str, int] = {
    "preflop": 0,
    "flop": 1,
    "turn": 2,
    "river": 3,
    "unknown": 9,
}

BOARD_CARD_COUNT_BY_STREET: Dict[str, int] = {
    "preflop": 0,
    "flop": 3,
    "turn": 4,
    "river": 5,
}

HAND_FILE_RE = re.compile(
    r"^hand_(?P<num>\d+)(?:_(?P<street>preflop|flop|turn|river)(?:_(?P<idx>\d+))?)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReplayImageItem:
    path: Path
    source_name: str
    source_hand_id: str
    source_hand_num: int
    source_street: str
    source_state_index: int

    @property
    def sort_key(self) -> Tuple[int, int, int, str]:
        return (
            self.source_hand_num,
            STREET_ORDER.get(self.source_street, STREET_ORDER["unknown"]),
            self.source_state_index,
            self.source_name.lower(),
        )


@dataclass
class ReplayImageResult:
    image_name: str
    source_hand_id: str
    source_street: str
    source_state_index: int
    status: str
    source_hand_num: int = 0
    saved_json_count: int = 0
    saved_json_paths: List[str] = None
    errors: List[str] = None
    warnings: List[str] = None
    extracted: Dict[str, Any] = None

    def __post_init__(self) -> None:
        if self.saved_json_paths is None:
            self.saved_json_paths = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.extracted is None:
            self.extracted = {}


def _repo_root_from_this_file() -> Path:
    return Path(__file__).resolve().parent.parent


def _project_root_from_this_file() -> Path:
    return Path(__file__).resolve().parent


def _default_test_images_dir() -> Path:
    return _repo_root_from_this_file() / "Script_Test_PokerVision_All_files" / "Test_image_6slot_display"


def _default_replay_output_dir() -> Path:
    return _repo_root_from_this_file() / "Script_Test_PokerVision_All_files" / "Test_Replay_Output"


def _load_replay_images(images_dir: Path, image_extensions: Iterable[str]) -> List[ReplayImageItem]:
    if not images_dir.exists():
        raise FileNotFoundError(f"Test image folder does not exist: {images_dir}")

    extensions = {ext.lower() for ext in image_extensions}
    items: List[ReplayImageItem] = []

    for path in images_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue

        stem = path.stem
        match = HAND_FILE_RE.match(stem)
        if not match:
            continue

        hand_num = int(match.group("num"))
        street = (match.group("street") or "unknown").lower()
        state_index = int(match.group("idx") or "1")

        items.append(
            ReplayImageItem(
                path=path,
                source_name=path.name,
                source_hand_id=f"hand_{hand_num:02d}",
                source_hand_num=hand_num,
                source_street=street,
                source_state_index=state_index,
            )
        )

    items.sort(key=lambda item: item.sort_key)
    return items


def _safe_rmtree(path: Path) -> None:
    resolved = path.resolve(strict=False)
    if resolved.anchor == str(resolved):
        raise ValueError(f"Refusing to remove filesystem root: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_read(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return data


def _deep_get(data: Dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _as_number_or_none(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    try:
        return round(float(str(value).strip()), 2)
    except Exception:
        return None


def _extract_frame_name(state: Dict[str, Any]) -> Optional[str]:
    value = state.get("frame_name")
    if value is None:
        value = _deep_get(state, "table", "frame_name")
    return str(value) if value is not None else None


def _extract_table_id(state: Dict[str, Any]) -> Optional[str]:
    value = state.get("table_id")
    if value is None:
        value = _deep_get(state, "table", "table_id")
    return str(value) if value is not None else None


def _extract_hand_id(state: Dict[str, Any]) -> Optional[str]:
    value = state.get("hand_id")
    if value is None:
        value = _deep_get(state, "table", "hand_id")
    return str(value) if value is not None else None


def _extract_board(state: Dict[str, Any]) -> Tuple[Optional[str], List[str]]:
    board = state.get("board")
    if isinstance(board, dict):
        street = board.get("street")
        cards = board.get("cards")
        return (
            str(street).lower() if street is not None else None,
            [str(card) for card in cards] if isinstance(cards, list) else [],
        )

    board = _deep_get(state, "table_structure", "classes", "Board")
    if isinstance(board, dict):
        street = board.get("street")
        cards = board.get("cards")
        return (
            str(street).lower() if street is not None else None,
            [str(card) for card in cards] if isinstance(cards, list) else [],
        )

    return None, []


def _extract_total_pot(state: Dict[str, Any]) -> Optional[float]:
    if "Total_pot" in state:
        return _as_number_or_none(state.get("Total_pot"))
    value = _deep_get(state, "table_structure", "classes", "Total_pot", "value")
    return _as_number_or_none(value)


def _extract_players_any_schema(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    players = state.get("players")
    if isinstance(players, dict) and "seats" not in players:
        return {str(pos): dict(data) for pos, data in players.items() if isinstance(data, dict)}

    seats = _deep_get(state, "players", "seats")
    if isinstance(seats, dict):
        out: Dict[str, Dict[str, Any]] = {}
        for seat_name, seat in seats.items():
            if not isinstance(seat, dict):
                continue
            position = seat.get("position") or seat_name
            out[str(position)] = dict(seat)
        return out

    return {}


def _extract_player_facts(state: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    players = _extract_players_any_schema(state)
    facts: Dict[str, Dict[str, Any]] = {}

    for position, player in sorted(players.items()):
        chips = player.get("chips")
        stack = player.get("stack")

        if isinstance(chips, dict):
            chips_value = _as_number_or_none(chips.get("value"))
            chips_detect = bool(chips.get("detect", chips_value is not None))
        else:
            chips_value = _as_number_or_none(chips)
            chips_detect = chips_value is not None

        if isinstance(stack, dict):
            stack_value = _as_number_or_none(stack.get("value"))
            all_in = bool(stack.get("all_in", False))
        else:
            stack_value = _as_number_or_none(stack)
            all_in = False

        hero_cards = player.get("hero_cards")
        if not isinstance(hero_cards, list):
            hero_cards = player.get("cards")

        facts[str(position)] = {
            "fold": bool(player.get("fold", False)),
            "sitout": bool(player.get("sitout", False)),
            "hero": bool(player.get("hero", False)) or (isinstance(hero_cards, list) and len(hero_cards) == 2 and str(position) in {"Player_seat1"}),
            "hero_cards": [str(card) for card in hero_cards] if isinstance(hero_cards, list) else [],
            "chips_detect": chips_detect,
            "chips_value": chips_value,
            "stack_value": stack_value,
            "all_in": all_in,
        }

    return facts


def _extract_hero_cards_and_count(state: Dict[str, Any]) -> Tuple[int, List[str], Optional[str]]:
    facts = _extract_player_facts(state)
    hero_positions: List[str] = []
    hero_cards: List[str] = []

    for position, player in facts.items():
        cards = player.get("hero_cards") if isinstance(player.get("hero_cards"), list) else []
        is_hero = bool(player.get("hero")) or len(cards) == 2
        if is_hero:
            hero_positions.append(position)
            if len(cards) == 2 and not hero_cards:
                hero_cards = [str(cards[0]), str(cards[1])]

    return len(hero_positions), hero_cards, hero_positions[0] if len(hero_positions) == 1 else None


def _extract_trigger_classes(state: Dict[str, Any]) -> List[str]:
    trigger_ui = state.get("trigger_ui")
    if not isinstance(trigger_ui, dict):
        trigger_ui = state.get("trigger") if isinstance(state.get("trigger"), dict) else {}

    detected = trigger_ui.get("detected_classes") if isinstance(trigger_ui, dict) else None
    if isinstance(detected, list):
        return sorted({str(class_name) for class_name in detected if str(class_name).strip()})

    classes = trigger_ui.get("classes") if isinstance(trigger_ui, dict) else None
    out: List[str] = []
    if isinstance(classes, dict):
        for class_name, block in classes.items():
            if isinstance(block, dict) and bool(block.get("detect", False)):
                out.append(str(class_name))
    return sorted(set(out))


def _is_service_or_inactive_source(item: ReplayImageItem, state: Dict[str, Any]) -> bool:
    # service_or_inactive: source PNG has no street in its filename and detector did not confirm Active.
    trigger_classes = _extract_trigger_classes(state)
    return item.source_street == "unknown" and "Active" not in trigger_classes


def _build_replay_source_block(index: int, item: ReplayImageItem) -> Dict[str, Any]:
    return {
        "schema_version": "image-replay-source-v1",
        "replay_index": index,
        "image_name": item.source_name,
        "source_hand_id": item.source_hand_id,
        "source_hand_num": item.source_hand_num,
        "source_street": item.source_street,
        "source_state_index": item.source_state_index,
    }


def _canonical_signature(state: Dict[str, Any]) -> str:
    street, board_cards = _extract_board(state)
    total_pot = _extract_total_pot(state)
    hero_count, hero_cards, hero_position = _extract_hero_cards_and_count(state)
    player_facts = _extract_player_facts(state)

    runtime_action = state.get("runtime_action") if isinstance(state.get("runtime_action"), dict) else {}
    service = runtime_action.get("service") if isinstance(runtime_action.get("service"), dict) else {}

    payload = {
        "table_id": _extract_table_id(state),
        "hand_id": _extract_hand_id(state),
        "street": street,
        "board_cards": board_cards,
        "total_pot": total_pot,
        "hero_count": hero_count,
        "hero_position": hero_position,
        "hero_cards": sorted(hero_cards),
        "players": player_facts,
    }

    # V7.0.2: service-only frames have intentionally empty poker-state fields.
    # Their canonical identity must include Trigger_UI service data, otherwise
    # Exit_cashOut / 1_roll_board / Remove_Game / Non_active_fold / True_active_fold
    # all collapse into the same empty poker signature.
    if isinstance(service, dict) and str(service.get("branch") or "") == "trigger_ui_service":
        service_status = str(service.get("status") or "")
        service_target = str(service.get("target_class") or "")
        service_sequence = list(service.get("target_sequence") or [])
        trigger_ui = state.get("trigger_ui") if isinstance(state.get("trigger_ui"), dict) else {}
        trigger_classes = trigger_ui.get("detected_classes") if isinstance(trigger_ui.get("detected_classes"), list) else []

        if service_status not in {"", "skipped"} or service_target or service_sequence:
            payload["service_signature"] = {
                "status": service_status,
                "target_class": service_target,
                "target_sequence": service_sequence,
                "trigger_classes": sorted(str(class_name) for class_name in trigger_classes),
                "click_points_count": len(service.get("click_points") or []),
            }

    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_state(item: ReplayImageItem, state: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    errors: List[str] = []
    warnings: List[str] = []

    frame_name = _extract_frame_name(state)
    table_id = _extract_table_id(state)
    hand_id = _extract_hand_id(state)
    street, board_cards = _extract_board(state)
    total_pot = _extract_total_pot(state)
    player_facts = _extract_player_facts(state)
    hero_count, hero_cards, hero_position = _extract_hero_cards_and_count(state)

    if not frame_name:
        errors.append("missing frame_name")
    if not table_id:
        errors.append("missing table_id")
    if not hand_id:
        errors.append("missing hand_id")
    service_or_inactive = _is_service_or_inactive_source(item, state)
    trigger_classes = _extract_trigger_classes(state)

    if service_or_inactive:
        warnings.append(
            "source file has no street/Active poker state; "
            f"players/HERO validation skipped for service_or_inactive frame, trigger_classes={trigger_classes}"
        )
    else:
        if not player_facts:
            errors.append("missing players/seats")
        if hero_count != 1:
            errors.append(f"expected exactly one hero, got {hero_count}")
        if hero_count == 1 and len(hero_cards) != 2:
            errors.append(f"hero must have exactly 2 cards, got {len(hero_cards)}")

    if item.source_street != "unknown":
        if street != item.source_street:
            errors.append(f"street mismatch: file={item.source_street}, json={street}")
        expected_board_count = BOARD_CARD_COUNT_BY_STREET[item.source_street]
        if len(board_cards) != expected_board_count:
            errors.append(
                f"board card count mismatch for {item.source_street}: "
                f"expected={expected_board_count}, actual={len(board_cards)}"
            )
    else:
        warnings.append("source file has no street in name; street/card-count check skipped")

    extracted = {
        "frame_name": frame_name,
        "table_id": table_id,
        "hand_id": hand_id,
        "street": street,
        "board_cards": board_cards,
        "board_card_count": len(board_cards),
        "total_pot": total_pot,
        "players_count": len(player_facts),
        "player_positions": sorted(player_facts.keys()),
        "hero_count": hero_count,
        "hero_position": hero_position,
        "hero_cards": hero_cards,
        "trigger_classes": _extract_trigger_classes(state),
        "service_or_inactive": _is_service_or_inactive_source(item, state),
    }

    return errors, warnings, extracted


CLEAR_REQUIRED_TOP_LEVEL_KEYS = {"frame_id", "board", "Total_pot", "players"}
CLEAR_ALLOWED_TOP_LEVEL_KEYS = CLEAR_REQUIRED_TOP_LEVEL_KEYS | {
    "click_result",
    "engine_context",
    "engine_decision_preview",
}
CLEAR_FORBIDDEN_ANYWHERE_KEYS = {
    "frame_name",
    "table_id",
    "hand_id",
    "action_event_id",
    "action_signature",
    "pipeline_meta",
    "trigger_ui",
    "table_structure",
    "runtime_event",
    "runtime_action",
    "warnings",
    "errors",
    "stable_state",
    "slot_bbox",
    "confidence",
    "bbox",
    "processing_time_ms",
    "solver_action",
    "solver_status",
    "solver_payload_path",
    "click_points",
    "service",
    "action_button",
}


def _walk_forbidden_keys(data: Any, *, path: str = "$") -> List[str]:
    found: List[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text in CLEAR_FORBIDDEN_ANYWHERE_KEYS:
                found.append(child_path)
            found.extend(_walk_forbidden_keys(value, path=child_path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_walk_forbidden_keys(value, path=f"{path}[{index}]"))
    return found



def _count_click_points(block: Any) -> int:
    if not isinstance(block, dict):
        return 0
    points = block.get("click_points")
    return len(points) if isinstance(points, list) else 0


def _runtime_bool(block: Any, key: str, *, default: bool = False) -> bool:
    if not isinstance(block, dict):
        return default
    value = block.get(key)
    return bool(value) if isinstance(value, bool) else default


def _validate_runtime_contract(
    *,
    item: ReplayImageItem,
    dark_state: Dict[str, Any],
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """Validate runtime/action-button/service data stays diagnostic-only and replay-safe."""
    errors: List[str] = []
    warnings: List[str] = []
    extracted: Dict[str, Any] = {}

    runtime_action = dark_state.get("runtime_action")
    runtime_event = dark_state.get("runtime_event")
    trigger_classes = _extract_trigger_classes(dark_state)
    service_or_inactive = _is_service_or_inactive_source(item, dark_state)

    extracted["runtime_audit_present"] = isinstance(runtime_action, dict)
    extracted["runtime_event_present"] = isinstance(runtime_event, dict)
    extracted["runtime_trigger_classes"] = trigger_classes

    if not isinstance(runtime_action, dict):
        errors.append("Dark_JSON must contain runtime_action diagnostic block")
        return errors, warnings, extracted

    service = runtime_action.get("service")
    action_button = runtime_action.get("action_button")
    if not isinstance(service, dict):
        errors.append("runtime_action.service must be object")
        service = {}
    if not isinstance(action_button, dict):
        errors.append("runtime_action.action_button must be object")
        action_button = {}

    service_status = str(service.get("status") or "skipped")
    action_status = str(action_button.get("status") or "skipped")
    runtime_status = str(runtime_action.get("status") or "skipped")

    service_points_count = _count_click_points(service)
    action_points_count = _count_click_points(action_button)
    service_real_click_enabled = _runtime_bool(service, "real_click_enabled", default=False)
    action_real_click_enabled = _runtime_bool(action_button, "real_click_enabled", default=False)
    service_dry_run = _runtime_bool(service, "dry_run", default=False)
    action_dry_run = _runtime_bool(action_button, "dry_run", default=False)

    extracted.update(
        {
            "runtime_status": runtime_status,
            "runtime_service_status": service_status,
            "runtime_action_button_status": action_status,
            "runtime_service_target_class": service.get("target_class"),
            "runtime_service_target_sequence": list(service.get("target_sequence") or []) if isinstance(service.get("target_sequence"), list) else [],
            "runtime_action_button_target_sequence": list(action_button.get("target_sequence") or []) if isinstance(action_button.get("target_sequence"), list) else [],
            "runtime_service_frame_finished": bool(service.get("frame_finished", False)),
            "runtime_service_skip_action_button_runtime": bool(service.get("skip_action_button_runtime", False)),
            "runtime_service_dry_run": service_dry_run,
            "runtime_action_button_dry_run": action_dry_run,
            "runtime_service_real_click_enabled": service_real_click_enabled,
            "runtime_action_button_real_click_enabled": action_real_click_enabled,
            "runtime_service_click_points_count": service_points_count,
            "runtime_action_button_click_points_count": action_points_count,
            "runtime_total_click_points_count": service_points_count + action_points_count,
        }
    )

    # Replay must never execute real clicks. Runtime data may be present in Dark_JSON,
    # but real-click flags and clicked statuses are forbidden in this safe harness.
    if service_real_click_enabled:
        errors.append("Replay runtime audit: service real_click_enabled must be False")
    if action_real_click_enabled:
        errors.append("Replay runtime audit: action_button real_click_enabled must be False")
    if service_status == "clicked":
        errors.append("Replay runtime audit: service branch must not perform real clicked status")
    if action_status == "clicked":
        errors.append("Replay runtime audit: action_button branch must not perform real clicked status")

    # Active poker-state frames may have Action_Button diagnostics. Service/inactive frames must
    # stay outside action-button poker runtime and must not create a Clear_JSON state.
    if service_or_inactive:
        if extracted["runtime_event_present"]:
            warnings.append("service/inactive frame unexpectedly has runtime_event; verify ActionEventGate semantics")
        if action_status not in {"skipped", "blocked"}:
            errors.append(f"service/inactive frame must not run Action_Button runtime; action_status={action_status!r}")

        if extracted["runtime_service_skip_action_button_runtime"]:
            if action_points_count:
                errors.append("service skip_action_button_runtime=true must suppress Action_Button click points")
            if extracted["runtime_action_button_target_sequence"]:
                errors.append("service skip_action_button_runtime=true must suppress Action_Button target sequence")

        if "True_active_fold" in trigger_classes:
            if service.get("target_class") == "True_active_fold" or "True_active_fold" in extracted["runtime_service_target_sequence"]:
                errors.append("True_active_fold is confirmation-only and must not be selected as a click target")
            if service_points_count:
                errors.append("True_active_fold frame must not have service click points in replay")

        if "Remove_Table" in trigger_classes and "Active" not in trigger_classes:
            if service.get("target_class") == "Remove_Table" or "Remove_Table" in extracted["runtime_service_target_sequence"]:
                errors.append("Remove_Table without Active must not be selected as a click target")
            if service_points_count and service.get("target_class") in {None, "", "Remove_Table"}:
                errors.append("Remove_Table without Active must not have service click points unless another service target was selected")
    else:
        if not extracted["runtime_event_present"]:
            errors.append("Active poker-state frame must contain runtime_event ActionEventGate diagnostic block")
        if action_status not in {"skipped", "dry_run", "blocked", "error"}:
            warnings.append(f"Unexpected action_button status for replay Active frame: {action_status!r}")
        if action_points_count and not action_dry_run:
            errors.append("Action_Button click points in replay must be dry-run only")

    return errors, warnings, extracted


def _validate_clear_json_artifacts(
    *,
    item: ReplayImageItem,
    dark_state: Dict[str, Any],
    replay_output_dir: Path,
    index: int,
) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """Validate the new Dark_JSON -> Clear_JSON contract for one replay frame."""
    errors: List[str] = []
    warnings: List[str] = []
    extracted: Dict[str, Any] = {}

    saved_dark_path = dark_state.get("__saved_dark_json_path")
    if saved_dark_path:
        dark_path = Path(str(saved_dark_path))
        extracted["dark_json_path"] = str(dark_path)
        if "Dark_JSON" not in dark_path.parts:
            errors.append(f"saved technical state path is not inside Dark_JSON folder: {dark_path}")
        if not dark_path.name.endswith(".dark.json"):
            errors.append(f"Dark_JSON filename must end with .dark.json: {dark_path.name}")

    contract = dark_state.get("clear_json_contract")
    if not isinstance(contract, dict):
        errors.append("missing dark_state.clear_json_contract block")
        return errors, warnings, extracted

    status = str(contract.get("status") or "")
    contract_reason = str(contract.get("reason") or "")
    extracted["clear_json_contract_status"] = status
    extracted["clear_json_contract_reason"] = contract_reason
    publication = contract.get("publication") if isinstance(contract.get("publication"), dict) else {}
    pending_path_value = contract.get("pending_path") or publication.get("pending_path")
    extracted["clear_json_pending_path"] = str(pending_path_value) if pending_path_value else None
    extracted["clear_json_pending_present"] = bool(pending_path_value)

    state_machine = contract.get("state_machine")
    if isinstance(state_machine, dict):
        extracted["state_machine_reason"] = state_machine.get("reason")
        extracted["state_machine_frame_id"] = state_machine.get("frame_id")
        extracted["state_machine_previous_frame_id"] = state_machine.get("previous_frame_id")
        extracted["state_machine_street_occurrence"] = state_machine.get("street_occurrence")
        extracted["state_machine_should_save"] = state_machine.get("should_save")
    else:
        extracted["state_machine_reason"] = None
        extracted["state_machine_frame_id"] = None
        extracted["state_machine_previous_frame_id"] = None
        extracted["state_machine_street_occurrence"] = None
        extracted["state_machine_should_save"] = None

    recovery = contract.get("recovery")
    if isinstance(recovery, dict):
        recovery_rules = [str(rule) for rule in recovery.get("rules", [])] if isinstance(recovery.get("rules"), list) else []
        recovery_warnings = [str(warn) for warn in recovery.get("warnings", [])] if isinstance(recovery.get("warnings"), list) else []
        extracted["recovery_present"] = True
        extracted["recovery_applied"] = bool(recovery.get("applied", False))
        extracted["recovery_reason"] = recovery.get("reason")
        extracted["recovery_rules"] = recovery_rules
        extracted["recovery_warnings"] = recovery_warnings
        extracted["recovery_chips_recovery"] = recovery.get("chips_recovery")
        extracted["recovery_hero_recovery"] = recovery.get("hero_recovery")
    else:
        recovery_rules = []
        recovery_warnings = []
        extracted["recovery_present"] = False
        extracted["recovery_applied"] = False
        extracted["recovery_reason"] = None
        extracted["recovery_rules"] = []
        extracted["recovery_warnings"] = []
        extracted["recovery_chips_recovery"] = None
        extracted["recovery_hero_recovery"] = None

    decision_contract = contract.get("decision_json_contract") if isinstance(contract.get("decision_json_contract"), dict) else {}
    decision_path_value = decision_contract.get("path") if isinstance(decision_contract, dict) else None
    extracted["decision_json_path"] = str(decision_path_value) if decision_path_value else None
    extracted["decision_json_present"] = bool(decision_path_value)
    extracted["decision_json_status"] = decision_contract.get("status") if isinstance(decision_contract, dict) else None
    extracted["decision_json_validation"] = decision_contract.get("validation") if isinstance(decision_contract, dict) else None

    action_decision_contract = contract.get("action_decision_contract") if isinstance(contract.get("action_decision_contract"), dict) else {}
    action_decision_path_value = action_decision_contract.get("path") if isinstance(action_decision_contract, dict) else None
    extracted["action_decision_json_path"] = str(action_decision_path_value) if action_decision_path_value else None
    extracted["action_decision_json_present"] = bool(action_decision_path_value)
    extracted["action_decision_json_status"] = action_decision_contract.get("status") if isinstance(action_decision_contract, dict) else None
    extracted["action_decision_json_validation"] = action_decision_contract.get("validation") if isinstance(action_decision_contract, dict) else None
    extracted["action_decision_action"] = action_decision_contract.get("action") if isinstance(action_decision_contract, dict) else None

    action_runtime_plan_contract = action_decision_contract.get("action_runtime_plan_contract") if isinstance(action_decision_contract.get("action_runtime_plan_contract"), dict) else {}
    action_runtime_plan_path_value = action_runtime_plan_contract.get("path") if isinstance(action_runtime_plan_contract, dict) else None
    extracted["action_runtime_plan_json_path"] = str(action_runtime_plan_path_value) if action_runtime_plan_path_value else None
    extracted["action_runtime_plan_json_present"] = bool(action_runtime_plan_path_value)
    extracted["action_runtime_plan_status"] = action_runtime_plan_contract.get("status") if isinstance(action_runtime_plan_contract, dict) else None
    extracted["action_runtime_plan_validation"] = action_runtime_plan_contract.get("validation") if isinstance(action_runtime_plan_contract, dict) else None
    extracted["action_runtime_plan_planned_action"] = action_runtime_plan_contract.get("planned_action") if isinstance(action_runtime_plan_contract, dict) else None
    extracted["action_runtime_plan_target_sequence"] = action_runtime_plan_contract.get("target_sequence") if isinstance(action_runtime_plan_contract, dict) else None

    runtime_action_block = dark_state.get("runtime_action") if isinstance(dark_state.get("runtime_action"), dict) else {}
    extracted["runtime_action_source"] = runtime_action_block.get("source") if isinstance(runtime_action_block, dict) else None
    extracted["runtime_action_plan_present"] = bool(runtime_action_block.get("action_runtime_plan_contract")) if isinstance(runtime_action_block, dict) else False

    service_or_inactive = _is_service_or_inactive_source(item, dark_state)

    if service_or_inactive:
        if status != "skipped":
            errors.append(f"service/inactive frame must not save Clear_JSON; status={status!r}")
        if contract.get("path"):
            errors.append(f"service/inactive frame unexpectedly has Clear_JSON path: {contract.get('path')}")
        if extracted.get("clear_json_pending_path"):
            errors.append(f"service/inactive frame unexpectedly has pending Clear_JSON path: {extracted.get('clear_json_pending_path')}")
        if extracted.get("decision_json_path"):
            errors.append(f"service/inactive frame unexpectedly has Decision_JSON path: {extracted.get('decision_json_path')}")
        if extracted.get("action_decision_json_path"):
            errors.append(f"service/inactive frame unexpectedly has Action_Decision_JSON path: {extracted.get('action_decision_json_path')}")
        if extracted.get("action_runtime_plan_json_path"):
            errors.append(f"service/inactive frame unexpectedly has Action_Runtime_Plan_JSON path: {extracted.get('action_runtime_plan_json_path')}")
        if extracted["recovery_applied"]:
            errors.append(f"service/inactive frame must not apply Clear_JSON recovery: {recovery}")
        return errors, warnings, extracted

    if status != "saved":
        if status == "skipped" and contract_reason == "duplicate_clear_json_state_blocked":
            warnings.append("Active poker-state Clear_JSON duplicate was correctly skipped by state-machine")
            if extracted["recovery_chips_recovery"] not in (None, "disabled"):
                errors.append(f"Clear_JSON recovery must keep chips recovery disabled, got {extracted['recovery_chips_recovery']!r}")
            return errors, warnings, extracted
        errors.append(f"Active poker-state frame must save Clear_JSON or be state-machine duplicate; status={status!r}, contract={contract}")
        return errors, warnings, extracted

    pending_path_value = extracted.get("clear_json_pending_path")
    if not pending_path_value:
        errors.append("Active poker-state frame must include Clear_JSON_Pending path before final publication")
    else:
        pending_path = Path(str(pending_path_value))
        if "Clear_JSON_Pending" not in pending_path.parts:
            errors.append(f"Pending Clear_JSON path is not inside Clear_JSON_Pending folder: {pending_path}")
        elif not pending_path.exists():
            errors.append(f"Pending Clear_JSON file does not exist: {pending_path}")

    decision_path_value = extracted.get("decision_json_path")
    if not decision_path_value:
        errors.append("Active poker-state frame must include Decision_JSON path built from Clear_JSON")
    else:
        decision_path = Path(str(decision_path_value))
        if "Decision_JSON" not in decision_path.parts:
            errors.append(f"Decision_JSON path is not inside Decision_JSON folder: {decision_path}")
        elif not decision_path.exists():
            errors.append(f"Decision_JSON file does not exist: {decision_path}")
        else:
            try:
                decision_state = _json_read(decision_path)
                generated_decision_path = replay_output_dir / "generated_decision_json" / f"{index:03d}_{item.path.stem}.decision.json"
                _write_json(generated_decision_path, decision_state)
                extracted["generated_decision_json_path"] = str(generated_decision_path)
                try:
                    from logic.decision_json_builder import validate_decision_json_contract

                    decision_validation = validate_decision_json_contract(decision_state)
                    extracted["decision_builder_validation"] = decision_validation
                    if not isinstance(decision_validation, dict) or not decision_validation.get("ok"):
                        errors.append(f"decision_json_builder validation failed: {decision_validation}")
                except Exception as exc:
                    errors.append(f"decision_json_builder validation crashed: {exc}")
                if decision_state.get("source") != "Clear_JSON":
                    errors.append("Decision_JSON.source must be Clear_JSON")
                if decision_state.get("source_frame_id") != (contract.get("state_machine") or {}).get("frame_id") and decision_state.get("source_frame_id") != (dark_state.get("table") or {}).get("frame_id"):
                    # state-machine may rewrite frame_id later; final file validation below checks exact Clear_JSON frame_id.
                    pass
                for forbidden_key in ("runtime_action", "runtime_event", "trigger_ui", "table_structure", "click_result", "click_points"):
                    if forbidden_key in decision_state:
                        errors.append(f"Decision_JSON must not contain technical/output key: {forbidden_key}")
            except Exception as exc:
                errors.append(f"failed to read Decision_JSON: {exc}")

    action_decision_path_value = extracted.get("action_decision_json_path")
    if not action_decision_path_value:
        errors.append("Active poker-state frame must include Action_Decision_JSON path built from Decision_JSON")
    else:
        action_decision_path = Path(str(action_decision_path_value))
        if "Action_Decision_JSON" not in action_decision_path.parts:
            errors.append(f"Action_Decision_JSON path is not inside Action_Decision_JSON folder: {action_decision_path}")
        elif not action_decision_path.exists():
            errors.append(f"Action_Decision_JSON file does not exist: {action_decision_path}")
        else:
            try:
                action_decision_state = _json_read(action_decision_path)
                generated_action_decision_path = replay_output_dir / "generated_action_decision_json" / f"{index:03d}_{item.path.stem}.action.json"
                _write_json(generated_action_decision_path, action_decision_state)
                extracted["generated_action_decision_json_path"] = str(generated_action_decision_path)
                try:
                    from logic.action_decision_stub import validate_action_decision_contract

                    action_decision_validation = validate_action_decision_contract(action_decision_state)
                    extracted["action_decision_builder_validation"] = action_decision_validation
                    if not isinstance(action_decision_validation, dict) or not action_decision_validation.get("ok"):
                        errors.append(f"action_decision_stub validation failed: {action_decision_validation}")
                except Exception as exc:
                    errors.append(f"action_decision_stub validation crashed: {exc}")
                if action_decision_state.get("source") != "Decision_JSON":
                    errors.append("Action_Decision_JSON.source must be Decision_JSON")
                if action_decision_state.get("source_decision_frame_id") != (contract.get("state_machine") or {}).get("frame_id") and action_decision_state.get("source_decision_frame_id") != (dark_state.get("table") or {}).get("frame_id"):
                    # final comparison below checks exact Clear_JSON/Decision_JSON link.
                    pass
                for forbidden_key in ("runtime_action", "runtime_event", "trigger_ui", "table_structure", "click_result", "click_points", "clear_json", "dark_json"):
                    if forbidden_key in action_decision_state:
                        errors.append(f"Action_Decision_JSON must not contain technical/output key: {forbidden_key}")
            except Exception as exc:
                errors.append(f"failed to read Action_Decision_JSON: {exc}")

    if not extracted["recovery_present"]:
        errors.append("Active poker-state frame must include clear_json_contract.recovery audit block")
    elif extracted["recovery_chips_recovery"] != "disabled":
        errors.append(f"Clear_JSON recovery must explicitly disable chips recovery, got {extracted['recovery_chips_recovery']!r}")

    forbidden_recovery_rules = [rule for rule in recovery_rules if "chip" in rule.lower() and "normalized_missing_chips_to_false" not in rule]
    if forbidden_recovery_rules:
        errors.append(f"Clear_JSON recovery must not restore dynamic chips values: {forbidden_recovery_rules}")

    clear_path_value = contract.get("path")
    if not clear_path_value:
        errors.append("clear_json_contract.status=saved but path is missing")
        return errors, warnings, extracted

    clear_path = Path(str(clear_path_value))
    extracted["clear_json_path"] = str(clear_path)
    if "Clear_JSON" not in clear_path.parts:
        errors.append(f"Clear_JSON path is not inside Clear_JSON folder: {clear_path}")
    if not clear_path.exists():
        errors.append(f"Clear_JSON file does not exist: {clear_path}")
        return errors, warnings, extracted

    try:
        clear_state = _json_read(clear_path)
    except Exception as exc:
        errors.append(f"failed to read Clear_JSON: {exc}")
        return errors, warnings, extracted

    # If Decision_JSON was generated, it must point back to the final Clear_JSON frame_id.
    decision_path_value_for_compare = extracted.get("decision_json_path")
    if decision_path_value_for_compare:
        try:
            decision_state_for_compare = _json_read(Path(str(decision_path_value_for_compare)))
            if decision_state_for_compare.get("source_frame_id") != clear_state.get("frame_id"):
                errors.append(
                    "Decision_JSON.source_frame_id must equal final Clear_JSON.frame_id: "
                    f"decision={decision_state_for_compare.get('source_frame_id')!r}, "
                    f"clear={clear_state.get('frame_id')!r}"
                )
        except Exception as exc:
            errors.append(f"failed to compare Decision_JSON source_frame_id: {exc}")

    action_runtime_plan_path_value = extracted.get("action_runtime_plan_json_path")
    if not action_runtime_plan_path_value:
        errors.append("Active poker-state frame must include Action_Runtime_Plan_JSON path built from Action_Decision_JSON")
    else:
        action_runtime_plan_path = Path(str(action_runtime_plan_path_value))
        if "Action_Runtime_Plan_JSON" not in action_runtime_plan_path.parts:
            errors.append(f"Action_Runtime_Plan_JSON path is not inside Action_Runtime_Plan_JSON folder: {action_runtime_plan_path}")
        elif not action_runtime_plan_path.exists():
            errors.append(f"Action_Runtime_Plan_JSON file does not exist: {action_runtime_plan_path}")
        else:
            try:
                action_runtime_plan_state = _json_read(action_runtime_plan_path)
                generated_action_runtime_plan_path = replay_output_dir / "generated_action_runtime_plan_json" / f"{index:03d}_{item.path.stem}.runtime_plan.json"
                _write_json(generated_action_runtime_plan_path, action_runtime_plan_state)
                extracted["generated_action_runtime_plan_json_path"] = str(generated_action_runtime_plan_path)
                try:
                    from logic.action_runtime_plan_builder import validate_action_runtime_plan_contract

                    runtime_plan_validation = validate_action_runtime_plan_contract(action_runtime_plan_state)
                    extracted["action_runtime_plan_builder_validation"] = runtime_plan_validation
                    if not isinstance(runtime_plan_validation, dict) or not runtime_plan_validation.get("ok"):
                        errors.append(f"action_runtime_plan_builder validation failed: {runtime_plan_validation}")
                except Exception as exc:
                    errors.append(f"action_runtime_plan_builder validation crashed: {exc}")
                if action_runtime_plan_state.get("source") != "Action_Decision_JSON":
                    errors.append("Action_Runtime_Plan_JSON.source must be Action_Decision_JSON")
                for forbidden_key in ("runtime_action", "click_result", "click_points", "bbox", "confidence", "mouse"):
                    if forbidden_key in action_runtime_plan_state:
                        errors.append(f"Action_Runtime_Plan_JSON must not contain technical/output key: {forbidden_key}")
            except Exception as exc:
                errors.append(f"failed to read Action_Runtime_Plan_JSON: {exc}")

    if extracted.get("runtime_action_source") != "Action_Decision_JSON":
        errors.append(f"runtime_action.source must be Action_Decision_JSON, got {extracted.get('runtime_action_source')!r}")
    if not extracted.get("runtime_action_plan_present"):
        errors.append("runtime_action must include action_runtime_plan_contract for V0.7 audit")

    action_decision_path_value_for_compare = extracted.get("action_decision_json_path")
    if action_decision_path_value_for_compare and decision_path_value_for_compare:
        try:
            action_decision_state_for_compare = _json_read(Path(str(action_decision_path_value_for_compare)))
            decision_state_for_compare = _json_read(Path(str(decision_path_value_for_compare)))
            if action_decision_state_for_compare.get("source_decision_frame_id") != decision_state_for_compare.get("source_frame_id"):
                errors.append(
                    "Action_Decision_JSON.source_decision_frame_id must equal Decision_JSON.source_frame_id: "
                    f"action={action_decision_state_for_compare.get('source_decision_frame_id')!r}, "
                    f"decision={decision_state_for_compare.get('source_frame_id')!r}"
                )
        except Exception as exc:
            errors.append(f"failed to compare Action_Decision_JSON source_decision_frame_id: {exc}")

    action_runtime_plan_path_value_for_compare = extracted.get("action_runtime_plan_json_path")
    if action_runtime_plan_path_value_for_compare and action_decision_path_value_for_compare:
        try:
            runtime_plan_state_for_compare = _json_read(Path(str(action_runtime_plan_path_value_for_compare)))
            action_decision_state_for_compare = _json_read(Path(str(action_decision_path_value_for_compare)))
            if runtime_plan_state_for_compare.get("source_action_decision_frame_id") != action_decision_state_for_compare.get("source_decision_frame_id"):
                errors.append(
                    "Action_Runtime_Plan_JSON source_action_decision_frame_id must match Action_Decision_JSON source_decision_frame_id: "
                    f"plan={runtime_plan_state_for_compare.get('source_action_decision_frame_id')!r}, "
                    f"action={action_decision_state_for_compare.get('source_decision_frame_id')!r}"
                )
            plan_target_sequence = runtime_plan_state_for_compare.get("target_sequence")
            plan_target_sequences = runtime_plan_state_for_compare.get("target_sequences")
            action_target_buttons = action_decision_state_for_compare.get("target_button_classes")

            if not isinstance(plan_target_sequence, list) or not plan_target_sequence:
                errors.append(
                    "Action_Runtime_Plan_JSON target_sequence must be a non-empty list: "
                    f"plan={plan_target_sequence!r}"
                )

            if not isinstance(plan_target_sequences, list) or not plan_target_sequences:
                errors.append(
                    "Action_Runtime_Plan_JSON target_sequences must be a non-empty list: "
                    f"plan={plan_target_sequences!r}"
                )
            elif list(plan_target_sequence) not in [list(seq) for seq in plan_target_sequences if isinstance(seq, list)]:
                errors.append(
                    "Action_Runtime_Plan_JSON target_sequence must be one of target_sequences: "
                    f"target_sequence={plan_target_sequence!r}, target_sequences={plan_target_sequences!r}"
                )

            if isinstance(action_target_buttons, list) and action_target_buttons:
                flattened_plan_buttons = []
                if isinstance(plan_target_sequences, list):
                    for seq in plan_target_sequences:
                        if isinstance(seq, list):
                            for button in seq:
                                if button not in flattened_plan_buttons:
                                    flattened_plan_buttons.append(button)

                missing_action_buttons = [
                    button for button in action_target_buttons
                    if button not in flattened_plan_buttons
                ]
                if missing_action_buttons:
                    errors.append(
                        "Action_Runtime_Plan_JSON target_sequences must cover Action_Decision_JSON fallback buttons: "
                        f"missing={missing_action_buttons!r}, plan={plan_target_sequences!r}, action={action_target_buttons!r}"
                    )
        except Exception as exc:
            errors.append(f"failed to compare Action_Runtime_Plan_JSON with Action_Decision_JSON: {exc}")

    # Keep a copy under Test_Replay_Output for easy manual inspection, paired by replay index/source PNG.
    generated_clear_path = replay_output_dir / "generated_clear_json" / f"{index:03d}_{item.path.stem}.clear.json"
    _write_json(generated_clear_path, clear_state)
    extracted["generated_clear_json_path"] = str(generated_clear_path)

    top_keys = set(clear_state.keys())
    extracted["clear_top_level_keys"] = sorted(top_keys)
    click_result = clear_state.get("click_result")
    extracted["final_clear_json_has_click_result"] = isinstance(click_result, dict)
    if not isinstance(click_result, dict):
        errors.append("Final Clear_JSON must contain compact click_result in V0.4 publication discipline")
    if not CLEAR_REQUIRED_TOP_LEVEL_KEYS.issubset(top_keys) or not top_keys.issubset(CLEAR_ALLOWED_TOP_LEVEL_KEYS):
        errors.append(
            "Clear_JSON top-level keys mismatch: "
            f"required={sorted(CLEAR_REQUIRED_TOP_LEVEL_KEYS)}, "
            f"allowed={sorted(CLEAR_ALLOWED_TOP_LEVEL_KEYS)}, actual={sorted(top_keys)}"
        )

    forbidden_paths = _walk_forbidden_keys(clear_state)
    if forbidden_paths:
        errors.append(f"Clear_JSON contains forbidden technical keys: {forbidden_paths}")

    try:
        from logic.clear_json_builder import validate_clear_json_contract

        validation = validate_clear_json_contract(clear_state)
        extracted["clear_builder_validation"] = validation
        if not isinstance(validation, dict) or not validation.get("ok"):
            errors.append(f"clear_json_builder validation failed: {validation}")
    except Exception as exc:
        errors.append(f"clear_json_builder validation crashed: {exc}")

    frame_id = clear_state.get("frame_id")
    if not isinstance(frame_id, str) or not frame_id.strip():
        errors.append("Clear_JSON frame_id must be a non-empty string")
    elif _extract_table_id(dark_state) and not frame_id.startswith(str(_extract_table_id(dark_state)) + "_"):
        warnings.append(f"Clear_JSON frame_id does not start with table_id prefix: frame_id={frame_id}")

    board = clear_state.get("board")
    if not isinstance(board, dict):
        errors.append("Clear_JSON board must be object")
        board = {}
    clear_street = str(board.get("street") or "").lower()
    clear_cards = board.get("cards") if isinstance(board.get("cards"), list) else []
    extracted["clear_street"] = clear_street
    extracted["clear_board_card_count"] = len(clear_cards)

    if item.source_street != "unknown":
        if clear_street != item.source_street:
            errors.append(f"Clear_JSON street mismatch: file={item.source_street}, clear={clear_street}")
        expected_board_count = BOARD_CARD_COUNT_BY_STREET[item.source_street]
        if len(clear_cards) != expected_board_count:
            errors.append(
                f"Clear_JSON board card count mismatch for {item.source_street}: "
                f"expected={expected_board_count}, actual={len(clear_cards)}"
            )

    players = clear_state.get("players")
    if not isinstance(players, dict) or not players:
        errors.append("Clear_JSON players must be non-empty object for Active poker-state")
        players = {}

    if any(str(key).startswith("Player_seat") for key in players.keys()):
        errors.append(f"Clear_JSON players must use logical positions, not Player_seat keys: {sorted(players.keys())}")

    hero_positions = []
    for position, player in players.items():
        if not isinstance(player, dict):
            errors.append(f"Clear_JSON player {position} must be object")
            continue
        if not isinstance(player.get("fold"), bool):
            errors.append(f"Clear_JSON player {position}.fold must be bool")
        if not isinstance(player.get("stack"), (int, float)) or isinstance(player.get("stack"), bool):
            errors.append(f"Clear_JSON player {position}.stack must be number")
        chips = player.get("chips")
        if chips is not False and (not isinstance(chips, (int, float)) or isinstance(chips, bool)):
            errors.append(f"Clear_JSON player {position}.chips must be number or false")
        if player.get("hero") is True:
            hero_positions.append(str(position))
            cards = player.get("cards")
            if not isinstance(cards, list) or len(cards) != 2:
                errors.append(f"Clear_JSON HERO {position}.cards must contain exactly 2 cards")
        elif "cards" in player:
            errors.append(f"Clear_JSON non-HERO player {position} must not contain cards")

    extracted["clear_hero_positions"] = hero_positions
    if len(hero_positions) != 1:
        errors.append(f"Clear_JSON must contain exactly one HERO, got {len(hero_positions)}")

    for rule in recovery_rules:
        if rule.startswith("restored_missing_player:"):
            restored_position = rule.split(":", 1)[1]
            restored_player = players.get(restored_position)
            if not isinstance(restored_player, dict):
                errors.append(f"Recovery rule {rule!r} exists, but restored player is absent from Clear_JSON")
                continue
            if restored_player.get("chips") is not False:
                errors.append(
                    f"Recovered missing player {restored_position} must have chips=false, "
                    f"actual={restored_player.get('chips')!r}"
                )

    hero_recovery_reason = extracted.get("recovery_hero_recovery")
    hero_recovered = hero_recovery_reason in {
        "board_continuation_confirmed_same_hand",
        "partial_hero_card_match_confirmed_same_hand",
    }
    if hero_recovered:
        if len(hero_positions) != 1:
            errors.append("HERO recovery was reported, but Clear_JSON does not contain exactly one HERO")
        else:
            hero_player = players.get(hero_positions[0], {})
            hero_cards = hero_player.get("cards") if isinstance(hero_player, dict) else None
            if not isinstance(hero_cards, list) or len(hero_cards) != 2:
                errors.append(f"HERO recovery was reported, but HERO cards are invalid: {hero_cards!r}")

    return errors, warnings, extracted


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def _install_safe_runtime_stubs(dac: Any, *, real_service_dry_run: bool = False) -> None:
    def _service_stub(**_: Any) -> Dict[str, Any]:
        return {
            "service_click": {
                "status": "skipped",
                "frame_finished": False,
                "skip_action_button_runtime": False,
                "message": "Skipped by test_image_replay_cycle_v12 safe service runtime stub; action dry-run is still allowed for transaction audit.",
            }
        }

    def _action_stub(**_: Any) -> Dict[str, Any]:
        return {
            "payload": {"status": "skipped", "path": None, "message": "Skipped by test_image_replay_cycle_v12 safe runtime stub."},
            "solver": {"status": "skipped"},
            "action_buttons": {"status": "skipped", "detected_classes": []},
            "click": {"status": "dry_run", "target_sequence": [], "dry_run": True, "real_click_enabled": False, "guard_passed": True, "message": "Safe replay dry-run click completion for V0.3 transaction audit."},
        }

    if not real_service_dry_run:
        dac._run_v11_stage25_service_runtime_safely = _service_stub
    dac._run_v11_stage2_runtime_safely = _action_stub


def _prepare_display_cycle_for_image_replay(*, dac: Any, replay_output_dir: Path, current_image_holder: Dict[str, Image.Image], real_service_dry_run: bool = False) -> None:
    dac.UI_DISPLAY_CYCLE_OUTPUT_DIR = replay_output_dir / "ui_display_cycle"
    dac.CURRENT_CYCLE_DIR_NAME = "current_cycle"
    dac.CLEAR_PREVIOUS_UI_DISPLAY_OUTPUTS_ON_BUTTON_CLICK = False
    dac.SAVE_DEBUG_DESKTOP_CAPTURE = False
    dac.SAVE_DEBUG_TABLE_CROPS = False

    _install_safe_runtime_stubs(dac, real_service_dry_run=real_service_dry_run)

    def _dummy_screenshot() -> Image.Image:
        return Image.new("RGB", (3000, 1800), (0, 0, 0))

    def _current_image_as_table_roi(slot: Any, screenshot: Image.Image) -> Image.Image:
        image = current_image_holder.get("image")
        if image is None:
            raise RuntimeError("Internal test error: current replay image is not set")
        return image

    dac.capture_primary_monitor = _dummy_screenshot
    dac.crop_table_roi = _current_image_as_table_roi


def _run_replay(args: argparse.Namespace) -> int:
    project_root = _project_root_from_this_file()
    repo_root = _repo_root_from_this_file()

    sys.path.insert(0, str(project_root))

    import config  # type: ignore
    import display_analysis_cycle as dac  # type: ignore

    images_dir = Path(args.images_dir) if args.images_dir else _default_test_images_dir()
    replay_output_dir = Path(args.output_dir) if args.output_dir else _default_replay_output_dir()
    real_service_dry_run = bool(getattr(args, "real_service_dry_run", False))

    image_extensions = getattr(config, "IMAGE_EXTENSIONS", {".png", ".jpg", ".jpeg", ".bmp", ".webp"})
    items = _load_replay_images(images_dir=images_dir, image_extensions=image_extensions)

    if args.max_images is not None:
        items = items[: max(0, int(args.max_images))]

    print("=" * 100)
    print("IMAGE_REPLAY_CYCLE_V12")
    print("=" * 100)
    print(f"Project root: {project_root}")
    print(f"Repo root:    {repo_root}")
    print(f"Images dir:   {images_dir}")
    print(f"Output dir:   {replay_output_dir}")
    print(f"Images found: {len(items)}")
    print()

    if not items:
        print("[ERROR] No valid hand_*.png/jpg images found.")
        return 2

    print("Replay order:")
    for idx, item in enumerate(items, start=1):
        print(f"  {idx:03d}. {item.source_name} hand={item.source_hand_id} street={item.source_street} state_idx={item.source_state_index}")

    if args.list_only:
        print()
        print("[RESULT] OK: order listing only; models were not executed.")
        return 0

    _safe_rmtree(replay_output_dir)
    _ensure_dir(replay_output_dir)
    _ensure_dir(replay_output_dir / "reports")
    _ensure_dir(replay_output_dir / "generated_json")
    _ensure_dir(replay_output_dir / "generated_clear_json")

    current_image_holder: Dict[str, Image.Image] = {}
    _prepare_display_cycle_for_image_replay(
        dac=dac,
        replay_output_dir=replay_output_dir,
        current_image_holder=current_image_holder,
        real_service_dry_run=real_service_dry_run,
    )

    hand_tracker = dac.HandIdentityTracker()
    action_event_gate = dac.ActionEventGate(inactive_reset_passes=2)
    clear_json_state_machine = dac.ClearJsonStateMachine()

    results: List[ReplayImageResult] = []
    signature_seen: Dict[str, str] = {}
    previous_positions_by_source_hand: Dict[str, set[str]] = {}

    for index, item in enumerate(items, start=1):
        print()
        print("-" * 100)
        print(f"[{index:03d}/{len(items):03d}] {item.source_name}")

        result = ReplayImageResult(
            image_name=item.source_name,
            source_hand_id=item.source_hand_id,
            source_street=item.source_street,
            source_state_index=item.source_state_index,
            status="pending",
            source_hand_num=item.source_hand_num,
        )

        try:
            with Image.open(item.path) as img:
                current_image_holder["image"] = img.convert("RGB").copy()

            saved_paths = dac.run_ui_display_analysis_cycle(
                image_by_table_id={args.table_id: item.path},
                opened_table_ids={args.table_id},
                hand_tracker=hand_tracker,
                action_event_gate=action_event_gate,
                clear_json_state_machine=clear_json_state_machine,
                display_pass_id=f"replay_{index:06d}_{item.path.stem}",
                clear_previous_outputs_on_start=False,
                cycle_id=f"image_replay_v12_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            )

            result.saved_json_count = len(saved_paths)
            result.saved_json_paths = [str(Path(path)) for path in saved_paths]

            if not saved_paths:
                result.status = "skipped_no_new_json"
                result.warnings.append("no JSON saved; possible duplicate state blocked by ActionEventGate")
                print("[SKIP] no new JSON saved")
            else:
                state = _json_read(Path(saved_paths[-1]))
                state["replay_source"] = _build_replay_source_block(index, item)

                generated_json_path = replay_output_dir / "generated_json" / f"{index:03d}_{item.path.stem}.json"
                _write_json(generated_json_path, state)

                # Preserve the original Dark_JSON path returned by display_analysis_cycle, then
                # copy the technical state into generated_json for stable replay reports.
                state["__saved_dark_json_path"] = str(Path(saved_paths[-1]))

                errors, warnings, extracted = _validate_state(item, state)
                runtime_errors, runtime_warnings, runtime_extracted = _validate_runtime_contract(
                    item=item,
                    dark_state=state,
                )
                clear_errors, clear_warnings, clear_extracted = _validate_clear_json_artifacts(
                    item=item,
                    dark_state=state,
                    replay_output_dir=replay_output_dir,
                    index=index,
                )
                errors.extend(runtime_errors)
                warnings.extend(runtime_warnings)
                extracted.update(runtime_extracted)
                errors.extend(clear_errors)
                warnings.extend(clear_warnings)
                extracted.update(clear_extracted)
                extracted["generated_json_path"] = str(generated_json_path)

                result.errors.extend(errors)
                result.warnings.extend(warnings)
                result.extracted = extracted
                result.saved_json_paths = [str(generated_json_path)]

                signature = _canonical_signature(state)
                if signature in signature_seen:
                    result.warnings.append(f"canonical duplicate of {signature_seen[signature]}")
                else:
                    signature_seen[signature] = item.source_name

                current_positions = set(extracted.get("player_positions") or [])
                previous_positions = previous_positions_by_source_hand.get(item.source_hand_id)
                if previous_positions:
                    missing = sorted(previous_positions - current_positions)
                    if missing:
                        result.warnings.append(f"player positions disappeared vs previous same-hand state: {missing}")
                    previous_positions_by_source_hand[item.source_hand_id] = previous_positions | current_positions
                else:
                    previous_positions_by_source_hand[item.source_hand_id] = current_positions

                result.status = "ok" if not result.errors else "fail"

                print(
                    f"[JSON] saved={len(saved_paths)} frame={extracted.get('frame_name')} "
                    f"street={extracted.get('street')} board={extracted.get('board_card_count')} "
                    f"hero={extracted.get('hero_cards')} players={extracted.get('players_count')}"
                )
                if result.errors:
                    print(f"[FAIL] {result.errors}")
                elif result.warnings:
                    print(f"[WARN] {result.warnings}")
                else:
                    print("[OK]")

        except Exception as exc:
            result.status = "error"
            result.errors.append(str(exc))
            if args.traceback:
                result.errors.append(traceback.format_exc())
            print(f"[ERROR] {exc}")

        results.append(result)

    recovery_applied_total = sum(1 for item in results if item.extracted and item.extracted.get("recovery_applied"))
    recovery_present_total = sum(1 for item in results if item.extracted and item.extracted.get("recovery_present"))
    clear_saved_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("clear_json_contract_status") == "saved"
    )
    clear_skipped_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("clear_json_contract_status") == "skipped"
    )
    clear_pending_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("clear_json_pending_present")
    )
    decision_json_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("decision_json_present")
    )
    action_decision_json_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("action_decision_json_present")
    )
    action_runtime_plan_json_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("action_runtime_plan_json_present")
    )
    runtime_audit_present_total = sum(
        1
        for item in results
        if item.extracted and item.extracted.get("runtime_audit_present")
    )
    runtime_real_click_enabled_total = sum(
        1
        for item in results
        if item.extracted and (
            item.extracted.get("runtime_service_real_click_enabled")
            or item.extracted.get("runtime_action_button_real_click_enabled")
        )
    )
    runtime_click_points_total = sum(
        int(item.extracted.get("runtime_total_click_points_count") or 0)
        for item in results
        if item.extracted
    )

    summary = {
        "schema_version": "image-replay-cycle-v07-action-runtime-plan-audit",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "images_dir": str(images_dir),
        "output_dir": str(replay_output_dir),
        "table_id": args.table_id,
        "total_images": len(items),
        "status_counter": {},
        "saved_json_total": sum(item.saved_json_count for item in results),
        "clear_json_saved_total": clear_saved_total,
        "clear_json_skipped_total": clear_skipped_total,
        "clear_json_pending_total": clear_pending_total,
        "decision_json_total": decision_json_total,
        "action_decision_json_total": action_decision_json_total,
        "action_runtime_plan_json_total": action_runtime_plan_json_total,
        "recovery_present_total": recovery_present_total,
        "recovery_applied_total": recovery_applied_total,
        "runtime_audit_present_total": runtime_audit_present_total,
        "runtime_real_click_enabled_total": runtime_real_click_enabled_total,
        "runtime_click_points_total": runtime_click_points_total,
        "errors_total": sum(len(item.errors) for item in results),
        "warnings_total": sum(len(item.warnings) for item in results),
        "results": [asdict(item) for item in results],
    }

    for item in results:
        summary["status_counter"][item.status] = summary["status_counter"].get(item.status, 0) + 1

    report_json_path = replay_output_dir / "reports" / "image_replay_report.json"
    report_txt_path = replay_output_dir / "reports" / "image_replay_report.txt"

    _write_json(report_json_path, summary)

    txt_lines = [
        "IMAGE_REPLAY_CYCLE_V12",
        "=" * 100,
        f"Images dir:       {images_dir}",
        f"Output dir:       {replay_output_dir}",
        f"Table id:         {args.table_id}",
        f"Total images:     {summary['total_images']}",
        f"Saved JSON total: {summary['saved_json_total']}",
        f"Clear saved:      {summary['clear_json_saved_total']}",
        f"Clear skipped:    {summary['clear_json_skipped_total']}",
        f"Clear pending:    {summary['clear_json_pending_total']}",
        f"Decision JSON:    {summary['decision_json_total']}",
        f"Action Decision:  {summary['action_decision_json_total']}",
        f"Runtime Plan:     {summary['action_runtime_plan_json_total']}",
        f"Recovery present: {summary['recovery_present_total']}",
        f"Recovery applied: {summary['recovery_applied_total']}",
        f"Runtime audit:    {summary['runtime_audit_present_total']}",
        f"Runtime realclick:{summary['runtime_real_click_enabled_total']}",
        f"Runtime points:   {summary['runtime_click_points_total']}",
        f"Errors total:     {summary['errors_total']}",
        f"Warnings total:   {summary['warnings_total']}",
        f"Status counter:   {summary['status_counter']}",
        "",
        "Per-image result:",
    ]

    for item in results:
        txt_lines.append(
            f"- {item.image_name}: status={item.status}, saved={item.saved_json_count}, "
            f"street={item.extracted.get('street') if item.extracted else None}, "
            f"hero={item.extracted.get('hero_cards') if item.extracted else None}, "
            f"clear_status={item.extracted.get('clear_json_contract_status') if item.extracted else None}, "
            f"clear_reason={item.extracted.get('clear_json_contract_reason') if item.extracted else None}, "
            f"state_machine={item.extracted.get('state_machine_reason') if item.extracted else None}, "
            f"recovery_applied={item.extracted.get('recovery_applied') if item.extracted else None}, "
            f"recovery_rules={item.extracted.get('recovery_rules') if item.extracted else None}, "
            f"runtime_status={item.extracted.get('runtime_status') if item.extracted else None}, "
            f"service_status={item.extracted.get('runtime_service_status') if item.extracted else None}, "
            f"action_status={item.extracted.get('runtime_action_button_status') if item.extracted else None}, "
            f"realclick=({item.extracted.get('runtime_service_real_click_enabled') if item.extracted else None},"
            f"{item.extracted.get('runtime_action_button_real_click_enabled') if item.extracted else None}), "
            f"click_points={item.extracted.get('runtime_total_click_points_count') if item.extracted else None}, "
            f"action_decision={item.extracted.get('action_decision_json_status') if item.extracted else None}, "
            f"errors={len(item.errors)}, warnings={len(item.warnings)}"
        )
        for err in item.errors:
            txt_lines.append(f"    ERROR: {err}")
        for warn in item.warnings:
            txt_lines.append(f"    WARN:  {warn}")

    _write_text(report_txt_path, "\n".join(txt_lines) + "\n")

    print()
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Status counter:   {summary['status_counter']}")
    print(f"Saved JSON total: {summary['saved_json_total']}")
    print(f"Clear saved:      {summary['clear_json_saved_total']}")
    print(f"Clear skipped:    {summary['clear_json_skipped_total']}")
    print(f"Clear pending:    {summary['clear_json_pending_total']}")
    print(f"Decision JSON:    {summary['decision_json_total']}")
    print(f"Action Decision:  {summary['action_decision_json_total']}")
    print(f"Runtime Plan:     {summary['action_runtime_plan_json_total']}")
    print(f"Recovery present: {summary['recovery_present_total']}")
    print(f"Recovery applied: {summary['recovery_applied_total']}")
    print(f"Runtime audit:    {summary['runtime_audit_present_total']}")
    print(f"Runtime realclick:{summary['runtime_real_click_enabled_total']}")
    print(f"Runtime points:   {summary['runtime_click_points_total']}")
    print(f"Errors total:     {summary['errors_total']}")
    print(f"Warnings total:   {summary['warnings_total']}")
    print(f"Report JSON:      {report_json_path}")
    print(f"Report TXT:       {report_txt_path}")

    if summary["errors_total"] > 0 or summary["status_counter"].get("error", 0) > 0:
        print()
        print("[RESULT] FAIL: replay produced errors.")
        return 1

    if summary["warnings_total"] > 0 or summary["status_counter"].get("skipped_no_new_json", 0) > 0:
        print()
        print("[RESULT] WARNING: replay completed with warnings/skipped duplicate states.")
        return 0

    print()
    print("[RESULT] OK: replay completed without errors.")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PokerVision V1.2 safe image replay cycle tester.")
    parser.add_argument("--images-dir", default=None, help="Folder with hand_*.png/jpg replay images.")
    parser.add_argument("--output-dir", default=None, help="Replay output folder.")
    parser.add_argument("--table-id", default="table_01", help="Configured table slot id to use for all replay images. Default: table_01.")
    parser.add_argument("--max-images", type=int, default=None, help="Optional limit for quick partial replay.")
    parser.add_argument("--list-only", action="store_true", help="Only print sorted replay order. Do not run models.")
    parser.add_argument("--traceback", action="store_true", help="Write full Python traceback into report on exceptions.")
    parser.add_argument("--real-service-dry-run", action="store_true", help="Run real Trigger_UI service runtime in dry-run mode while keeping Action_Button runtime stubbed.")
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()
    return _run_replay(args)


if __name__ == "__main__":
    raise SystemExit(main())
