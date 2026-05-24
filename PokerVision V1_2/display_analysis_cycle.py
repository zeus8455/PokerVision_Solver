r"""
display_analysis_cycle.py

PokerVision Core V3.1 — live desktop analysis cycle + controlled live-click gate audit.

Что делает каждый display-pass:
1. При первом pass удаляет старую outputs/ui_display_cycle.
2. Делает screenshot основного монитора.
3. V1.2 обрабатывает реальные table_N области рабочего стола; тестовые изображения не открываются.
4. Запускает полный detector pipeline:
   Trigger UI -> Table Structure -> Players -> Digit Amounts -> Card Detection.
5. После детекций V1 HandIdentityTracker решает для каждой области table_N:
   - новая это раздача или продолжение прошлой;
   - base hand_id: hand_01, hand_02, ...;
   - frame_name для JSON: hand_01_preflop, hand_01_flop,
     hand_08_preflop_02 и т.д.
6. Сохраняет clean JSON с filename == frame_name.json.
7. V1.1 Stage 2: после сохранения JSON запускает безопасную runtime-цепочку
   solver_payload -> solver_stub -> Action_Button_Detector -> click dry-run report.
8. Не выполняет сверку с эталонными JSON; сохраняет только собственные результаты анализа.

Ключевое правило V1:
- отсутствие strong Active = отдельный hand_N без продолжения;
- strong Active + те же HERO cards Player_seat1 в той же table-области = та же раздача;
- strong Active + другие HERO cards = новая раздача.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config import (
    CARD_DETECTION_ENABLED,
    CARD_DETECTION_REQUIRE_PLAYERS,
    CLEAR_PREVIOUS_UI_DISPLAY_OUTPUTS_ON_BUTTON_CLICK,
    CURRENT_CYCLE_DIR_NAME,
    DEFAULT_DISPLAY_PASS_ID,
    DIGIT_AMOUNTS_ENABLED,
    DIGIT_AMOUNTS_REQUIRE_PLAYERS,
    PLAYER_STATE_ENABLED,
    PLAYER_STATE_REQUIRE_TABLE_STRUCTURE,
    RUNTIME_HAND_ID_PREFIX,
    RUNTIME_HAND_NUMBER_MIN_WIDTH,
    SAVE_DEBUG_DESKTOP_CAPTURE,
    SAVE_DEBUG_TABLE_CROPS,
    TABLE_STATUS_READY_FOR_STRUCTURE_PIPELINE,
    TABLE_STRUCTURE_ENABLED,
    TABLE_STRUCTURE_REQUIRE_ACTIVE,
    TRIGGER_UI_ENABLED,
    UI_DISPLAY_CYCLE_OUTPUT_DIR,
    V11_CLICK_DRY_RUN,
    V11_REAL_MOUSE_CLICK_ENABLED,
    V11_TRIGGER_UI_SERVICE_DRY_RUN,
    V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED,
    V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE,
    V03_TABLE_ACTION_TRANSACTION_GATE_ENABLED,
    V03_TRANSACTION_DRY_RUN_COUNTS_AS_COMPLETED,
    V03_TRANSACTION_RELEASE_ON_INACTIVE,
    V04_PENDING_FINAL_CLEAR_JSON_ENABLED,
    V04_CLEAR_JSON_PENDING_DIR_NAME,
    V04_CLEAR_JSON_FINAL_DIR_NAME,
    V04_FINAL_CLEAR_JSON_REQUIRES_CLICK_RESULT,
    V04_DELETE_PENDING_AFTER_FINAL_SAVE,
    V05_DECISION_JSON_ENABLED,
    V05_DECISION_JSON_DIR_NAME,
    V06_ACTION_DECISION_ENABLED,
    V06_ACTION_DECISION_DIR_NAME,
    V141_SOLVER_ACTION_DECISION_CANDIDATE_ENABLED,
    V141_SOLVER_ACTION_DECISION_CANDIDATE_DIR_NAME,
    V07_ACTION_RUNTIME_PLAN_ENABLED,
    V07_ACTION_RUNTIME_PLAN_DIR_NAME,
    V10_JSON_COMPLETE_DIR_NAME,
    V08_LIVE_HAND_CONTINUITY_ENABLED,
    V08_INACTIVE_DOES_NOT_RESET_HAND,
    V08_KEEP_LAST_HAND_ON_INVALID_HERO,
    V09_CLICK_EXECUTION_GUARD_ENABLED,
    V09_REAL_CLICK_MASTER_ARMED,
    V09_REQUIRE_SLOT_BOUNDARY_GUARD,
    V09_REQUIRE_NO_REPEAT_DECISION_GUARD,
    V09_REQUIRE_BUTTON_AVAILABILITY_GUARD,
    V09_REQUIRE_ACTION_RUNTIME_PLAN_SOURCE,
    V09_ALLOW_DRY_RUN_COMPLETION,
    V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK,
    V09_CLICK_CONFIRMATION_REPORT_ENABLED,
    V12_SAVE_ONLY_TRIGGERED_TABLES,
    ensure_dir,
)
from json_state import (
    add_error,
    add_warning,
    build_table_frame_state,
    elapsed_ms,
    now_perf_counter,
    save_table_frame_json,
)
from logic.clear_json_builder import (
    build_clear_json_from_dark_state,
    validate_clear_json_contract,
)
from logic.clear_json_recovery import recover_clear_json_state
from logic.decision_json_builder import (
    build_decision_json_from_clear_state,
    validate_decision_json_contract,
)
from logic.action_decision_stub import (
    build_action_decision_from_decision_json,
    validate_action_decision_contract,
)
from logic.action_runtime_plan_builder import (
    build_action_runtime_plan_from_action_decision,
    validate_action_runtime_plan_contract,
)
from logic.click_execution_guard import (
    ClickExecutionRequest,
    ClickGuardConfig,
    validate_click_execution_request,
)
from logic.controlled_real_click_scope import (
    ControlledRealClickScopeRequest,
    build_controlled_real_click_scope_from_config,
)
from logic.live_hand_continuity import (
    decide_live_hand_continuity,
    normalize_card_list,
)
from logic.clear_json_state_machine import ClearJsonStateMachine
from logic.poker_clear_solver_preview_adapter import build_clear_safe_solver_preview_blocks
from logic.poker_preflop_solver_preview_builder import build_preflop_solver_preview
from logic.solver_action_decision_candidate import (
    build_solver_action_decision_candidate_from_clear_json,
    validate_solver_action_decision_candidate,
)
from logic.table_action_transaction_gate import TableActionTransactionGate
from pipeline.card_detection_pipeline import run_card_detection_pipeline
from pipeline.digit_amounts_pipeline import run_digit_amounts_pipeline
from pipeline.player_state_pipeline import (
    build_skipped_player_state_block,
    run_player_state_pipeline,
)
from pipeline.table_structure_pipeline import (
    build_skipped_table_structure_block,
    run_table_structure_pipeline,
)
from pipeline.trigger_ui_pipeline import run_trigger_ui_pipeline
from table_slots import TableSlot, list_table_slots


try:
    from runtime.v11_stage1_runtime import run_v11_stage1_runtime as _run_v11_stage1_runtime
    V11_STAGE2_RUNTIME_AVAILABLE = True
    V11_STAGE2_IMPORT_ERROR: Optional[str] = None
except Exception as exc:
    _run_v11_stage1_runtime = None
    V11_STAGE2_RUNTIME_AVAILABLE = False
    V11_STAGE2_IMPORT_ERROR = str(exc)

try:
    from runtime.trigger_ui_service_runtime import (
        run_v11_trigger_ui_service_runtime as _run_v11_trigger_ui_service_runtime,
    )
    V11_STAGE25_SERVICE_RUNTIME_AVAILABLE = True
    V11_STAGE25_SERVICE_IMPORT_ERROR: Optional[str] = None
except Exception as exc:
    _run_v11_trigger_ui_service_runtime = None
    V11_STAGE25_SERVICE_RUNTIME_AVAILABLE = False
    V11_STAGE25_SERVICE_IMPORT_ERROR = str(exc)


try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except Exception:
    ImageGrab = None
    PIL_AVAILABLE = False


VALID_STREETS = {"preflop", "flop", "turn", "river"}

# Process-wide Clear_JSON state-machine used by live cycles when caller does not
# inject its own instance. Replay tests inject a fresh instance for deterministic runs.
_DEFAULT_CLEAR_JSON_STATE_MACHINE = ClearJsonStateMachine()
_DEFAULT_TABLE_ACTION_TRANSACTION_GATE = TableActionTransactionGate(
    dry_run_counts_as_completed=V03_TRANSACTION_DRY_RUN_COUNTS_AS_COMPLETED,
    release_on_inactive=V03_TRANSACTION_RELEASE_ON_INACTIVE,
)
_DEFAULT_EXECUTED_CLICK_DECISION_IDS_BY_TABLE: Dict[str, Set[str]] = {}
_DEFAULT_CONTROLLED_REAL_CLICK_SCOPE = build_controlled_real_click_scope_from_config()


@dataclass(frozen=True)
class FrameIdentity:
    hand_id: str
    frame_name: str
    is_continuation: bool
    active_confirmed: bool
    hero_cards_key: Optional[Tuple[str, str]]
    street: Optional[str]
    street_occurrence: Optional[int]
    warning: Optional[str] = None


@dataclass
class _TrackedTableHand:
    hand_id: str
    hero_cards_key: Tuple[str, str]
    street_counts: Dict[str, int] = field(default_factory=dict)
    last_board_cards: List[str] = field(default_factory=list)
    last_street: Optional[str] = None
    inactive_pass_count: int = 0




@dataclass(frozen=True)
class ActionEventDecision:
    """Runtime gate decision for one visible Active action spot."""

    should_process: bool
    action_event_id: Optional[str]
    action_signature: Optional[str]
    reason: str
    duplicate_of: Optional[str] = None
    event_index: Optional[int] = None

    def to_json(self) -> Dict[str, object]:
        return {
            "gate_version": "v12_action_event_gate_2026_05_12",
            "should_process": self.should_process,
            "action_event_id": self.action_event_id,
            "action_signature": self.action_signature,
            "reason": self.reason,
            "duplicate_of": self.duplicate_of,
            "event_index": self.event_index,
        }


@dataclass
class _ActionEventTableState:
    active_latched: bool = False
    no_active_pass_count: int = 0
    last_processed_signature: Optional[str] = None
    last_processed_event_id: Optional[str] = None
    event_index: int = 0


class ActionEventGate:
    """
    One-shot gate for Active frames.

    It prevents a live scan loop from creating a new JSON/solver payload every
    900 ms while the same Active spot is still visible. A new JSON is allowed
    only when the normalized action signature changes, or after Active has been
    absent for a small debounce window.
    """

    def __init__(self, *, inactive_reset_passes: int = 2) -> None:
        self.inactive_reset_passes = max(1, int(inactive_reset_passes))
        self._state_by_table_id: Dict[str, _ActionEventTableState] = {}

    def _state(self, table_id: str) -> _ActionEventTableState:
        if table_id not in self._state_by_table_id:
            self._state_by_table_id[table_id] = _ActionEventTableState()
        return self._state_by_table_id[table_id]

    def observe_inactive(self, table_id: str) -> None:
        state = self._state(table_id)
        state.no_active_pass_count += 1
        if state.no_active_pass_count >= self.inactive_reset_passes:
            state.active_latched = False
            state.last_processed_signature = None
            state.last_processed_event_id = None

    @staticmethod
    def _normalize_amount(value: Any) -> Optional[float | str]:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            return round(float(value), 2)
        text = str(value).strip()
        if not text:
            return None
        try:
            return round(float(text), 2)
        except ValueError:
            return text

    @staticmethod
    def _extract_board_cards(table_structure_block: Optional[Dict[str, Any]]) -> List[str]:
        classes = (table_structure_block or {}).get("classes") if isinstance(table_structure_block, dict) else None
        board = (classes or {}).get("Board") if isinstance(classes, dict) else None
        cards = (board or {}).get("cards") if isinstance(board, dict) else None
        return [str(card) for card in cards] if isinstance(cards, list) else []

    @classmethod
    def _extract_total_pot(cls, table_structure_block: Optional[Dict[str, Any]]) -> Optional[float | str]:
        classes = (table_structure_block or {}).get("classes") if isinstance(table_structure_block, dict) else None
        total_pot = (classes or {}).get("Total_pot") if isinstance(classes, dict) else None
        value = (total_pot or {}).get("value") if isinstance(total_pot, dict) else None
        return cls._normalize_amount(value)

    @classmethod
    def _extract_player_action_facts(cls, players_block: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, object]]:
        seats = (players_block or {}).get("seats") if isinstance(players_block, dict) else None
        if not isinstance(seats, dict):
            return {}

        facts: Dict[str, Dict[str, object]] = {}
        for seat_name in sorted(seats.keys()):
            seat = seats.get(seat_name)
            if not isinstance(seat, dict):
                continue
            chips = seat.get("chips") if isinstance(seat.get("chips"), dict) else {}
            stack = seat.get("stack") if isinstance(seat.get("stack"), dict) else {}
            facts[str(seat_name)] = {
                "position": seat.get("position"),
                "fold": bool(seat.get("fold", False)),
                "sitout": bool(seat.get("sitout", False)),
                "chips_detect": bool(chips.get("detect", False)),
                "chips_value": cls._normalize_amount(chips.get("value")),
                "all_in": bool(stack.get("all_in", False)),
            }
        return facts

    @staticmethod
    def _hash_payload(payload: Dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def build_signature(
        self,
        *,
        table_id: str,
        hero_cards: List[str],
        street: Optional[str],
        table_structure_block: Optional[Dict[str, Any]],
        players_block: Optional[Dict[str, Any]],
    ) -> str:
        payload: Dict[str, Any] = {
            "table_id": table_id,
            "hero_cards": sorted(str(card) for card in hero_cards if str(card).strip()),
            "street": str(street or "unknown").lower(),
            "board_cards": self._extract_board_cards(table_structure_block),
            "total_pot": self._extract_total_pot(table_structure_block),
            "player_action_facts": self._extract_player_action_facts(players_block),
        }
        return self._hash_payload(payload)

    def evaluate_active(
        self,
        *,
        table_id: str,
        hero_cards: List[str],
        street: Optional[str],
        table_structure_block: Optional[Dict[str, Any]],
        players_block: Optional[Dict[str, Any]],
    ) -> ActionEventDecision:
        state = self._state(table_id)
        state.no_active_pass_count = 0
        state.active_latched = True

        signature = self.build_signature(
            table_id=table_id,
            hero_cards=hero_cards,
            street=street,
            table_structure_block=table_structure_block,
            players_block=players_block,
        )

        if signature == state.last_processed_signature:
            return ActionEventDecision(
                should_process=False,
                action_event_id=None,
                action_signature=signature,
                reason="duplicate_active_frame_blocked",
                duplicate_of=state.last_processed_event_id,
                event_index=state.event_index,
            )

        state.event_index += 1
        event_id = f"evt_{table_id}_{signature[:16]}"
        state.last_processed_signature = signature
        state.last_processed_event_id = event_id
        return ActionEventDecision(
            should_process=True,
            action_event_id=event_id,
            action_signature=signature,
            reason="new_active_action_event",
            event_index=state.event_index,
        )


class HandIdentityTracker:
    """
    Stateful V1 resolver for real runtime identity.

    Tracker is deliberately independent from source test image names. It consumes
    only detector-derived facts from the current table frame.
    """

    def __init__(self) -> None:
        self._next_hand_number = 1
        self._active_hand_by_table_id: Dict[str, _TrackedTableHand] = {}

    def _allocate_hand_id(self) -> str:
        number = self._next_hand_number
        self._next_hand_number += 1
        return f"{RUNTIME_HAND_ID_PREFIX}_{number:0{RUNTIME_HAND_NUMBER_MIN_WIDTH}d}"

    @staticmethod
    def _normalize_hero_cards(hero_cards: List[str]) -> Optional[Tuple[str, str]]:
        clean = [str(card) for card in hero_cards if str(card).strip()]
        if len(clean) != 2 or len(set(clean)) != 2:
            return None
        return tuple(sorted(clean))  # order-independent hand identity

    @staticmethod
    def _normalize_street(street: Optional[str]) -> Optional[str]:
        normalized = str(street).strip().lower() if street is not None else None
        return normalized if normalized in VALID_STREETS else None

    @staticmethod
    def _build_frame_name(hand_id: str, street: Optional[str], occurrence: Optional[int]) -> str:
        if street is None:
            return hand_id
        if occurrence is None or occurrence <= 1:
            return f"{hand_id}_{street}"
        return f"{hand_id}_{street}_{occurrence:02d}"

    @staticmethod
    def _normalize_board_cards(board_cards: Optional[List[str]]) -> List[str]:
        return normalize_card_list(board_cards)

    @staticmethod
    def _update_tracked_context(
        tracked: _TrackedTableHand,
        *,
        board_cards: List[str],
        street: Optional[str],
    ) -> None:
        if board_cards and len(board_cards) >= len(tracked.last_board_cards):
            tracked.last_board_cards = list(board_cards)
        if street is not None:
            tracked.last_street = street
        tracked.inactive_pass_count = 0

    def resolve(
        self,
        *,
        table_id: str,
        active_confirmed: bool,
        hero_cards: List[str],
        street: Optional[str],
        board_cards: Optional[List[str]] = None,
    ) -> FrameIdentity:
        normalized_street = self._normalize_street(street)
        normalized_board_cards = self._normalize_board_cards(board_cards)

        if not active_confirmed:
            previous = self._active_hand_by_table_id.get(table_id)
            if previous is not None:
                previous.inactive_pass_count += 1

            if not V08_INACTIVE_DOES_NOT_RESET_HAND:
                self._active_hand_by_table_id.pop(table_id, None)

            hand_id = self._allocate_hand_id()
            return FrameIdentity(
                hand_id=hand_id,
                frame_name=hand_id,
                is_continuation=False,
                active_confirmed=False,
                hero_cards_key=None,
                street=None,
                street_occurrence=None,
            )

        hero_cards_key = self._normalize_hero_cards(hero_cards)
        previous = self._active_hand_by_table_id.get(table_id)

        # Без двух валидных HERO cards нельзя надёжно доказать continuation.
        # V0.8: missing HERO on a single Active frame must not erase the last
        # known hand; the frame itself remains invalid for Clear_JSON, but a
        # future frame may still prove continuation by HERO + board.
        if hero_cards_key is None:
            hand_id = self._allocate_hand_id()
            if not V08_KEEP_LAST_HAND_ON_INVALID_HERO:
                self._active_hand_by_table_id.pop(table_id, None)
            occurrence = 1 if normalized_street is not None else None
            warning = (
                f"{table_id}: strong Active detected, but HERO cards are not exactly two unique cards; "
                "continuation identity cannot be proven for this frame."
            )
            return FrameIdentity(
                hand_id=hand_id,
                frame_name=self._build_frame_name(hand_id, normalized_street, occurrence),
                is_continuation=False,
                active_confirmed=True,
                hero_cards_key=None,
                street=normalized_street,
                street_occurrence=occurrence,
                warning=warning,
            )

        continuity_decision = None
        is_continuation = False
        if previous is not None and V08_LIVE_HAND_CONTINUITY_ENABLED:
            continuity_decision = decide_live_hand_continuity(
                previous_hero_cards_key=previous.hero_cards_key,
                current_hero_cards_key=hero_cards_key,
                previous_board_cards=previous.last_board_cards,
                current_board_cards=normalized_board_cards,
                previous_street=previous.last_street,
                current_street=normalized_street,
            )
            is_continuation = continuity_decision.should_continue
        elif previous is not None:
            is_continuation = previous.hero_cards_key == hero_cards_key

        if is_continuation and previous is not None:
            tracked = previous
        else:
            tracked = _TrackedTableHand(
                hand_id=self._allocate_hand_id(),
                hero_cards_key=hero_cards_key,
                last_board_cards=list(normalized_board_cards),
                last_street=normalized_street,
            )
            self._active_hand_by_table_id[table_id] = tracked

        occurrence: Optional[int]
        if normalized_street is None:
            occurrence = None
        else:
            occurrence = tracked.street_counts.get(normalized_street, 0) + 1
            tracked.street_counts[normalized_street] = occurrence

        self._update_tracked_context(
            tracked,
            board_cards=normalized_board_cards,
            street=normalized_street,
        )

        warning = None
        if normalized_street is None:
            warning = (
                f"{table_id}: strong Active detected with valid HERO cards, but street is unknown; "
                "frame_name falls back to base hand_id."
            )
        elif continuity_decision is not None and not continuity_decision.should_continue and previous is not None:
            warning = (
                f"{table_id}: V0.8 live hand continuity rejected previous hand: "
                f"{continuity_decision.reason}; a new hand was started."
            )

        return FrameIdentity(
            hand_id=tracked.hand_id,
            frame_name=self._build_frame_name(tracked.hand_id, normalized_street, occurrence),
            is_continuation=is_continuation,
            active_confirmed=True,
            hero_cards_key=hero_cards_key,
            street=normalized_street,
            street_occurrence=occurrence,
            warning=warning,
        )

def make_cycle_id() -> str:
    return "cycle_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def clear_previous_outputs() -> None:
    if not CLEAR_PREVIOUS_UI_DISPLAY_OUTPUTS_ON_BUTTON_CLICK:
        return

    if UI_DISPLAY_CYCLE_OUTPUT_DIR.exists():
        shutil.rmtree(UI_DISPLAY_CYCLE_OUTPUT_DIR)


def build_cycle_dir() -> Path:
    return UI_DISPLAY_CYCLE_OUTPUT_DIR / CURRENT_CYCLE_DIR_NAME


def capture_primary_monitor():
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for monitor capture. Install: pip install pillow")
    return ImageGrab.grab(all_screens=False)


def crop_table_roi(slot: TableSlot, screenshot):
    bbox = slot.bbox
    return screenshot.crop((bbox.x1, bbox.y1, bbox.x2, bbox.y2))


def save_desktop_screenshot(cycle_dir: Path, screenshot, display_pass_id: str) -> Path:
    desktop_path = cycle_dir / "_debug" / display_pass_id / "desktop_capture.png"
    ensure_dir(desktop_path.parent)
    screenshot.save(desktop_path)
    return desktop_path


def validate_bbox_inside_screenshot(slot: TableSlot, screenshot_size: Dict[str, int]) -> None:
    bbox = slot.bbox
    if bbox.x2 > screenshot_size["w"] or bbox.y2 > screenshot_size["h"]:
        raise ValueError(
            f"{slot.table_id} bbox is outside screenshot. "
            f"bbox={bbox.to_json()}, screenshot_size={screenshot_size}"
        )


def save_table_crop(cycle_dir: Path, slot: TableSlot, table_roi, display_pass_id: str) -> Path:
    table_dir = cycle_dir / "_debug" / display_pass_id / "table_crops" / slot.table_id
    ensure_dir(table_dir)
    crop_path = table_dir / f"{slot.table_id}_display_crop.png"
    table_roi.save(crop_path)
    return crop_path


def _write_json_atomic(path: Path, data: Dict[str, object]) -> None:
    ensure_dir(path.parent)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def _build_table_lifecycle_gate_audit(
    decision: object,
    *,
    stage: str,
) -> Dict[str, object]:
    """Build a compact V2.1 audit block for the early per-table lifecycle gate."""
    if decision is None or not hasattr(decision, "to_json"):
        return {
            "schema_version": "table_lifecycle_gate_v2_1",
            "stage": str(stage),
            "status": "missing",
            "heavy_analysis_allowed": False,
            "heavy_analysis_blocked": True,
            "blocked_reason": "missing_lifecycle_decision",
        }

    payload = decision.to_json()
    if not isinstance(payload, dict):
        payload = {}

    lifecycle_stage = str(payload.get("lifecycle_stage") or "")
    is_analysis_stage = lifecycle_stage == "analysis_cycle" or str(stage) == "before_heavy_analysis"
    should_process = bool(payload.get("should_process", False))

    payload.update({
        "schema_version": "table_lifecycle_gate_v2_1",
        "stage": str(stage),
        "heavy_analysis_allowed": should_process if is_analysis_stage else payload.get("heavy_analysis_allowed"),
        "heavy_analysis_blocked": (not should_process) if is_analysis_stage else payload.get("heavy_analysis_blocked"),
        "blocked_reason": payload.get("reason") if is_analysis_stage and not should_process else payload.get("blocked_reason"),
    })
    return payload


def _safe_json_filename(value: object, *, fallback: str = "state") -> str:
    text = str(value or "").strip() or fallback
    safe_chars: List[str] = []
    for char in text:
        if char.isalnum() or char in {"_", "-", "."}:
            safe_chars.append(char)
        else:
            safe_chars.append("_")
    return "".join(safe_chars).strip("._") or fallback


def save_dark_table_frame_json(
    *,
    state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
    frame_name: str,
) -> Path:
    """Save full technical state as Dark_JSON."""
    filename = _safe_json_filename(frame_name, fallback="frame") + ".dark.json"
    path = cycle_dir / "Dark_JSON" / table_id / filename
    _write_json_atomic(path, state)
    return path


def save_pending_clear_table_frame_json(
    *,
    clear_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save a pre-action Clear_JSON candidate for diagnostics only."""
    frame_id = clear_state.get("frame_id") or "clear_state_candidate"
    filename = _safe_json_filename(frame_id, fallback="clear_state_candidate") + ".pending.json"
    path = cycle_dir / V04_CLEAR_JSON_PENDING_DIR_NAME / table_id / filename
    _write_json_atomic(path, clear_state)
    return path


def save_clear_table_frame_json(
    *,
    clear_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save final minimal poker-state Clear_JSON after action/click completion."""
    frame_id = clear_state.get("frame_id") or "clear_state"
    filename = _safe_json_filename(frame_id, fallback="clear_state") + ".json"
    path = cycle_dir / V04_CLEAR_JSON_FINAL_DIR_NAME / table_id / filename
    _write_json_atomic(path, clear_state)
    return path


def save_decision_table_frame_json(
    *,
    decision_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save compact Decision_JSON built from Clear_JSON only."""
    frame_id = decision_state.get("source_frame_id") or "decision_state"
    filename = _safe_json_filename(frame_id, fallback="decision_state") + ".decision.json"
    path = cycle_dir / V05_DECISION_JSON_DIR_NAME / table_id / filename
    _write_json_atomic(path, decision_state)
    return path



def save_solver_action_decision_candidate_table_frame_json(
    *,
    candidate_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save Solver_Action_Decision_Candidate_JSON without affecting runtime."""
    frame_id = str(
        candidate_state.get("source_clear_frame_id")
        or candidate_state.get("source_decision_frame_id")
        or "unknown_frame"
    )
    safe_table_id = str(table_id or "table_unknown")
    path = (
        cycle_dir
        / V141_SOLVER_ACTION_DECISION_CANDIDATE_DIR_NAME
        / safe_table_id
        / f"{frame_id}.solver_candidate.json"
    )
    _write_json_atomic(path, candidate_state)
    return path


def save_action_decision_table_frame_json(
    *,
    action_decision_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save compact Action_Decision_JSON built from Decision_JSON only."""
    frame_id = action_decision_state.get("source_decision_frame_id") or "action_decision_state"
    filename = _safe_json_filename(frame_id, fallback="action_decision_state") + ".action.json"
    path = cycle_dir / V06_ACTION_DECISION_DIR_NAME / table_id / filename
    _write_json_atomic(path, action_decision_state)
    return path


def save_action_runtime_plan_table_frame_json(
    *,
    runtime_plan_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save compact Action_Runtime_Plan_JSON built from Action_Decision_JSON only."""
    frame_id = runtime_plan_state.get("source_action_decision_frame_id") or "action_runtime_plan"
    filename = _safe_json_filename(frame_id, fallback="action_runtime_plan") + ".runtime_plan.json"
    path = cycle_dir / V07_ACTION_RUNTIME_PLAN_DIR_NAME / table_id / filename
    _write_json_atomic(path, runtime_plan_state)
    return path


def save_completed_json_table_frame_json(
    *,
    completed_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Path:
    """Save final completed-cycle JSON after Clear_JSON + action runtime completion."""
    frame_id = completed_state.get("frame_id") or "completed_state"
    filename = _safe_json_filename(frame_id, fallback="completed_state") + ".complete.json"
    path = cycle_dir / V10_JSON_COMPLETE_DIR_NAME / table_id / filename
    _write_json_atomic(path, completed_state)
    return path


def _extract_clear_hero_position_and_cards(clear_state: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Tuple[str, ...]]:
    """Return HERO logical position and normalized cards from a minimal Clear_JSON state."""
    if not isinstance(clear_state, dict):
        return None, tuple()
    players = clear_state.get("players")
    if not isinstance(players, dict):
        return None, tuple()
    for position, payload in players.items():
        if isinstance(payload, dict) and payload.get("hero") is True:
            cards = normalize_card_list(payload.get("cards"))
            return str(position), tuple(cards)
    return None, tuple()


def _clear_board_cards(clear_state: Optional[Dict[str, Any]]) -> Tuple[str, ...]:
    if not isinstance(clear_state, dict):
        return tuple()
    board = clear_state.get("board")
    if not isinstance(board, dict):
        return tuple()
    return tuple(normalize_card_list(board.get("cards")))


def _clear_street(clear_state: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(clear_state, dict):
        return None
    board = clear_state.get("board")
    if not isinstance(board, dict):
        return None
    street = board.get("street")
    return str(street).strip().lower() if street is not None else None


def _clear_total_pot(clear_state: Optional[Dict[str, Any]]) -> Optional[float]:
    if not isinstance(clear_state, dict):
        return None
    value = clear_state.get("Total_pot")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_click_decision_id(click_result: Optional[Dict[str, object]]) -> Optional[str]:
    if not isinstance(click_result, dict):
        return None
    decision_id = click_result.get("decision_id")
    text = str(decision_id).strip() if decision_id is not None else ""
    return text or None


def _extract_previous_click_decision_id(clear_state: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(clear_state, dict):
        return None
    click_result = clear_state.get("click_result")
    return _extract_click_decision_id(click_result if isinstance(click_result, dict) else None)


def _detect_final_clear_json_publication_block(
    *,
    previous_clear_state: Optional[Dict[str, Any]],
    current_clear_state: Dict[str, Any],
    click_result: Optional[Dict[str, object]],
) -> Optional[Dict[str, object]]:
    """
    V0.8 live safety guard before Final Clear_JSON publication.

    Blocks two live noise modes:
    - same click/dry-run decision_id reused for a later Final Clear_JSON;
    - same hand/street/board/pot/HERO cards while HERO logical position jumps.

    Dark_JSON, Pending Clear_JSON, Decision_JSON and RuntimePlan stay saved for diagnostics.
    """
    if not isinstance(previous_clear_state, dict):
        return None

    previous_decision_id = _extract_previous_click_decision_id(previous_clear_state)
    current_decision_id = _extract_click_decision_id(click_result)
    if previous_decision_id and current_decision_id and previous_decision_id == current_decision_id:
        return {
            "reason": "duplicate_click_result_reused",
            "message": "Final Clear_JSON publication blocked because click_result.decision_id was already used by previous final Clear_JSON for this table/hand.",
            "previous_decision_id": previous_decision_id,
            "current_decision_id": current_decision_id,
        }

    previous_hero_position, previous_hero_cards = _extract_clear_hero_position_and_cards(previous_clear_state)
    current_hero_position, current_hero_cards = _extract_clear_hero_position_and_cards(current_clear_state)
    if not previous_hero_position or not current_hero_position:
        return None
    if not previous_hero_cards or previous_hero_cards != current_hero_cards:
        return None

    same_street = _clear_street(previous_clear_state) == _clear_street(current_clear_state)
    same_board = _clear_board_cards(previous_clear_state) == _clear_board_cards(current_clear_state)
    prev_pot = _clear_total_pot(previous_clear_state)
    curr_pot = _clear_total_pot(current_clear_state)
    same_pot = prev_pot is not None and curr_pot is not None and abs(prev_pot - curr_pot) < 0.0001

    if same_street and same_board and same_pot and previous_hero_position != current_hero_position:
        return {
            "reason": "hero_position_drift_same_state",
            "message": "Final Clear_JSON publication blocked because HERO position changed while same HERO cards, board, street and Total_pot stayed unchanged.",
            "previous_hero_position": previous_hero_position,
            "current_hero_position": current_hero_position,
            "hero_cards": list(current_hero_cards),
            "street": _clear_street(current_clear_state),
            "Total_pot": curr_pot,
        }

    return None


def _click_guard_config() -> ClickGuardConfig:
    """Build V0.9 click guard config from project config flags."""
    return ClickGuardConfig(
        enabled=bool(V09_CLICK_EXECUTION_GUARD_ENABLED),
        real_click_master_armed=bool(V09_REAL_CLICK_MASTER_ARMED),
        require_slot_boundary_guard=bool(V09_REQUIRE_SLOT_BOUNDARY_GUARD),
        require_no_repeat_decision_guard=bool(V09_REQUIRE_NO_REPEAT_DECISION_GUARD),
        require_button_availability_guard=bool(V09_REQUIRE_BUTTON_AVAILABILITY_GUARD),
        allow_dry_run_completion=bool(V09_ALLOW_DRY_RUN_COMPLETION),
        block_real_click_when_live_capture_no_click=bool(V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK),
        live_data_capture_no_click_mode=bool(V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE),
        action_real_click_enabled=bool(V11_REAL_MOUSE_CLICK_ENABLED),
        action_dry_run=bool(V11_CLICK_DRY_RUN),
        required_plan_source=str(V09_REQUIRE_ACTION_RUNTIME_PLAN_SOURCE or "Action_Runtime_Plan_JSON"),
    )


def _slot_bbox_tuple_from_state(state: Dict[str, object]) -> Optional[Tuple[float, float, float, float]]:
    table = state.get("table") if isinstance(state.get("table"), dict) else {}
    bbox = table.get("slot_bbox") if isinstance(table, dict) else None
    if not isinstance(bbox, dict):
        return None
    try:
        return (float(bbox["x1"]), float(bbox["y1"]), float(bbox["x2"]), float(bbox["y2"]))
    except (KeyError, TypeError, ValueError):
        return None


def _load_runtime_plan_from_contract(runtime_plan_contract: Dict[str, object]) -> Dict[str, object]:
    path_text = str(runtime_plan_contract.get("path") or "").strip()
    if path_text:
        try:
            with Path(path_text).open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass
    # Fallback is intentionally permissive for diagnostics only. A strict guard
    # will reject this if schema/source do not satisfy ClickGuardConfig.
    return dict(runtime_plan_contract)


def _first_action_click_point(runtime_action: Dict[str, object]) -> Optional[Dict[str, object]]:
    action_button = runtime_action.get("action_button") if isinstance(runtime_action.get("action_button"), dict) else {}
    click_points = action_button.get("click_points") if isinstance(action_button, dict) else None
    if not isinstance(click_points, list):
        return None
    for point in click_points:
        if isinstance(point, dict):
            return point
    return None


def _click_point_xy(point_payload: Dict[str, object]) -> Optional[Tuple[float, float]]:
    raw = point_payload.get("global_click_point") if isinstance(point_payload, dict) else None
    if not isinstance(raw, dict):
        return None
    try:
        return float(raw["x"]), float(raw["y"])
    except (KeyError, TypeError, ValueError):
        return None


def _first_target_button_from_runtime_plan(plan: Dict[str, object]) -> str:
    target_sequence = plan.get("target_sequence")
    if isinstance(target_sequence, list) and target_sequence:
        return str(target_sequence[0])
    target_classes = plan.get("target_button_classes")
    if isinstance(target_classes, list) and target_classes:
        return str(target_classes[0])
    return ""


def _build_controlled_real_click_scope_report(
    *,
    state: Dict[str, object],
    table_id: str,
    click_result: Dict[str, object],
    runtime_plan_contract: Dict[str, object],
) -> Dict[str, object]:
    """Evaluate V1.1.3 ControlledRealClickScope before ClickExecutionGuard."""

    runtime_action = state.get("runtime_action") if isinstance(state.get("runtime_action"), dict) else {}
    action_button_block = runtime_action.get("action_button") if isinstance(runtime_action.get("action_button"), dict) else {}
    runtime_plan = _load_runtime_plan_from_contract(runtime_plan_contract)

    click_point_payload = _first_action_click_point(runtime_action)
    target_button = str((click_point_payload or {}).get("class_name") or "").strip()
    if not target_button:
        target_button = _first_target_button_from_runtime_plan(runtime_plan)

    target_sequence = runtime_plan.get("target_sequence")
    if not isinstance(target_sequence, list):
        target_sequence = click_result.get("target_sequence") if isinstance(click_result.get("target_sequence"), list) else []

    runtime_branch = str(
        runtime_plan.get("runtime_branch")
        or action_button_block.get("branch")
        or "action_button"
    )
    action = str(
        click_result.get("action")
        or runtime_plan.get("planned_action")
        or action_button_block.get("solver_action")
        or ""
    )
    decision_id = str(click_result.get("decision_id") or action_button_block.get("decision_id") or "")
    already_executed = _DEFAULT_EXECUTED_CLICK_DECISION_IDS_BY_TABLE.get(str(table_id), set())

    request = ControlledRealClickScopeRequest(
        table_id=str(table_id),
        runtime_branch=runtime_branch,
        action=action,
        decision_id=decision_id,
        target_button_class=target_button,
        target_sequence=target_sequence,
        dry_run=bool(click_result.get("dry_run", V11_CLICK_DRY_RUN)),
        real_click_enabled=bool(click_result.get("real_click_enabled", V11_REAL_MOUSE_CLICK_ENABLED)),
        source=str(runtime_plan.get("source") or runtime_plan_contract.get("source") or "Action_Runtime_Plan_JSON"),
        already_executed_decision_ids=already_executed,
    )
    return _DEFAULT_CONTROLLED_REAL_CLICK_SCOPE.evaluate(request)

def _build_click_execution_guard_report(
    *,
    state: Dict[str, object],
    table_id: str,
    hand_id: str,
    clear_state: Dict[str, Any],
    click_result: Dict[str, object],
    runtime_plan_contract: Dict[str, object],
) -> Dict[str, object]:
    """Validate V0.9 click guards and return Dark_JSON audit payload."""
    runtime_action = state.get("runtime_action") if isinstance(state.get("runtime_action"), dict) else {}
    runtime_plan = _load_runtime_plan_from_contract(runtime_plan_contract)
    slot_bbox = _slot_bbox_tuple_from_state(state)
    click_point_payload = _first_action_click_point(runtime_action)
    click_xy = _click_point_xy(click_point_payload or {}) if click_point_payload else None

    if slot_bbox is None:
        return {
            "schema_version": "click_result_v09",
            "status": "blocked",
            "reason": "missing_slot_bbox",
            "message": "ClickExecutionGuard cannot run because table.slot_bbox is missing or invalid.",
            "guard_passed": False,
            "guards": {},
        }
    target_button = str((click_point_payload or {}).get("class_name") or "").strip() or _first_target_button_from_runtime_plan(runtime_plan)
    synthetic_click_point_used = False
    if click_xy is None:
        # In replay / live no-click data-capture mode the Action_Button runtime may not
        # produce a physical click point even though the action plan is valid. Do not
        # block Final Clear_JSON for this diagnostic dry-run case. Use the slot center
        # only as a non-click guard placeholder so slot/no-repeat/button/master guards
        # can still be audited. Real-click mode remains blocked by ClickExecutionGuard
        # if a true button point is unavailable or master/no-click guards are not armed.
        dry_run_requested = bool(click_result.get("dry_run", V11_CLICK_DRY_RUN))
        real_click_requested = bool(click_result.get("real_click_enabled", V11_REAL_MOUSE_CLICK_ENABLED))
        if dry_run_requested and not real_click_requested:
            x1, y1, x2, y2 = slot_bbox
            click_xy = ((float(x1) + float(x2)) / 2.0, (float(y1) + float(y2)) / 2.0)
            synthetic_click_point_used = True
        else:
            return {
                "schema_version": "click_result_v09",
                "status": "blocked",
                "reason": "missing_click_point",
                "message": "ClickExecutionGuard cannot run because runtime_action.action_button.click_points has no valid global_click_point.",
                "guard_passed": False,
                "guards": {},
            }

    street = _clear_street(clear_state) or "unknown"
    decision_id = str(click_result.get("decision_id") or "")
    already_executed = _DEFAULT_EXECUTED_CLICK_DECISION_IDS_BY_TABLE.get(str(table_id), set())

    request = ClickExecutionRequest(
        table_id=str(table_id),
        hand_id=str(hand_id),
        street=str(street),
        decision_id=decision_id,
        action=str(click_result.get("action") or runtime_plan.get("planned_action") or "fold"),
        target_button_class=target_button,
        click_point=click_xy,
        slot_bbox=slot_bbox,
        action_runtime_plan=runtime_plan,
        already_executed_decision_ids=already_executed,
        dry_run=bool(click_result.get("dry_run", V11_CLICK_DRY_RUN)),
        real_click_enabled=bool(click_result.get("real_click_enabled", V11_REAL_MOUSE_CLICK_ENABLED)),
    )
    controlled_scope_report = _build_controlled_real_click_scope_report(
        state=state,
        table_id=table_id,
        click_result=click_result,
        runtime_plan_contract=runtime_plan_contract,
    )
    state["controlled_real_click_scope"] = controlled_scope_report
    runtime_action_block = state.get("runtime_action")
    if isinstance(runtime_action_block, dict):
        runtime_action_block["controlled_real_click_scope"] = controlled_scope_report

    if isinstance(controlled_scope_report, dict) and not bool(controlled_scope_report.get("scope_passed")):
        return {
            "schema_version": "click_result_v09",
            "status": "blocked",
            "reason": "controlled_real_click_scope_failed",
            "message": str(controlled_scope_report.get("message") or "Final Clear_JSON publication blocked by ControlledRealClickScope."),
            "guard_passed": False,
            "source": "ControlledRealClickScope",
            "runtime_plan_path": runtime_plan_contract.get("path"),
            "controlled_real_click_scope": controlled_scope_report,
            "guards": {"controlled_real_click_scope": False},
        }

    guard_result = validate_click_execution_request(request, _click_guard_config())
    guard_result["source"] = "ClickExecutionGuard"
    guard_result["runtime_plan_path"] = runtime_plan_contract.get("path")
    if synthetic_click_point_used:
        guard_result["diagnostic_click_point_source"] = "slot_center_no_click_placeholder"
        guard_result["message"] = (
            str(guard_result.get("message") or "")
            + " Synthetic slot-center point was used only for no-click/dry-run audit because no physical click point was available."
        ).strip()
    return guard_result


def _remember_executed_click_decision(table_id: str, click_result: Optional[Dict[str, object]]) -> None:
    decision_id = _extract_click_decision_id(click_result)
    if not decision_id:
        return
    table_key = str(table_id)
    if table_key not in _DEFAULT_EXECUTED_CLICK_DECISION_IDS_BY_TABLE:
        _DEFAULT_EXECUTED_CLICK_DECISION_IDS_BY_TABLE[table_key] = set()
    _DEFAULT_EXECUTED_CLICK_DECISION_IDS_BY_TABLE[table_key].add(decision_id)
    if isinstance(click_result, dict):
        dry_run = bool(click_result.get("dry_run", V11_CLICK_DRY_RUN))
        real_click_enabled = bool(click_result.get("real_click_enabled", V11_REAL_MOUSE_CLICK_ENABLED))
        status = str(click_result.get("status") or "").strip().lower()
        if real_click_enabled and not dry_run and status in {"clicked", "confirmed"}:
            _DEFAULT_CONTROLLED_REAL_CLICK_SCOPE.record_success(decision_id)


def _is_v31_confirmed_real_click_for_final_publication(
    *,
    state: Dict[str, object],
    click_result: Optional[Dict[str, object]],
) -> bool:
    """Return True when runtime already executed a V3.1-controlled real click.

    V3.3: Final Clear_JSON publication previously re-ran ClickExecutionGuard
    after runtime had already clicked. In real-click mode that can create a false
    post-click block, while Dark_JSON already proves the Action_Button click was
    protected by ROI guard + V3.1 gate + success record. This helper recognizes
    that exact confirmed path and allows final publication to proceed.
    """

    if not isinstance(click_result, dict):
        return False
    if str(click_result.get("status") or "").strip().lower() not in {"clicked", "confirmed"}:
        return False
    if bool(click_result.get("dry_run", True)):
        return False
    if not bool(click_result.get("real_click_enabled", False)):
        return False

    runtime_action = state.get("runtime_action") if isinstance(state.get("runtime_action"), dict) else {}
    action_button = runtime_action.get("action_button") if isinstance(runtime_action.get("action_button"), dict) else {}
    if not isinstance(action_button, dict):
        return False

    gate = action_button.get("controlled_live_click_gate")
    success = action_button.get("controlled_live_click_success")
    roi_guard = action_button.get("action_button_slot_roi_guard")

    if not isinstance(gate, dict) or not isinstance(success, dict):
        return False
    if str(gate.get("status") or "") != "CONTROLLED_LIVE_CLICK_GATE_PASSED":
        return False
    if not bool(gate.get("scope_passed")):
        return False
    if str(success.get("status") or "") != "CONTROLLED_LIVE_CLICK_SUCCESS_RECORDED":
        return False

    click_decision_id = str(click_result.get("decision_id") or "").strip()
    success_decision_id = str(success.get("decision_id") or "").strip()
    if click_decision_id and success_decision_id and click_decision_id != success_decision_id:
        return False

    if isinstance(roi_guard, dict):
        if not bool(roi_guard.get("ok")):
            return False
        if not bool(roi_guard.get("full_screen_search_blocked")):
            return False

    click_points = action_button.get("click_points")
    if isinstance(click_points, list) and click_points:
        if not all(isinstance(point, dict) and bool(point.get("inside_slot_bbox")) for point in click_points):
            return False

    return True



def _failed_active_finalization_release_reason(
    *,
    state: Dict[str, object],
    transaction_runtime_report: Optional[Dict[str, object]],
    clear_json_path: Optional[Path],
) -> Optional[Dict[str, object]]:
    """Return release metadata when an Active lifecycle cannot reach completion.

    V4.1: a strong Active frame may pass detector stages but fail Clear_JSON
    validation, Decision_JSON construction, Action_Decision, or RuntimePlan. In
    that case there is no valid click/dry-run completion path. Leaving the table
    transaction in waiting_click/click_pending blocks later streets. The caller
    uses this diagnostic decision to abort/release the open transaction while
    preserving Dark_JSON.
    """

    if clear_json_path is not None:
        return None
    if not isinstance(transaction_runtime_report, dict):
        return None
    if bool(transaction_runtime_report.get("click_completed")):
        return None

    contract = state.get("clear_json_contract") if isinstance(state.get("clear_json_contract"), dict) else {}
    runtime_action = state.get("runtime_action") if isinstance(state.get("runtime_action"), dict) else {}
    action_button = runtime_action.get("action_button") if isinstance(runtime_action.get("action_button"), dict) else {}
    action_plan = runtime_action.get("action_runtime_plan_contract") if isinstance(runtime_action.get("action_runtime_plan_contract"), dict) else {}

    contract_status = str(contract.get("status") or "").strip()
    contract_reason = str(contract.get("reason") or "").strip()
    transaction_status = str(transaction_runtime_report.get("status") or "").strip()
    transaction_reason = str(transaction_runtime_report.get("reason") or "").strip()
    transaction_phase = str(transaction_runtime_report.get("phase") or "").strip()
    click_result = transaction_runtime_report.get("click_result") if isinstance(transaction_runtime_report.get("click_result"), dict) else {}
    click_status = str(click_result.get("status") or "").strip()
    payload_status = str(action_button.get("payload_status") or "").strip()
    action_button_status = str(action_button.get("status") or "").strip()
    runtime_plan_status = str(action_plan.get("status") or "").strip()
    if not runtime_plan_status:
        action_decision_contract = contract.get("action_decision_contract") if isinstance(contract.get("action_decision_contract"), dict) else {}
        nested_plan = action_decision_contract.get("action_runtime_plan_contract") if isinstance(action_decision_contract.get("action_runtime_plan_contract"), dict) else {}
        runtime_plan_status = str(nested_plan.get("status") or "").strip()

    validation_failed = contract_status in {"validation_failed", "error"} or contract_reason in {
        "pending_clear_json_contract_validation_failed",
        "final_clear_json_contract_validation_failed",
        "clear_json_build_or_save_error",
    }
    no_runtime_plan = runtime_plan_status in {"not_built", "validation_failed", "error"}
    payload_failed = payload_status in {"error", "validation_failed"}
    runtime_skipped = click_status == "skipped" or action_button_status == "skipped"
    transaction_pending = transaction_status in {"pending", "skipped", ""} or transaction_reason == "click_cycle_not_completed"

    if not (validation_failed or no_runtime_plan or payload_failed):
        return None
    if not (transaction_pending or runtime_skipped or transaction_phase in {"waiting_click", "click_pending"}):
        return None

    if validation_failed:
        reason = contract_reason or "active_clear_json_validation_failed"
    elif no_runtime_plan:
        reason = "active_runtime_plan_not_built"
    else:
        reason = "active_action_payload_failed"

    return {
        "schema_version": "failed_active_finalization_release_v4_1",
        "status": "FAILED_ACTIVE_FINALIZATION_RELEASE_REQUIRED",
        "reason": reason,
        "contract_status": contract_status,
        "contract_reason": contract_reason,
        "transaction_status": transaction_status,
        "transaction_reason": transaction_reason,
        "transaction_phase": transaction_phase,
        "click_status": click_status,
        "payload_status": payload_status,
        "action_button_status": action_button_status,
        "runtime_plan_status": runtime_plan_status,
        "message": (
            "Strong Active frame could not build a valid Clear_JSON/Decision/RuntimePlan "
            "completion path. The table transaction must be released so later streets "
            "or new Active signatures are not blocked by an impossible click cycle."
        ),
    }


def _release_failed_active_finalization_if_needed(
    *,
    state: Dict[str, object],
    table_action_transaction_gate: Optional[TableActionTransactionGate],
    table_id: str,
    action_transaction_decision: object,
    transaction_runtime_report: Optional[Dict[str, object]],
    clear_json_path: Optional[Path],
) -> Optional[Dict[str, object]]:
    """Abort/release an open table transaction after failed Active finalization."""

    if table_action_transaction_gate is None:
        return None
    if action_transaction_decision is None or not bool(getattr(action_transaction_decision, "should_process", False)):
        return None

    release_decision = _failed_active_finalization_release_reason(
        state=state,
        transaction_runtime_report=transaction_runtime_report,
        clear_json_path=clear_json_path,
    )
    if not isinstance(release_decision, dict):
        return None

    release_reason = str(release_decision.get("reason") or "failed_active_finalization_released")
    release_message = str(release_decision.get("message") or release_reason)
    if hasattr(table_action_transaction_gate, "release_failed_active_finalization"):
        release_report = table_action_transaction_gate.release_failed_active_finalization(
            table_id=table_id,
            reason=release_reason,
            message=release_message,
        )
    else:
        release_report = table_action_transaction_gate.abort_analysis_cycle(
            table_id=table_id,
            reason=release_reason,
            message=release_message,
        )

    release_payload = {
        "schema_version": "failed_active_finalization_release_v4_1",
        "status": "FAILED_ACTIVE_FINALIZATION_RELEASED",
        "reason": release_reason,
        "decision": release_decision,
        "release_report": release_report,
        "message": release_message,
    }
    state["failed_active_finalization_release"] = release_payload

    runtime_report = state.get("action_transaction_runtime")
    if isinstance(runtime_report, dict):
        runtime_report["pre_release_status"] = runtime_report.get("status")
        runtime_report["pre_release_reason"] = runtime_report.get("reason")
        runtime_report["pre_release_phase"] = runtime_report.get("phase")
        runtime_report["status"] = "aborted"
        runtime_report["reason"] = "failed_active_finalization_released"
        runtime_report["phase"] = "aborted"
        runtime_report["click_completed"] = False
        runtime_report["v4_1_failed_active_finalization_release"] = release_payload

    contract = state.get("clear_json_contract")
    if isinstance(contract, dict):
        contract["v4_1_failed_active_finalization_release"] = release_payload

    return release_payload

def build_and_save_action_runtime_plan_contract(
    *,
    action_decision_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Dict[str, object]:
    """Build/save Action_Runtime_Plan_JSON and return a Dark_JSON contract block."""
    if not V07_ACTION_RUNTIME_PLAN_ENABLED:
        return {
            "enabled": False,
            "source": "Action_Decision_JSON",
            "path": None,
            "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
            "status": "disabled",
        }

    try:
        runtime_plan_state = build_action_runtime_plan_from_action_decision(action_decision_state)
        validation = validate_action_runtime_plan_contract(runtime_plan_state)
        if validation.get("ok"):
            path = save_action_runtime_plan_table_frame_json(
                runtime_plan_state=runtime_plan_state,
                cycle_dir=cycle_dir,
                table_id=table_id,
            )
            return {
                "enabled": True,
                "source": "Action_Decision_JSON",
                "path": str(path),
                "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
                "validation": validation,
                "status": "saved",
                "planned_action": runtime_plan_state.get("planned_action"),
                "target_sequence": runtime_plan_state.get("target_sequence"),
                "target_sequences": runtime_plan_state.get("target_sequences"),
                "runtime_branch": runtime_plan_state.get("runtime_branch"),
                "dry_run": runtime_plan_state.get("dry_run"),
                "real_click_enabled": runtime_plan_state.get("real_click_enabled"),
            }
        return {
            "enabled": True,
            "source": "Action_Decision_JSON",
            "path": None,
            "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
            "validation": validation,
            "status": "validation_failed",
        }
    except Exception as exc:
        return {
            "enabled": True,
            "source": "Action_Decision_JSON",
            "path": None,
            "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
            "validation": {"ok": False, "errors": [str(exc)], "warnings": []},
            "status": "error",
        }


def build_and_save_action_decision_contract(
    *,
    decision_state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
) -> Dict[str, object]:
    """Build/save Action_Decision_JSON and return a Dark_JSON contract block."""
    if not V06_ACTION_DECISION_ENABLED:
        return {
            "enabled": False,
            "source": "Decision_JSON",
            "path": None,
            "dir": V06_ACTION_DECISION_DIR_NAME,
            "status": "disabled",
        }

    try:
        action_decision_state = build_action_decision_from_decision_json(decision_state)
        validation = validate_action_decision_contract(action_decision_state)
        if validation.get("ok"):
            path = save_action_decision_table_frame_json(
                action_decision_state=action_decision_state,
                cycle_dir=cycle_dir,
                table_id=table_id,
            )
            runtime_plan_contract = build_and_save_action_runtime_plan_contract(
                action_decision_state=action_decision_state,
                cycle_dir=cycle_dir,
                table_id=table_id,
            )
            return {
                "enabled": True,
                "source": "Decision_JSON",
                "path": str(path),
                "dir": V06_ACTION_DECISION_DIR_NAME,
                "validation": validation,
                "status": "saved",
                "action": action_decision_state.get("action"),
                "size_policy": action_decision_state.get("size_policy"),
                "target_button_classes": action_decision_state.get("target_button_classes"),
                "action_runtime_plan_contract": runtime_plan_contract,
            }
        return {
            "enabled": True,
            "source": "Decision_JSON",
            "path": None,
            "dir": V06_ACTION_DECISION_DIR_NAME,
            "validation": validation,
            "status": "validation_failed",
        }
    except Exception as exc:
        return {
            "enabled": True,
            "source": "Decision_JSON",
            "path": None,
            "dir": V06_ACTION_DECISION_DIR_NAME,
            "validation": {"ok": False, "errors": [str(exc)], "warnings": []},
            "status": "error",
        }




def build_and_save_solver_action_decision_candidate_contract(
    *,
    clear_state: Dict[str, Any],
    cycle_dir: Path,
    table_id: str,
) -> Dict[str, object]:
    """Build/save Solver_Action_Decision_Candidate_JSON without affecting runtime."""
    if not V141_SOLVER_ACTION_DECISION_CANDIDATE_ENABLED:
        return {
            "enabled": False,
            "source": "Clear_JSON.engine_decision_preview",
            "path": None,
            "dir": V141_SOLVER_ACTION_DECISION_CANDIDATE_DIR_NAME,
            "status": "disabled",
        }

    try:
        candidate_state = build_solver_action_decision_candidate_from_clear_json(clear_state)
        validation = validate_solver_action_decision_candidate(candidate_state)

        if validation.get("ok"):
            path = save_solver_action_decision_candidate_table_frame_json(
                candidate_state=candidate_state,
                cycle_dir=cycle_dir,
                table_id=table_id,
            )
            return {
                "enabled": True,
                "source": "Clear_JSON.engine_decision_preview",
                "path": str(path),
                "dir": V141_SOLVER_ACTION_DECISION_CANDIDATE_DIR_NAME,
                "validation": validation,
                "status": "saved",
                "action": candidate_state.get("action"),
                "size_policy": candidate_state.get("size_policy"),
                "target_button_classes": candidate_state.get("target_button_classes"),
                "solver_stub": candidate_state.get("solver_stub"),
            }

        return {
            "enabled": True,
            "source": "Clear_JSON.engine_decision_preview",
            "path": None,
            "dir": V141_SOLVER_ACTION_DECISION_CANDIDATE_DIR_NAME,
            "validation": validation,
            "status": "validation_failed",
        }

    except Exception as exc:
        return {
            "enabled": True,
            "source": "Clear_JSON.engine_decision_preview",
            "path": None,
            "dir": V141_SOLVER_ACTION_DECISION_CANDIDATE_DIR_NAME,
            "validation": {"ok": False, "errors": [str(exc)], "warnings": []},
            "status": "error",
        }


def _attach_preflop_solver_preview_to_clear_state(clear_state: Dict[str, Any]) -> Dict[str, Any]:
    """Attach Clear_JSON-safe preflop solver preview blocks when available.

    Safe integration rule:
    - Never raises.
    - Does nothing for non-preflop or unsupported states.
    - Does not affect Action_Decision_JSON, runtime plan, or click execution.
    """
    if not isinstance(clear_state, dict):
        return clear_state

    board = clear_state.get("board")
    if not isinstance(board, dict) or board.get("street") != "preflop":
        return clear_state

    try:
        solver_preview = build_preflop_solver_preview(clear_state)
        solver_blocks = build_clear_safe_solver_preview_blocks(solver_preview)
        if isinstance(solver_blocks, dict):
            clear_state.update(solver_blocks)
    except Exception:
        # Keep final Clear_JSON publication independent from solver preview failures.
        return clear_state

    return clear_state


def save_dark_and_clear_table_frame_json(
    *,
    state: Dict[str, object],
    cycle_dir: Path,
    table_id: str,
    hand_id: str,
    frame_name: str,
    active_confirmed: bool,
    clear_json_state_machine: Optional[ClearJsonStateMachine] = None,
    clear_json_save_allowed: bool = True,
    clear_json_build_allowed: bool = True,
    clear_json_build_block_reason: Optional[str] = None,
    click_result: Optional[Dict[str, object]] = None,
) -> Tuple[Path, Optional[Path]]:
    """
    Save Dark_JSON for every persisted frame.

    V0.4/V0.7 publication discipline:
    - Active poker-state first creates Clear_JSON_Pending for diagnostics.
    - Decision_JSON is built only from validated Clear_JSON candidate.
    - Final Clear_JSON is saved only after the action transaction confirms a
      completed click/dry-run cycle and a compact click_result can be attached.
    - If action/click is not completed, no final Clear_JSON is published.
    - V4.0 duplicate Active frames can hard-stop before Pending/Decision so
      only Dark_JSON audit is preserved for those repeated frames.
    """
    clear_path: Optional[Path] = None
    pending_path: Optional[Path] = None

    if not active_confirmed:
        state["clear_json_contract"] = {
            "status": "skipped",
            "reason": "not_active_poker_state",
            "publication_stage": "dark_json_only",
            "message": "Clear_JSON is not saved for service/inactive frames.",
        }
    elif not clear_json_build_allowed:
        block_reason = str(clear_json_build_block_reason or "clear_json_build_suppressed_before_pending_decision")
        state["clear_json_contract"] = {
            "status": "skipped",
            "reason": block_reason,
            "publication_stage": "dark_json_only",
            "pending_path": None,
            "path": None,
            "hard_stop_before_pending_decision": True,
            "message": (
                "Clear_JSON_Pending, Decision_JSON, Action_Decision_JSON and "
                "Action_Runtime_Plan_JSON were not built for this frame. "
                "Only Dark_JSON audit was preserved."
            ),
            "publication": {
                "pending_dir": V04_CLEAR_JSON_PENDING_DIR_NAME,
                "final_dir": V04_CLEAR_JSON_FINAL_DIR_NAME,
                "pending_path": None,
                "final_path": None,
                "final_requires_click_result": bool(V04_FINAL_CLEAR_JSON_REQUIRES_CLICK_RESULT),
            },
            "decision_json_contract": {
                "enabled": bool(V05_DECISION_JSON_ENABLED),
                "source": "Clear_JSON",
                "path": None,
                "dir": V05_DECISION_JSON_DIR_NAME,
                "status": "not_built_duplicate_active_hard_stop",
            },
            "action_decision_contract": {
                "enabled": bool(V06_ACTION_DECISION_ENABLED),
                "source": "Decision_JSON",
                "path": None,
                "dir": V06_ACTION_DECISION_DIR_NAME,
                "status": "not_built_duplicate_active_hard_stop",
                "action_runtime_plan_contract": {
                    "enabled": bool(V07_ACTION_RUNTIME_PLAN_ENABLED),
                    "source": "Action_Decision_JSON",
                    "path": None,
                    "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
                    "status": "not_built_duplicate_active_hard_stop",
                },
            },
        }
    else:
        try:
            clear_state_candidate = build_clear_json_from_dark_state(state)

            recovery_report: Dict[str, object] = {
                "status": "not_applied",
                "reason": "state_machine_not_provided",
            }
            previous_clear_state: Optional[Dict[str, Any]] = None
            if clear_json_state_machine is not None:
                previous_clear_state = clear_json_state_machine.get_last_clear_json(
                    table_id=table_id,
                    hand_id=hand_id,
                )
                clear_state_candidate, recovery_report = recover_clear_json_state(
                    current_clear=clear_state_candidate,
                    previous_clear=previous_clear_state,
                )

            pending_validation = validate_clear_json_contract(clear_state_candidate)
            decision_json_path: Optional[Path] = None
            decision_json_validation: Dict[str, object] = {"ok": False, "errors": ["Decision_JSON was not built."], "warnings": []}
            action_decision_contract: Dict[str, object] = {
                "enabled": bool(V06_ACTION_DECISION_ENABLED),
                "source": "Decision_JSON",
                "path": None,
                "dir": V06_ACTION_DECISION_DIR_NAME,
                "status": "not_built",
                "action_runtime_plan_contract": {
                    "enabled": bool(V07_ACTION_RUNTIME_PLAN_ENABLED),
                    "source": "Action_Decision_JSON",
                    "path": None,
                    "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
                    "status": "not_built",
                },
            }
            if pending_validation.get("ok"):
                pending_path = save_pending_clear_table_frame_json(
                    clear_state=clear_state_candidate,
                    cycle_dir=cycle_dir,
                    table_id=table_id,
                )
                if V05_DECISION_JSON_ENABLED:
                    try:
                        decision_state = build_decision_json_from_clear_state(clear_state_candidate)
                        decision_json_validation = validate_decision_json_contract(decision_state)
                        if decision_json_validation.get("ok"):
                            decision_json_path = save_decision_table_frame_json(
                                decision_state=decision_state,
                                cycle_dir=cycle_dir,
                                table_id=table_id,
                            )
                            action_decision_contract = build_and_save_action_decision_contract(
                                decision_state=decision_state,
                                cycle_dir=cycle_dir,
                                table_id=table_id,
                            )
                            if action_decision_contract.get("status") not in {"saved", "disabled"}:
                                for message in action_decision_contract.get("validation", {}).get("errors", []) if isinstance(action_decision_contract.get("validation"), dict) else []:
                                    add_error(state, block="action_decision_contract", message=str(message))
                        else:
                            for message in decision_json_validation.get("errors", []) if isinstance(decision_json_validation, dict) else []:
                                add_error(state, block="decision_json_contract", message=str(message))
                    except Exception as exc:
                        decision_json_validation = {"ok": False, "errors": [str(exc)], "warnings": []}
                        add_error(state, block="decision_json_contract", message=str(exc))
            elif V05_DECISION_JSON_ENABLED:
                decision_json_validation = {"ok": False, "errors": ["Pending Clear_JSON validation failed; Decision_JSON was not built."], "warnings": []}

            state["clear_json_contract"] = {
                "status": "pending",
                "reason": "clear_json_candidate_waiting_for_action_result",
                "publication_stage": "pending",
                "pending_path": str(pending_path) if pending_path else None,
                "path": None,
                "recovery": recovery_report,
                "pending_validation": pending_validation,
                "publication": {
                    "pending_dir": V04_CLEAR_JSON_PENDING_DIR_NAME,
                    "final_dir": V04_CLEAR_JSON_FINAL_DIR_NAME,
                    "pending_path": str(pending_path) if pending_path else None,
                    "final_path": None,
                    "final_requires_click_result": bool(V04_FINAL_CLEAR_JSON_REQUIRES_CLICK_RESULT),
                },
                "decision_json_contract": {
                    "enabled": bool(V05_DECISION_JSON_ENABLED),
                    "source": "Clear_JSON",
                    "path": str(decision_json_path) if decision_json_path else None,
                    "dir": V05_DECISION_JSON_DIR_NAME,
                    "validation": decision_json_validation,
                    "status": "saved" if decision_json_path else ("skipped" if not V05_DECISION_JSON_ENABLED else "validation_failed"),
                },
                "action_decision_contract": action_decision_contract,
            }

            if not pending_validation.get("ok"):
                state["clear_json_contract"].update({
                    "status": "validation_failed",
                    "reason": "pending_clear_json_contract_validation_failed",
                    "message": "Pending Clear_JSON candidate failed validation; final Clear_JSON was not published.",
                })
                for message in pending_validation.get("errors", []) if isinstance(pending_validation, dict) else []:
                    add_error(state, block="clear_json_contract", message=str(message))
                for message in pending_validation.get("warnings", []) if isinstance(pending_validation, dict) else []:
                    add_warning(state, block="clear_json_contract", message=str(message))
            elif not clear_json_save_allowed:
                state["clear_json_contract"].update({
                    "status": "skipped",
                    "reason": "action_transaction_not_completed",
                    "publication_stage": "pending_only",
                    "message": "Final Clear_JSON is not published because the Active action/click transaction did not complete.",
                })
            elif V04_FINAL_CLEAR_JSON_REQUIRES_CLICK_RESULT and not isinstance(click_result, dict):
                state["clear_json_contract"].update({
                    "status": "skipped",
                    "reason": "missing_click_result_for_final_clear_json",
                    "publication_stage": "pending_only",
                    "message": "Final Clear_JSON requires compact click_result.",
                })
                add_error(state, block="clear_json_contract", message="Final Clear_JSON requires compact click_result.")
            else:
                click_execution_guard_report: Optional[Dict[str, object]] = None
                if isinstance(click_result, dict) and V09_CLICK_CONFIRMATION_REPORT_ENABLED:
                    runtime_plan_contract_for_guard = {}
                    if isinstance(action_decision_contract, dict):
                        maybe_plan = action_decision_contract.get("action_runtime_plan_contract")
                        if isinstance(maybe_plan, dict):
                            runtime_plan_contract_for_guard = maybe_plan
                    click_execution_guard_report = _build_click_execution_guard_report(
                        state=state,
                        table_id=table_id,
                        hand_id=hand_id,
                        clear_state=clear_state_candidate,
                        click_result=click_result,
                        runtime_plan_contract=runtime_plan_contract_for_guard,
                    )
                    state["click_execution_guard"] = click_execution_guard_report
                    runtime_action_block = state.get("runtime_action")
                    if isinstance(runtime_action_block, dict):
                        runtime_action_block["click_execution_guard"] = click_execution_guard_report

                v31_confirmed_real_click = _is_v31_confirmed_real_click_for_final_publication(
                    state=state,
                    click_result=click_result,
                )

                if (
                    isinstance(click_execution_guard_report, dict)
                    and not bool(click_execution_guard_report.get("guard_passed"))
                    and not v31_confirmed_real_click
                ):
                    state["clear_json_contract"].update({
                        "status": "skipped",
                        "reason": "click_execution_guard_failed",
                        "publication_stage": "pending_only",
                        "path": None,
                        "click_execution_guard": click_execution_guard_report,
                        "message": str(click_execution_guard_report.get("message") or "Final Clear_JSON publication blocked by V0.9 ClickExecutionGuard."),
                    })
                    add_warning(
                        state,
                        block="click_execution_guard",
                        message=str(click_execution_guard_report.get("message") or "Final Clear_JSON publication blocked by V0.9 ClickExecutionGuard."),
                    )
                else:
                    if (
                        isinstance(click_execution_guard_report, dict)
                        and not bool(click_execution_guard_report.get("guard_passed"))
                        and v31_confirmed_real_click
                    ):
                        click_execution_guard_report["v33_final_publication_override"] = {
                            "schema_version": "v3_3_final_clear_real_clicked_publication",
                            "status": "allowed",
                            "reason": "v31_confirmed_real_click_already_executed",
                            "message": "Final Clear_JSON publication allowed because V3.1 controlled live-click gate already executed and recorded this real Action_Button click.",
                        }
                        state["clear_json_contract"]["v33_final_publication_override"] = click_execution_guard_report["v33_final_publication_override"]
                    # Keep Final Clear_JSON.click_result compact and schema-safe.
                    # The full V0.9 guard audit remains in Dark_JSON.click_execution_guard
                    # and runtime_action.click_execution_guard; it is intentionally not
                    # copied into final Clear_JSON.click_result.
                    final_publication_block = _detect_final_clear_json_publication_block(
                        previous_clear_state=previous_clear_state,
                        current_clear_state=clear_state_candidate,
                        click_result=click_result,
                    )
                    if isinstance(final_publication_block, dict):
                        state["clear_json_contract"].update({
                            "status": "skipped",
                            "reason": final_publication_block.get("reason", "final_clear_json_publication_blocked"),
                            "publication_stage": "pending_only",
                            "path": None,
                            "final_publication_guard": final_publication_block,
                            "message": final_publication_block.get("message", "Final Clear_JSON publication blocked by V0.8 final publication guard."),
                        })
                        add_warning(
                            state,
                            block="clear_json_contract",
                            message=str(final_publication_block.get("message", "Final Clear_JSON publication blocked by V0.8 final publication guard.")),
                        )
                    elif clear_json_state_machine is not None:
                        decision, clear_state_to_save = clear_json_state_machine.observe(
                            table_id=table_id,
                            hand_id=hand_id,
                            clear_json=clear_state_candidate,
                        )
                        state["clear_json_contract"].update({
                            "status": "saved" if decision.should_save else "skipped",
                            "reason": decision.reason,
                            "publication_stage": "final" if decision.should_save else "pending_only",
                            "state_machine": decision.to_json(),
                        })
    
                        if decision.should_save and clear_state_to_save is not None:
                            final_clear_state = dict(clear_state_to_save)
                            if click_result is not None:
                                final_clear_state["click_result"] = dict(click_result)
                            final_clear_state = _attach_preflop_solver_preview_to_clear_state(final_clear_state)
                            validation = validate_clear_json_contract(final_clear_state)
                            if validation.get("ok"):
                                clear_path = save_clear_table_frame_json(
                                    clear_state=final_clear_state,
                                    cycle_dir=cycle_dir,
                                    table_id=table_id,
                                )
                                state["clear_json_contract"].update({
                                    "path": str(clear_path),
                                    "validation": validation,
                                })
                                if V05_DECISION_JSON_ENABLED:
                                    try:
                                        final_decision_state = build_decision_json_from_clear_state(final_clear_state)
                                        final_decision_validation = validate_decision_json_contract(final_decision_state)
                                        if final_decision_validation.get("ok"):
                                            final_decision_path = save_decision_table_frame_json(
                                                decision_state=final_decision_state,
                                                cycle_dir=cycle_dir,
                                                table_id=table_id,
                                            )
                                            final_action_decision_contract = build_and_save_action_decision_contract(
                                                decision_state=final_decision_state,
                                                cycle_dir=cycle_dir,
                                                table_id=table_id,
                                            )
                                            if final_action_decision_contract.get("status") not in {"saved", "disabled"}:
                                                for message in final_action_decision_contract.get("validation", {}).get("errors", []) if isinstance(final_action_decision_contract.get("validation"), dict) else []:
                                                    add_error(state, block="action_decision_contract", message=str(message))
                                            state["clear_json_contract"]["action_decision_contract"] = final_action_decision_contract
                                            final_solver_candidate_contract = build_and_save_solver_action_decision_candidate_contract(
                                                clear_state=final_clear_state,
                                                cycle_dir=cycle_dir,
                                                table_id=table_id,
                                            )
                                            if final_solver_candidate_contract.get("status") not in {"saved", "disabled"}:
                                                for message in final_solver_candidate_contract.get("validation", {}).get("errors", []) if isinstance(final_solver_candidate_contract.get("validation"), dict) else []:
                                                    add_error(state, block="solver_action_decision_candidate_contract", message=str(message))
                                            state["clear_json_contract"]["solver_action_decision_candidate_contract"] = final_solver_candidate_contract
                                            state["clear_json_contract"]["decision_json_contract"] = {
                                                "enabled": True,
                                                "source": "Clear_JSON",
                                                "path": str(final_decision_path),
                                                "dir": V05_DECISION_JSON_DIR_NAME,
                                                "validation": final_decision_validation,
                                                "status": "saved",
                                            }
                                        else:
                                            state["clear_json_contract"]["decision_json_contract"] = {
                                                "enabled": True,
                                                "source": "Clear_JSON",
                                                "path": None,
                                                "dir": V05_DECISION_JSON_DIR_NAME,
                                                "validation": final_decision_validation,
                                                "status": "validation_failed",
                                            }
                                            for message in final_decision_validation.get("errors", []) if isinstance(final_decision_validation, dict) else []:
                                                add_error(state, block="decision_json_contract", message=str(message))
                                    except Exception as exc:
                                        state["clear_json_contract"]["decision_json_contract"] = {
                                            "enabled": True,
                                            "source": "Clear_JSON",
                                            "path": None,
                                            "dir": V05_DECISION_JSON_DIR_NAME,
                                            "validation": {"ok": False, "errors": [str(exc)], "warnings": []},
                                            "status": "error",
                                        }
                                        add_error(state, block="decision_json_contract", message=str(exc))
                                publication = state["clear_json_contract"].get("publication")
                                if isinstance(publication, dict):
                                    publication["final_path"] = str(clear_path)
                                _remember_executed_click_decision(table_id, click_result if isinstance(click_result, dict) else None)
                                if V04_DELETE_PENDING_AFTER_FINAL_SAVE and pending_path is not None:
                                    try:
                                        pending_path.unlink(missing_ok=True)
                                        state["clear_json_contract"]["pending_deleted_after_final_save"] = True
                                    except Exception as exc:
                                        add_warning(state, block="clear_json_contract", message=f"Failed to delete pending Clear_JSON: {exc}")
                            else:
                                state["clear_json_contract"].update({
                                    "status": "validation_failed",
                                    "reason": "final_clear_json_contract_validation_failed",
                                    "validation": validation,
                                    "path": None,
                                })
                                for message in validation.get("errors", []) if isinstance(validation, dict) else []:
                                    add_error(state, block="clear_json_contract", message=str(message))
                                for message in validation.get("warnings", []) if isinstance(validation, dict) else []:
                                    add_warning(state, block="clear_json_contract", message=str(message))
                        else:
                            state["clear_json_contract"].update({
                                "path": None,
                                "message": "Clear_JSON candidate was not persisted as final by state-machine.",
                            })
                            for message in decision.validation_errors:
                                add_error(state, block="clear_json_contract", message=str(message))
                            for message in decision.validation_warnings:
                                add_warning(state, block="clear_json_contract", message=str(message))
                    else:
                        final_clear_state = dict(clear_state_candidate)
                        if click_result is not None:
                            final_clear_state["click_result"] = dict(click_result)
                        final_clear_state = _attach_preflop_solver_preview_to_clear_state(final_clear_state)
                        validation = validate_clear_json_contract(final_clear_state)
                        if validation.get("ok"):
                            clear_path = save_clear_table_frame_json(
                                clear_state=final_clear_state,
                                cycle_dir=cycle_dir,
                                table_id=table_id,
                            )
                            state["clear_json_contract"].update({
                                "status": "saved",
                                "reason": "state_machine_not_provided",
                                "publication_stage": "final",
                                "path": str(clear_path),
                                "validation": validation,
                            })
                            if V05_DECISION_JSON_ENABLED:
                                try:
                                    final_decision_state = build_decision_json_from_clear_state(final_clear_state)
                                    final_decision_validation = validate_decision_json_contract(final_decision_state)
                                    if final_decision_validation.get("ok"):
                                        final_decision_path = save_decision_table_frame_json(
                                            decision_state=final_decision_state,
                                            cycle_dir=cycle_dir,
                                            table_id=table_id,
                                        )
                                        final_action_decision_contract = build_and_save_action_decision_contract(
                                            decision_state=final_decision_state,
                                            cycle_dir=cycle_dir,
                                            table_id=table_id,
                                        )
                                        if final_action_decision_contract.get("status") not in {"saved", "disabled"}:
                                            for message in final_action_decision_contract.get("validation", {}).get("errors", []) if isinstance(final_action_decision_contract.get("validation"), dict) else []:
                                                add_error(state, block="action_decision_contract", message=str(message))
                                        state["clear_json_contract"]["action_decision_contract"] = final_action_decision_contract
                                        final_solver_candidate_contract = build_and_save_solver_action_decision_candidate_contract(
                                            clear_state=final_clear_state,
                                            cycle_dir=cycle_dir,
                                            table_id=table_id,
                                        )
                                        if final_solver_candidate_contract.get("status") not in {"saved", "disabled"}:
                                            for message in final_solver_candidate_contract.get("validation", {}).get("errors", []) if isinstance(final_solver_candidate_contract.get("validation"), dict) else []:
                                                add_error(state, block="solver_action_decision_candidate_contract", message=str(message))
                                        state["clear_json_contract"]["solver_action_decision_candidate_contract"] = final_solver_candidate_contract
                                        state["clear_json_contract"]["decision_json_contract"] = {
                                            "enabled": True,
                                            "source": "Clear_JSON",
                                            "path": str(final_decision_path),
                                            "dir": V05_DECISION_JSON_DIR_NAME,
                                            "validation": final_decision_validation,
                                            "status": "saved",
                                        }
                                    else:
                                        state["clear_json_contract"]["decision_json_contract"] = {
                                            "enabled": True,
                                            "source": "Clear_JSON",
                                            "path": None,
                                            "dir": V05_DECISION_JSON_DIR_NAME,
                                            "validation": final_decision_validation,
                                            "status": "validation_failed",
                                        }
                                        for message in final_decision_validation.get("errors", []) if isinstance(final_decision_validation, dict) else []:
                                            add_error(state, block="decision_json_contract", message=str(message))
                                except Exception as exc:
                                    state["clear_json_contract"]["decision_json_contract"] = {
                                        "enabled": True,
                                        "source": "Clear_JSON",
                                        "path": None,
                                        "dir": V05_DECISION_JSON_DIR_NAME,
                                        "validation": {"ok": False, "errors": [str(exc)], "warnings": []},
                                        "status": "error",
                                    }
                                    add_error(state, block="decision_json_contract", message=str(exc))
                            publication = state["clear_json_contract"].get("publication")
                            if isinstance(publication, dict):
                                publication["final_path"] = str(clear_path)
                            _remember_executed_click_decision(table_id, click_result if isinstance(click_result, dict) else None)
                        else:
                            state["clear_json_contract"].update({
                                "status": "validation_failed",
                                "reason": "final_clear_json_contract_validation_failed",
                                "validation": validation,
                            })
                            for message in validation.get("errors", []) if isinstance(validation, dict) else []:
                                add_error(state, block="clear_json_contract", message=str(message))
                            for message in validation.get("warnings", []) if isinstance(validation, dict) else []:
                                add_warning(state, block="clear_json_contract", message=str(message))
        except Exception as exc:
            state["clear_json_contract"] = {
                "status": "error",
                "reason": "clear_json_build_or_save_error",
                "message": str(exc),
            }
            add_error(state, block="clear_json_contract", message=str(exc))

    # V0.7: expose the Action_Runtime_Plan contract inside runtime_action for Dark_JSON audit.
    try:
        contract = state.get("clear_json_contract") if isinstance(state.get("clear_json_contract"), dict) else {}
        action_decision_contract = contract.get("action_decision_contract") if isinstance(contract.get("action_decision_contract"), dict) else {}
        runtime_plan_contract = action_decision_contract.get("action_runtime_plan_contract") if isinstance(action_decision_contract.get("action_runtime_plan_contract"), dict) else {}
        if runtime_plan_contract:
            runtime_action_block = state.get("runtime_action")
            if isinstance(runtime_action_block, dict):
                runtime_action_block["source"] = "Action_Decision_JSON"
                runtime_action_block["action_runtime_plan_contract"] = runtime_plan_contract
                runtime_action_block["planned_action"] = runtime_plan_contract.get("planned_action")
                runtime_action_block["target_sequence_from_action_decision"] = runtime_plan_contract.get("target_sequence")
                runtime_action_block["target_sequences_from_action_decision"] = runtime_plan_contract.get("target_sequences")
    except Exception as exc:
        add_warning(state, block="action_runtime_plan_contract", message=f"Failed to attach runtime plan audit: {exc}")

    dark_path = save_dark_table_frame_json(
        state=state,
        cycle_dir=cycle_dir,
        table_id=table_id,
        frame_name=frame_name,
    )
    return dark_path, clear_path

def _extract_hero_cards(players_block: Optional[Dict[str, object]]) -> List[str]:
    if not players_block:
        return []
    seats = players_block.get("seats")
    if not isinstance(seats, dict):
        return []
    hero = seats.get("Player_seat1")
    if not isinstance(hero, dict):
        return []
    hero_cards = hero.get("hero_cards")
    if not isinstance(hero_cards, list):
        return []
    return [str(card) for card in hero_cards]


def _extract_board_cards_for_identity(table_structure_block: Optional[Dict[str, object]]) -> List[str]:
    if not table_structure_block:
        return []
    classes = table_structure_block.get("classes")
    if not isinstance(classes, dict):
        return []
    board = classes.get("Board")
    if not isinstance(board, dict):
        return []
    cards = board.get("cards")
    if not isinstance(cards, list):
        return []
    return [str(card) for card in cards if str(card).strip()]


def _extract_street(table_structure_block: Optional[Dict[str, object]]) -> Optional[str]:
    if not table_structure_block:
        return None
    classes = table_structure_block.get("classes")
    if not isinstance(classes, dict):
        return None
    board = classes.get("Board")
    if not isinstance(board, dict):
        return None
    street = board.get("street")
    return str(street) if street is not None else None


def _trigger_has_active_detect(trigger_ui_block: Optional[Dict[str, object]]) -> bool:
    if not trigger_ui_block:
        return False

    classes = trigger_ui_block.get("classes")
    if not isinstance(classes, dict):
        return False

    active_block = classes.get("Active")
    if not isinstance(active_block, dict):
        return False

    return bool(active_block.get("detect", False))



def _compact_click_points(click_points: object) -> List[Dict[str, object]]:
    """Keep click metadata compact for the main table-state JSON."""
    if not isinstance(click_points, list):
        return []

    compact: List[Dict[str, object]] = []
    for point in click_points:
        if not isinstance(point, dict):
            continue
        global_point = point.get("global_click_point") if isinstance(point.get("global_click_point"), dict) else {}
        compact.append(
            {
                "class_name": point.get("class_name"),
                "confidence": point.get("confidence"),
                "global_click_point": {
                    "x": global_point.get("x"),
                    "y": global_point.get("y"),
                },
                "inside_slot_bbox": bool(point.get("inside_slot_bbox", False)),
            }
        )
    return compact




def _compact_mouse_report(mouse: object) -> Dict[str, object]:
    if not isinstance(mouse, dict):
        return {}
    static = mouse.get("mouse_static") if isinstance(mouse.get("mouse_static"), dict) else {}
    movements = mouse.get("movements") if isinstance(mouse.get("movements"), list) else []
    return {
        "static_wait_status": static.get("status"),
        "waited_sec": static.get("waited_sec"),
        "click_count": mouse.get("click_count"),
        "movement_count": len(movements),
    }

def _compact_service_runtime_report(report: Dict[str, object]) -> Dict[str, object]:
    service = report.get("service_click", {}) if isinstance(report, dict) else {}
    death_card = report.get("death_card", {}) if isinstance(report, dict) else {}
    if not isinstance(service, dict):
        service = {}
    if not isinstance(death_card, dict):
        death_card = {}

    compact: Dict[str, object] = {
        "branch": "trigger_ui_service",
        "status": service.get("status", "skipped"),
        "target_class": service.get("target_class"),
        "target_sequence": list(service.get("target_sequence") or []),
        "decision_id": service.get("decision_id"),
        "dry_run": bool(service.get("dry_run", False)),
        "real_click_enabled": bool(service.get("real_click_enabled", False)),
        "guard_passed": bool(service.get("guard_passed", False)),
        "frame_finished": bool(service.get("frame_finished", False)),
        "skip_action_button_runtime": bool(service.get("skip_action_button_runtime", False)),
        "click_points": _compact_click_points(service.get("click_points")),
        "message": service.get("message"),
    }
    mouse_compact = _compact_mouse_report(service.get("mouse"))
    if mouse_compact:
        compact["mouse"] = mouse_compact

    if death_card.get("status") not in (None, "skipped") or death_card.get("hand_key") is not None:
        compact["death_card"] = {
            "status": death_card.get("status"),
            "hand_key": death_card.get("hand_key"),
            "matched": bool(death_card.get("matched", False)),
            "message": death_card.get("message"),
        }

    return compact



def _should_service_stop_poker_branch(service_report: Dict[str, object]) -> bool:
    """
    V7.0 ordered pipeline policy.

    True means Trigger_UI service branch has handled this frame and the heavy
    poker branch must not run for the same table/frame.

    Stop statuses:
    - dry_run: service action was selected in safe mode
    - clicked: service action performed a real click
    - confirmed: detect-only confirmation such as True_active_fold
    - explicit frame_finished / skip_action_button_runtime flags

    Non-stop statuses:
    - skipped: no actionable service branch
    - detected_only: passive service marker, e.g. Remove_Table only
    - blocked/error: no successful service action; keep normal diagnostics flow
    """
    service = service_report.get("service_click", {}) if isinstance(service_report, dict) else {}
    if not isinstance(service, dict):
        return False

    status = str(service.get("status") or "").strip().lower()
    if status in {"dry_run", "clicked", "confirmed"}:
        return True

    if bool(service.get("frame_finished")):
        return True

    if bool(service.get("skip_action_button_runtime")):
        return True

    return False


def _fallback_action_button_slot_roi_guard_for_compact_report(
    *,
    report: Dict[str, object],
    click: Dict[str, object],
    solver: Dict[str, object],
) -> Dict[str, object]:
    """Build a compact V2.7 exposure fallback when runtime click report has no ROI audit.

    V2.6 keeps the canonical schema_version. V2.7 only guarantees Dark_JSON
    visibility via audit_exposure_version. This fallback is diagnostic-only and
    never authorizes a click.
    """
    table_id = (
        click.get("table_id")
        or solver.get("table_id")
        or report.get("table_id")
        or "unknown_table"
    )
    click_points = click.get("click_points") if isinstance(click.get("click_points"), list) else []
    return {
        "schema_version": "action_button_slot_roi_runtime_audit_v2_6",
        "audit_exposure_version": "v2_7_dark_json_exposure",
        "ok": True,
        "status": "ACTION_BUTTON_SLOT_ROI_RUNTIME_AUDIT_EXPOSED_FALLBACK",
        "table_id": str(table_id),
        "detector_input_scope": "table_roi",
        "full_screen_search_blocked": True,
        "errors": [],
        "warnings": [
            "runtime_click_report_roi_guard_missing; compact Dark_JSON fallback audit inserted"
        ],
        "slot_bbox": None,
        "roi_size": None,
        "click_points_count": len(click_points),
        "per_button": [],
    }

def _compact_action_runtime_report(report: Dict[str, object]) -> Dict[str, object]:
    payload = report.get("payload", {}) if isinstance(report, dict) else {}
    solver = report.get("solver", {}) if isinstance(report, dict) else {}
    action_buttons = report.get("action_buttons", {}) if isinstance(report, dict) else {}
    click = report.get("click", {}) if isinstance(report, dict) else {}

    if not isinstance(payload, dict):
        payload = {}
    if not isinstance(solver, dict):
        solver = {}
    if not isinstance(action_buttons, dict):
        action_buttons = {}
    if not isinstance(click, dict):
        click = {}

    compact = {
        "branch": "action_button",
        "status": click.get("status") or solver.get("status") or payload.get("status") or "skipped",
        "payload_status": payload.get("status"),
        "solver_payload_path": payload.get("path"),
        "solver_status": solver.get("status"),
        "decision_id": click.get("decision_id") or solver.get("decision_id"),
        "solver_action": solver.get("action") or click.get("action"),
        "size_pct": solver.get("size_pct") if solver.get("size_pct") is not None else click.get("size_pct"),
        "solver_reason": solver.get("reason"),
        "total_pot_bb": solver.get("total_pot_bb"),
        "waited_sec": solver.get("waited_sec"),
        "action_button_status": action_buttons.get("status"),
        "action_button_detected_classes": list(action_buttons.get("detected_classes") or []),
        "target_sequence": list(click.get("target_sequence") or []),
        "dry_run": bool(click.get("dry_run", False)),
        "real_click_enabled": bool(click.get("real_click_enabled", False)),
        "guard_passed": bool(click.get("guard_passed", False)),
        "click_points": _compact_click_points(click.get("click_points")),
        "action_button_slot_roi_guard": (
            click.get("action_button_slot_roi_guard")
            if isinstance(click.get("action_button_slot_roi_guard"), dict)
            else _fallback_action_button_slot_roi_guard_for_compact_report(
                report=report if isinstance(report, dict) else {},
                click=click,
                solver=solver,
            )
        ),
        "controlled_live_click_gate": (
            click.get("controlled_live_click_gate")
            if isinstance(click.get("controlled_live_click_gate"), dict)
            else None
        ),
        "controlled_live_click_success": (
            click.get("controlled_live_click_success")
            if isinstance(click.get("controlled_live_click_success"), dict)
            else None
        ),
        "message": click.get("message") or payload.get("message"),
    }
    mouse_compact = _compact_mouse_report(click.get("mouse"))
    if mouse_compact:
        compact["mouse"] = mouse_compact
    return compact


def _build_runtime_action_block(
    *,
    service_report: Dict[str, object],
    action_report: Optional[Dict[str, object]],
) -> Dict[str, object]:
    service_block = _compact_service_runtime_report(service_report)
    action_block = _compact_action_runtime_report(action_report or {}) if action_report is not None else {
        "branch": "action_button",
        "status": "skipped",
        "message": "Action_Button runtime was skipped by Trigger_UI service branch.",
    }

    status = str(action_block.get("status") or service_block.get("status") or "skipped")
    if service_block.get("status") in {"clicked", "dry_run", "confirmed", "blocked", "error"} and action_block.get("status") == "skipped":
        status = str(service_block.get("status"))

    return {
        "status": status,
        "service": service_block,
        "action_button": action_block,
    }


def _build_live_capture_mode_block() -> Dict[str, object]:
    """Runtime-only Dark_JSON diagnostic for live no-click data capture mode."""
    return {
        "schema_version": "live_capture_mode_v1",
        "mode": "live_data_capture_no_click" if V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE else "live_runtime",
        "no_click_mode": bool(V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE),
        "action_real_click_enabled": bool(V11_REAL_MOUSE_CLICK_ENABLED),
        "action_dry_run": bool(V11_CLICK_DRY_RUN),
        "service_real_click_enabled": bool(V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED),
        "service_dry_run": bool(V11_TRIGGER_UI_SERVICE_DRY_RUN),
    }


def _run_v11_stage25_service_runtime_safely(
    *,
    state: Dict[str, object],
    table_roi: object,
    slot: TableSlot,
    trigger_result: object,
    cycle_dir: Path,
    identity: Optional[FrameIdentity] = None,
) -> Dict[str, object]:
    """
    Run the Trigger_UI service-click branch and return its in-memory report.

    No standalone _runtime JSON is written here; compact data is later embedded
    into the main table-state JSON.
    """
    if _run_v11_trigger_ui_service_runtime is None:
        message = V11_STAGE25_SERVICE_IMPORT_ERROR or "V1.1 Trigger_UI service runtime is not available."
        print(f"[V1.1 Stage2.5][{slot.table_id}] skipped: {message}")
        return {
            "service_click": {
                "status": "skipped",
                "frame_finished": False,
                "skip_action_button_runtime": False,
                "message": message,
            }
        }

    try:
        trigger_best_by_class = getattr(trigger_result, "best_by_class", None) if trigger_result is not None else None
        report = _run_v11_trigger_ui_service_runtime(
            full_state=state,
            table_roi_image=table_roi,
            slot=slot,
            trigger_best_by_class=trigger_best_by_class,
            cycle_dir=cycle_dir,
        )
        return report if isinstance(report, dict) else {}
    except Exception as exc:
        message = str(exc)
        print(f"[V1.1 Stage2.5][{slot.table_id}] service runtime error: {message}")
        return {
            "service_click": {
                "status": "error",
                "frame_finished": False,
                "skip_action_button_runtime": False,
                "message": message,
            }
        }


def _run_v11_stage2_runtime_safely(
    *,
    state: Dict[str, object],
    table_roi: object,
    slot: TableSlot,
    active_confirmed: bool,
    cycle_dir: Path,
    identity: Optional[FrameIdentity] = None,
) -> Dict[str, object]:
    """
    Run the safe V1.1 action-button chain and return its in-memory report.

    The solver payload JSON is still saved as the second allowed JSON file.
    No standalone _runtime click report is written.
    """
    if _run_v11_stage1_runtime is None:
        message = V11_STAGE2_IMPORT_ERROR or "V1.1 runtime is not available."
        print(f"[V1.1 Stage2][{slot.table_id}] skipped: {message}")
        return {
            "payload": {"status": "skipped", "path": None, "message": message},
            "solver": {"status": "skipped"},
            "action_buttons": {"status": "skipped", "detected_classes": []},
            "click": {"status": "skipped", "target_sequence": [], "message": message},
        }

    try:
        report = _run_v11_stage1_runtime(
            full_state=state,
            table_roi_image=table_roi,
            slot=slot,
            active_confirmed=active_confirmed,
            cycle_dir=cycle_dir,
        )
        return report if isinstance(report, dict) else {}
    except Exception as exc:
        message = str(exc)
        print(f"[V1.1 Stage2][{slot.table_id}] runtime error: {message}")
        return {
            "payload": {"status": "error", "path": None, "message": message},
            "solver": {"status": "skipped"},
            "action_buttons": {"status": "skipped", "detected_classes": []},
            "click": {"status": "error", "target_sequence": [], "message": message},
        }


def run_ui_display_analysis_cycle(
    image_by_table_id: Dict[str, Path],
    opened_table_ids: Set[str],
    hand_tracker: HandIdentityTracker,
    action_event_gate: Optional[ActionEventGate] = None,
    clear_json_state_machine: Optional[ClearJsonStateMachine] = None,
    table_action_transaction_gate: Optional[TableActionTransactionGate] = None,
    display_pass_id: str = DEFAULT_DISPLAY_PASS_ID,
    clear_previous_outputs_on_start: bool = True,
    cycle_id: str | None = None,
) -> List[Path]:
    """
    Запустить V1 runtime-анализ текущего display-pass.

    В одном pass у разных table_N могут быть разные hand_id/frame_name.
    display_pass_id используется только для debug-папок и не попадает в clean JSON.
    """
    started_at = now_perf_counter()

    if clear_previous_outputs_on_start:
        clear_previous_outputs()

    if cycle_id is None:
        cycle_id = make_cycle_id()
    cycle_dir = build_cycle_dir()
    ensure_dir(cycle_dir)

    if clear_json_state_machine is None:
        clear_json_state_machine = _DEFAULT_CLEAR_JSON_STATE_MACHINE
    if table_action_transaction_gate is None and V03_TABLE_ACTION_TRANSACTION_GATE_ENABLED:
        table_action_transaction_gate = _DEFAULT_TABLE_ACTION_TRANSACTION_GATE

    active_slots = [slot for slot in list_table_slots() if slot.table_id in image_by_table_id]
    if not active_slots:
        raise ValueError("Current display pass has no bound table images")

    screenshot = capture_primary_monitor()
    screenshot_size = {"w": screenshot.width, "h": screenshot.height}

    if SAVE_DEBUG_DESKTOP_CAPTURE:
        save_desktop_screenshot(cycle_dir, screenshot, display_pass_id=display_pass_id)

    saved_json_paths: List[Path] = []

    for slot in active_slots:
        if slot.table_id not in opened_table_ids:
            raise ValueError(f"Table window was not open for {slot.table_id}")

        validate_bbox_inside_screenshot(slot, screenshot_size)
        table_roi = crop_table_roi(slot=slot, screenshot=screenshot)

        if SAVE_DEBUG_TABLE_CROPS:
            save_table_crop(
                cycle_dir=cycle_dir,
                slot=slot,
                table_roi=table_roi,
                display_pass_id=display_pass_id,
            )

        trigger_result = None
        table_structure_result = None
        player_state_result = None
        digit_amounts_result = None
        card_detection_result = None
        table_status = "ok"

        if TRIGGER_UI_ENABLED:
            trigger_result = run_trigger_ui_pipeline(
                table_roi_image=table_roi,
                table_id=slot.table_id,
            )

        if V12_SAVE_ONLY_TRIGGERED_TABLES and trigger_result is not None:
            detected_classes = trigger_result.trigger_ui_block.get("detected_classes") if isinstance(trigger_result.trigger_ui_block, dict) else []
            detected_set = {str(class_name) for class_name in detected_classes}
            meaningful_detected_set = detected_set - {"Remove_Table"}
            if not meaningful_detected_set:
                # Real desktop mode: do not create JSON for idle slots.
                # Remove_Table is ignored here because it is a frequent passive service marker
                # and by itself does not mean that a poker hand/action frame exists.
                if action_event_gate is not None:
                    action_event_gate.observe_inactive(slot.table_id)
                if table_action_transaction_gate is not None:
                    table_action_transaction_gate.observe_inactive(slot.table_id)
                continue

        # V7.0.2 Stage 3 ordered pipeline:
        # Trigger_UI service branch is evaluated before heavy poker analysis.
        # If a service action/confirmation handles the frame, preserve Dark_JSON audit
        # and do not run table_structure/player/digit/card/Decision/Action branches.
        if trigger_result is not None:
            early_service_classes = []
            if isinstance(trigger_result.trigger_ui_block, dict):
                raw_service_classes = trigger_result.trigger_ui_block.get("detected_classes")
                if isinstance(raw_service_classes, list):
                    early_service_classes = [
                        str(class_name)
                        for class_name in raw_service_classes
                        if str(class_name).strip()
                    ]
            early_service_signature = "_".join(sorted(early_service_classes)) or "service"
            early_service_frame_name = f"{slot.table_id}_{cycle_id}_{early_service_signature}_service"

            early_service_state = build_table_frame_state(
                slot=slot,
                hand_id=f"{slot.table_id}_service",
                frame_name=early_service_frame_name,
                cycle_id=cycle_id,
                processing_time_ms=elapsed_ms(started_at),
                trigger_ui_block=trigger_result.trigger_ui_block,
                table_structure_block=None,
                players_block=None,
                table_status="service",
            )
            early_service_state["live_capture_mode"] = _build_live_capture_mode_block()

            for warning in trigger_result.warnings:
                add_warning(early_service_state, block="trigger_ui", message=warning)
            for error in trigger_result.errors:
                add_error(early_service_state, block="trigger_ui", message=error)

            early_service_report = _run_v11_stage25_service_runtime_safely(
                state=early_service_state,
                table_roi=table_roi,
                slot=slot,
                trigger_result=trigger_result,
                cycle_dir=cycle_dir,
                identity=None,
            )
            early_service_state["runtime_action"] = _build_runtime_action_block(
                service_report=early_service_report if isinstance(early_service_report, dict) else {},
                action_report=None,
            )

            if _should_service_stop_poker_branch(early_service_report if isinstance(early_service_report, dict) else {}):
                early_service_state["clear_json_contract"] = {
                    "status": "skipped",
                    "reason": "v70_service_first_branch_completed",
                    "publication_stage": "dark_json_only",
                    "pending_path": None,
                    "path": None,
                    "message": (
                        "V7.0 ordered pipeline: Trigger_UI service branch handled this frame before "
                        "heavy poker analysis. Clear_JSON_Pending, Decision_JSON, Action_Decision_JSON "
                        "and Action_Runtime_Plan_JSON were not built."
                    ),
                    "decision_json_contract": {
                        "enabled": bool(V05_DECISION_JSON_ENABLED),
                        "source": "Clear_JSON",
                        "path": None,
                        "dir": V05_DECISION_JSON_DIR_NAME,
                        "status": "not_built_service_first_stop",
                    },
                    "action_decision_contract": {
                        "enabled": bool(V06_ACTION_DECISION_ENABLED),
                        "source": "Decision_JSON",
                        "path": None,
                        "dir": V06_ACTION_DECISION_DIR_NAME,
                        "status": "not_built_service_first_stop",
                        "action_runtime_plan_contract": {
                            "enabled": bool(V07_ACTION_RUNTIME_PLAN_ENABLED),
                            "source": "Action_Decision_JSON",
                            "path": None,
                            "dir": V07_ACTION_RUNTIME_PLAN_DIR_NAME,
                            "status": "not_built_service_first_stop",
                        },
                    },
                }
                early_service_dark_path = save_dark_table_frame_json(
                    state=early_service_state,
                    cycle_dir=cycle_dir,
                    table_id=slot.table_id,
                    frame_name=str(early_service_state.get("frame_name") or f"{slot.table_id}_{cycle_id}_service"),
                )
                saved_json_paths.append(early_service_dark_path)
                if action_event_gate is not None:
                    action_event_gate.observe_inactive(slot.table_id)
                if table_action_transaction_gate is not None:
                    table_action_transaction_gate.observe_inactive(slot.table_id)
                continue

        early_action_transaction_decision = None
        early_lifecycle_gate_audit = None
        early_lifecycle_active = (
            trigger_result is not None
            and trigger_result.table_status_hint == TABLE_STATUS_READY_FOR_STRUCTURE_PIPELINE
        )
        if early_lifecycle_active and table_action_transaction_gate is not None:
            early_action_transaction_decision = table_action_transaction_gate.begin_analysis_cycle(
                table_id=slot.table_id,
                action_event_id=None,
                action_signature=None,
            )
            early_lifecycle_gate_audit = _build_table_lifecycle_gate_audit(
                early_action_transaction_decision,
                stage="before_heavy_analysis",
            )
            if not early_action_transaction_decision.should_process:
                print(
                    f"[TableActionTransactionGate][{slot.table_id}] heavy analysis skipped by early lifecycle gate: "
                    f"reason={early_action_transaction_decision.reason}, "
                    f"locked_by={early_action_transaction_decision.locked_by_transaction_id}"
                )
                continue

        if TABLE_STRUCTURE_ENABLED:
            structure_allowed = True
            skip_reason = None

            if TABLE_STRUCTURE_REQUIRE_ACTIVE:
                structure_allowed = (
                    trigger_result is not None
                    and trigger_result.table_status_hint == TABLE_STATUS_READY_FOR_STRUCTURE_PIPELINE
                )
                if not structure_allowed:
                    skip_reason = (
                        f"{slot.table_id}: Table_Seat_BoardPot_Detector skipped because "
                        "Trigger_UI strong Active was not detected."
                    )

            if structure_allowed:
                table_structure_result = run_table_structure_pipeline(
                    table_roi_image=table_roi,
                    table_id=slot.table_id,
                )
            else:
                table_structure_result = build_skipped_table_structure_block(
                    reason=skip_reason or "Table structure stage skipped by runtime policy."
                )

        if PLAYER_STATE_ENABLED:
            player_state_allowed = True
            skip_reason = None

            if PLAYER_STATE_REQUIRE_TABLE_STRUCTURE:
                table_structure_block = (
                    table_structure_result.table_structure_block
                    if table_structure_result else {}
                )
                player_state_allowed = (
                    table_structure_result is not None
                    and table_structure_block.get("next_stage_hint") == "players_pipeline_ready"
                    and bool(table_structure_result.player_seat_regions)
                )
                if not player_state_allowed:
                    skip_reason = (
                        f"{slot.table_id}: Player_State_Detector skipped because "
                        "table_structure did not provide players_pipeline_ready with runtime Player_seat regions."
                    )

            if player_state_allowed and table_structure_result is not None:
                player_state_result = run_player_state_pipeline(
                    table_roi_image=table_roi,
                    table_id=slot.table_id,
                    hand_id=display_pass_id,
                    cycle_dir=cycle_dir,
                    detected_player_seats=table_structure_result.detected_player_seats,
                    player_seat_regions=table_structure_result.player_seat_regions,
                )
            else:
                player_state_result = build_skipped_player_state_block(
                    reason=skip_reason or "Player state stage skipped by runtime policy."
                )

        if DIGIT_AMOUNTS_ENABLED:
            digit_allowed = True
            skip_reason = None

            if DIGIT_AMOUNTS_REQUIRE_PLAYERS:
                digit_allowed = (
                    table_structure_result is not None
                    and player_state_result is not None
                    and player_state_result.players_block.get("next_stage_hint") == "digit_amounts_pipeline_ready"
                )
                if not digit_allowed:
                    skip_reason = (
                        f"{slot.table_id}: Digit_Detector skipped because players stage did not provide "
                        "digit_amounts_pipeline_ready."
                    )

            if digit_allowed and table_structure_result is not None and player_state_result is not None:
                digit_amounts_result = run_digit_amounts_pipeline(
                    table_roi_image=table_roi,
                    table_id=slot.table_id,
                    hand_id=display_pass_id,
                    cycle_dir=cycle_dir,
                    table_structure_block=table_structure_result.table_structure_block,
                    players_block=player_state_result.players_block,
                    total_pot_region=table_structure_result.total_pot_region,
                    player_amount_regions=player_state_result.amount_regions,
                )
            elif table_structure_result is not None and player_state_result is not None:
                from pipeline.digit_amounts_pipeline import build_skipped_digit_amounts_result
                digit_amounts_result = build_skipped_digit_amounts_result(
                    table_structure_block=table_structure_result.table_structure_block,
                    players_block=player_state_result.players_block,
                    reason=skip_reason or "Digit amounts stage skipped by runtime policy.",
                )

        if CARD_DETECTION_ENABLED:
            card_allowed = True
            skip_reason = None

            if CARD_DETECTION_REQUIRE_PLAYERS:
                base_players_block = (
                    digit_amounts_result.players_block
                    if digit_amounts_result is not None
                    else (player_state_result.players_block if player_state_result is not None else {})
                )
                card_allowed = (
                    table_structure_result is not None
                    and player_state_result is not None
                    and bool(base_players_block.get("seats"))
                )
                if not card_allowed:
                    skip_reason = (
                        f"{slot.table_id}: Card_Detector skipped because players stage did not provide "
                        "a usable players block."
                    )

            if card_allowed and table_structure_result is not None and player_state_result is not None:
                source_table_block = (
                    digit_amounts_result.table_structure_block
                    if digit_amounts_result is not None
                    else table_structure_result.table_structure_block
                )
                source_players_block = (
                    digit_amounts_result.players_block
                    if digit_amounts_result is not None
                    else player_state_result.players_block
                )
                card_detection_result = run_card_detection_pipeline(
                    table_roi_image=table_roi,
                    table_id=slot.table_id,
                    hand_id=display_pass_id,
                    cycle_dir=cycle_dir,
                    table_structure_block=source_table_block,
                    players_block=source_players_block,
                    board_region=table_structure_result.board_region,
                    player_seat_regions=table_structure_result.player_seat_regions,
                )
            elif table_structure_result is not None and player_state_result is not None:
                from pipeline.card_detection_pipeline import build_skipped_card_detection_result
                source_table_block = (
                    digit_amounts_result.table_structure_block
                    if digit_amounts_result is not None
                    else table_structure_result.table_structure_block
                )
                source_players_block = (
                    digit_amounts_result.players_block
                    if digit_amounts_result is not None
                    else player_state_result.players_block
                )
                card_detection_result = build_skipped_card_detection_result(
                    table_structure_block=source_table_block,
                    players_block=source_players_block,
                    reason=skip_reason or "Card detection stage skipped by runtime policy.",
                )

        if card_detection_result and card_detection_result.status == "error":
            table_status = "error"
        elif digit_amounts_result and digit_amounts_result.status == "error":
            table_status = "error"
        elif player_state_result and player_state_result.players_block.get("status") == "error":
            table_status = "error"
        elif table_structure_result and table_structure_result.table_structure_block.get("status") == "error":
            table_status = "error"
        elif card_detection_result and card_detection_result.status == "warning":
            table_status = "warning"
        elif digit_amounts_result and digit_amounts_result.status == "warning":
            table_status = "warning"
        elif player_state_result and player_state_result.players_block.get("status") == "warning":
            table_status = "warning"
        elif table_structure_result and table_structure_result.table_structure_block.get("status") == "warning":
            table_status = "warning"
        else:
            table_status = "ok"

        final_table_structure_block = (
            card_detection_result.table_structure_block
            if card_detection_result else (
                digit_amounts_result.table_structure_block
                if digit_amounts_result else (
                    table_structure_result.table_structure_block
                    if table_structure_result else None
                )
            )
        )
        final_players_block = (
            card_detection_result.players_block
            if card_detection_result else (
                digit_amounts_result.players_block
                if digit_amounts_result else (
                    player_state_result.players_block
                    if player_state_result else None
                )
            )
        )

        active_confirmed = (
            trigger_result is not None
            and trigger_result.table_status_hint == TABLE_STATUS_READY_FOR_STRUCTURE_PIPELINE
        )
        hero_cards_for_identity = _extract_hero_cards(final_players_block)
        street_for_identity = _extract_street(final_table_structure_block)
        board_cards_for_identity = _extract_board_cards_for_identity(final_table_structure_block)

        action_event_decision: Optional[ActionEventDecision] = None
        action_transaction_decision = early_action_transaction_decision
        if action_event_gate is not None:
            if active_confirmed:
                action_event_decision = action_event_gate.evaluate_active(
                    table_id=slot.table_id,
                    hero_cards=hero_cards_for_identity,
                    street=street_for_identity,
                    table_structure_block=final_table_structure_block,
                    players_block=final_players_block,
                )
                if not action_event_decision.should_process:
                    # V0.8 live hotfix: duplicate Active/action events must not block
                    # table analysis or Dark_JSON publication. They only suppress the
                    # action/click branch later in this cycle. This preserves street
                    # continuity, so flop -> turn -> river can still be observed.
                    print(
                        f"[ActionEventGate][{slot.table_id}] duplicate Active action suppressed, "
                        f"analysis preserved: reason={action_event_decision.reason}, "
                        f"duplicate_of={action_event_decision.duplicate_of}"
                    )
            else:
                action_event_gate.observe_inactive(slot.table_id)
                if table_action_transaction_gate is not None:
                    table_action_transaction_gate.observe_inactive(slot.table_id)

        identity = hand_tracker.resolve(
            table_id=slot.table_id,
            active_confirmed=active_confirmed,
            hero_cards=hero_cards_for_identity,
            street=street_for_identity,
            board_cards=board_cards_for_identity,
        )

        total_ms = elapsed_ms(started_at)
        state = build_table_frame_state(
            slot=slot,
            hand_id=identity.hand_id,
            frame_name=identity.frame_name,
            cycle_id=cycle_id,
            processing_time_ms=total_ms,
            trigger_ui_block=(trigger_result.trigger_ui_block if trigger_result else None),
            table_structure_block=final_table_structure_block,
            players_block=final_players_block,
            table_status=table_status,
        )

        state["live_capture_mode"] = _build_live_capture_mode_block()

        if early_lifecycle_gate_audit is not None:
            state["table_lifecycle_gate"] = early_lifecycle_gate_audit

        if action_event_decision is not None:
            state["runtime_event"] = action_event_decision.to_json()
            state["table"]["action_event_id"] = action_event_decision.action_event_id

        if action_transaction_decision is not None:
            state["action_transaction"] = action_transaction_decision.to_json()

        if identity.warning:
            add_warning(state, block="hand_identity", message=identity.warning)

        if trigger_result:
            for warning in trigger_result.warnings:
                add_warning(state, block="trigger_ui", message=warning)
            for error in trigger_result.errors:
                add_error(state, block="trigger_ui", message=error)

        if table_structure_result:
            for warning in table_structure_result.warnings:
                add_warning(state, block="table_structure", message=warning)
            for error in table_structure_result.errors:
                add_error(state, block="table_structure", message=error)

        if player_state_result:
            for warning in player_state_result.warnings:
                add_warning(state, block="players", message=warning)
            for error in player_state_result.errors:
                add_error(state, block="players", message=error)

        if digit_amounts_result:
            for warning in digit_amounts_result.warnings:
                add_warning(state, block="digit_amounts", message=warning)
            for error in digit_amounts_result.errors:
                add_error(state, block="digit_amounts", message=error)

        if card_detection_result:
            for warning in card_detection_result.warnings:
                add_warning(state, block="card_detection", message=warning)
            for error in card_detection_result.errors:
                add_error(state, block="card_detection", message=error)

        service_report = _run_v11_stage25_service_runtime_safely(
            state=state,
            table_roi=table_roi,
            slot=slot,
            trigger_result=trigger_result,
            cycle_dir=cycle_dir,
            identity=identity,
        )
        service_click = service_report.get("service_click", {}) if isinstance(service_report, dict) else {}
        service_frame_finished = bool(service_click.get("frame_finished"))
        service_skip_action_runtime = bool(service_click.get("skip_action_button_runtime"))

        action_report: Optional[Dict[str, object]] = None
        action_runtime_candidate = (
            active_confirmed
            and action_event_decision is not None
            and bool(action_event_decision.should_process)
            and bool(action_event_decision.action_event_id)
        )
        action_runtime_allowed = (
            action_runtime_candidate
            and not service_frame_finished
            and not service_skip_action_runtime
        )

        # V2.0: the table transaction lifecycle starts before heavy analysis and
        # enters the action/click phase only when the action runtime is actually
        # going to run. This prevents repeated heavy analysis while an unfinished
        # per-table lifecycle is already open.
        if action_runtime_allowed and table_action_transaction_gate is not None:
            action_transaction_decision = table_action_transaction_gate.begin_action_cycle(
                table_id=slot.table_id,
                action_event_id=(action_event_decision.action_event_id if action_event_decision else None),
                action_signature=(action_event_decision.action_signature if action_event_decision else None),
            )
            state["action_transaction"] = action_transaction_decision.to_json()
            if isinstance(state.get("table_lifecycle_gate"), dict):
                state["table_lifecycle_gate"]["action_cycle"] = _build_table_lifecycle_gate_audit(
                    action_transaction_decision,
                    stage="before_action_runtime",
                )
            if not action_transaction_decision.should_process:
                print(
                    f"[TableActionTransactionGate][{slot.table_id}] action runtime suppressed, "
                    f"analysis preserved: reason={action_transaction_decision.reason}, "
                    f"locked_by={action_transaction_decision.locked_by_transaction_id}"
                )
                action_runtime_allowed = False

        if action_runtime_allowed:
            action_report = _run_v11_stage2_runtime_safely(
                state=state,
                table_roi=table_roi,
                slot=slot,
                active_confirmed=active_confirmed,
                cycle_dir=cycle_dir,
                identity=identity,
            )
        else:
            if not action_runtime_candidate:
                print(
                    f"[V1.1 Stage2][{slot.table_id}] skipped: "
                    "solver payload/action runtime requires a new strong Active action_event."
                )
            elif service_frame_finished or service_skip_action_runtime:
                print(
                    f"[V1.1 Stage2][{slot.table_id}] skipped by service runtime: "
                    f"frame_finished={service_frame_finished}, "
                    f"skip_action_runtime={service_skip_action_runtime}"
                )
            else:
                print(
                    f"[V1.1 Stage2][{slot.table_id}] skipped by late transaction gate; "
                    "table analysis was preserved."
                )

        state["runtime_action"] = _build_runtime_action_block(
            service_report=service_report if isinstance(service_report, dict) else {},
            action_report=action_report,
        )

        clear_json_save_allowed = True
        click_result_for_clear = None
        transaction_runtime_report: Optional[Dict[str, object]] = None
        if active_confirmed and table_action_transaction_gate is not None:
            if action_report is not None and action_transaction_decision is not None and action_transaction_decision.should_process:
                transaction_runtime_report = table_action_transaction_gate.finalize_from_runtime(
                    table_id=slot.table_id,
                    runtime_action=state["runtime_action"] if isinstance(state.get("runtime_action"), dict) else {},
                )
                state["action_transaction_runtime"] = transaction_runtime_report
                clear_json_save_allowed = bool(transaction_runtime_report.get("click_completed"))
                click_result = transaction_runtime_report.get("click_result")
                if isinstance(click_result, dict) and clear_json_save_allowed:
                    click_result_for_clear = click_result
            else:
                clear_json_save_allowed = False
                release_report = None
                if action_transaction_decision is not None and action_transaction_decision.should_process:
                    release_report = table_action_transaction_gate.abort_analysis_cycle(
                        table_id=slot.table_id,
                        reason="no_completed_action_runtime_for_active_lifecycle",
                        message="Early table lifecycle was released because no action runtime completed for this Active frame.",
                    )
                state["action_transaction_runtime"] = {
                    "status": "skipped",
                    "reason": "no_new_action_runtime_cycle_for_this_active_frame",
                    "click_completed": False,
                    "message": "Table analysis/Dark_JSON is preserved, but Final Clear_JSON requires a completed action runtime cycle.",
                    "early_lifecycle_release": release_report,
                }

        duplicate_active_hard_stop_before_pending = (
            active_confirmed
            and action_event_decision is not None
            and not bool(action_event_decision.should_process)
            and str(action_event_decision.reason) == "duplicate_active_frame_blocked"
        )
        if duplicate_active_hard_stop_before_pending:
            state["duplicate_active_hard_stop"] = {
                "schema_version": "duplicate_active_hard_stop_v4_0",
                "status": "DUPLICATE_ACTIVE_HARD_STOP_BEFORE_PENDING_DECISION",
                "reason": "duplicate_active_frame_blocked",
                "duplicate_of": action_event_decision.duplicate_of,
                "action_signature": action_event_decision.action_signature,
                "message": (
                    "Duplicate Active frame preserved as Dark_JSON only. "
                    "Clear_JSON_Pending, Decision_JSON, Action_Decision_JSON and "
                    "Action_Runtime_Plan_JSON are intentionally suppressed."
                ),
            }

        dark_json_path, clear_json_path = save_dark_and_clear_table_frame_json(
            state=state,
            cycle_dir=cycle_dir,
            table_id=slot.table_id,
            hand_id=identity.hand_id,
            frame_name=identity.frame_name,
            active_confirmed=active_confirmed,
            clear_json_state_machine=clear_json_state_machine,
            clear_json_save_allowed=clear_json_save_allowed,
            clear_json_build_allowed=not duplicate_active_hard_stop_before_pending,
            clear_json_build_block_reason=(
                "duplicate_active_frame_blocked"
                if duplicate_active_hard_stop_before_pending
                else None
            ),
            click_result=click_result_for_clear,
        )

        failed_finalization_release = None
        if active_confirmed and table_action_transaction_gate is not None:
            failed_finalization_release = _release_failed_active_finalization_if_needed(
                state=state,
                table_action_transaction_gate=table_action_transaction_gate,
                table_id=slot.table_id,
                action_transaction_decision=action_transaction_decision,
                transaction_runtime_report=transaction_runtime_report,
                clear_json_path=clear_json_path,
            )
            if isinstance(failed_finalization_release, dict):
                # The release audit is produced after Clear_JSON contract evaluation;
                # rewrite the same Dark_JSON file so the saved audit reflects the
                # final lifecycle release state.
                dark_json_path = save_dark_table_frame_json(
                    state=state,
                    cycle_dir=cycle_dir,
                    table_id=slot.table_id,
                    frame_name=identity.frame_name,
                )
            else:
                table_action_transaction_gate.mark_clear_json_saved(
                    table_id=slot.table_id,
                    clear_json_path=str(clear_json_path) if clear_json_path else None,
                )
                if (
                    clear_json_path
                    and isinstance(transaction_runtime_report, dict)
                    and bool(transaction_runtime_report.get("click_completed"))
                ):
                    try:
                        completed_state = json.loads(Path(str(clear_json_path)).read_text(encoding="utf-8"))
                        if not isinstance(completed_state, dict):
                            raise ValueError("Final Clear_JSON content is not an object.")
                        completed_json_path = save_completed_json_table_frame_json(
                            completed_state=completed_state,
                            cycle_dir=cycle_dir,
                            table_id=slot.table_id,
                        )
                        state["completed_json_contract"] = {
                            "status": "saved",
                            "path": str(completed_json_path),
                            "dir": V10_JSON_COMPLETE_DIR_NAME,
                            "source_clear_json_path": str(clear_json_path),
                            "reason": "final_clear_json_and_action_runtime_completed",
                        }
                    except Exception as exc:
                        state["completed_json_contract"] = {
                            "status": "error",
                            "path": None,
                            "dir": V10_JSON_COMPLETE_DIR_NAME,
                            "source_clear_json_path": str(clear_json_path),
                            "reason": "completed_json_save_error",
                            "message": str(exc),
                        }
                        add_warning(state, block="completed_json_contract", message=str(exc))
                    dark_json_path = save_dark_table_frame_json(
                        state=state,
                        cycle_dir=cycle_dir,
                        table_id=slot.table_id,
                        frame_name=identity.frame_name,
                    )

        # Compatibility: current replay harness reads the returned path as the full technical state.
        # The upgraded harness will also verify the linked Clear_JSON path from clear_json_contract.
        saved_json_paths.append(dark_json_path)


    return saved_json_paths
