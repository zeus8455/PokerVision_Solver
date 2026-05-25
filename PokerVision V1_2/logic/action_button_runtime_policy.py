"""
logic/action_button_runtime_policy.py
PokerVision V1.1.1 вЂ” controlled Action_Button runtime policy.

Purpose:
- Keep real-click button semantics deterministic and separated from YOLO output.
- Convert an Action_Decision / Action_Runtime_Plan action into allowed button sequences.
- Restrict first controlled real-click tests to low-risk simple actions:
  fold / check / call / check_fold.
- Explicitly block bet/raise real-click sizing branch for the first real-click stage.
- V1.10.1 allows supported bet/raise size sequences for dry-run plan diagnostics only.

This module does not run YOLO and does not click the mouse.
It only decides whether a detected Action_Button sequence is allowed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set


CANONICAL_BUTTONS: List[str] = [
    "FOLD",
    "33%",
    "50%",
    "70%",
    "98%",
    "Call",
    "Check/fold",
    "Check",
    "Bet/Raise",
]

_BUTTON_ALIASES: Dict[str, str] = {
    "fold": "FOLD",
    "Fold": "FOLD",
    "FOLD": "FOLD",
    "call": "Call",
    "CALL": "Call",
    "Call": "Call",
    "check": "Check",
    "CHECK": "Check",
    "Check": "Check",
    "check/fold": "Check/fold",
    "Check/Fold": "Check/fold",
    "CHECK/FOLD": "Check/fold",
    "check_fold": "Check/fold",
    "CHECK_FOLD": "Check/fold",
    "Check_fold": "Check/fold",
    "bet/raise": "Bet/Raise",
    "Bet/raise": "Bet/Raise",
    "BET/RAISE": "Bet/Raise",
    "bet_raise": "Bet/Raise",
    "raise": "Bet/Raise",
    "Raise": "Bet/Raise",
    "33": "33%",
    "33%": "33%",
    "33_pct": "33%",
    "50": "50%",
    "50%": "50%",
    "50_pct": "50%",
    "70": "70%",
    "70%": "70%",
    "70_pct": "70%",
    "98": "98%",
    "98%": "98%",
    "98_pct": "98%",
}

_ACTION_ALIASES: Dict[str, str] = {
    "fold": "fold",
    "call": "call",
    "check": "check",
    "checkfold": "check_fold",
    "check_fold": "check_fold",
    "check/fold": "check_fold",
    "bet": "bet_raise",
    "raise": "bet_raise",
    "bet_raise": "bet_raise",
    "bet/raise": "bet_raise",
}

LOW_RISK_REAL_CLICK_ACTIONS: Set[str] = {"fold", "check", "call", "check_fold"}
BLOCKED_FIRST_REAL_CLICK_ACTIONS: Set[str] = {"bet_raise"}


@dataclass(frozen=True)
class ActionButtonRuntimePolicyResult:
    ok: bool
    action: str
    selected_sequence: List[str] = field(default_factory=list)
    target_sequences: List[List[str]] = field(default_factory=list)
    blocked_reason: Optional[str] = None
    detected_classes: List[str] = field(default_factory=list)
    missing_classes: List[str] = field(default_factory=list)
    real_click_allowed: bool = False
    policy_version: str = "v1.1.1_action_button_runtime_policy"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy_version": self.policy_version,
            "ok": self.ok,
            "action": self.action,
            "selected_sequence": list(self.selected_sequence),
            "target_sequences": [list(seq) for seq in self.target_sequences],
            "blocked_reason": self.blocked_reason,
            "detected_classes": list(self.detected_classes),
            "missing_classes": list(self.missing_classes),
            "real_click_allowed": self.real_click_allowed,
        }


def canonical_button_class(value: Any) -> str:
    text = str(value or "").strip()
    return _BUTTON_ALIASES.get(text, text)


def normalize_action(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_")
    return _ACTION_ALIASES.get(text, text or "fold")


def normalize_detected_classes(values: Optional[Iterable[Any]]) -> List[str]:
    if values is None:
        return []
    result: List[str] = []
    for item in values:
        canonical = canonical_button_class(item)
        if canonical and canonical not in result:
            result.append(canonical)
    return result


_VALID_SIZE_PCTS: Set[int] = {33, 50, 70, 98}


def _normalize_size_pct_from_policy(size_policy: Any) -> Optional[int]:
    """Return supported pct size from solver/runtime size_policy.

    Accepts either:
    - {"kind": "pct", "value": 98}
    - {"type": "pct", "value": 98}
    - direct values like 98 / "98" / "98%"
    """
    if size_policy is None or size_policy == "":
        return None

    raw_value: Any = None
    if isinstance(size_policy, dict):
        kind = str(size_policy.get("kind") or size_policy.get("type") or "").strip().lower()
        if kind and kind != "pct":
            return None
        raw_value = size_policy.get("value")
    else:
        raw_value = size_policy

    if raw_value is None or raw_value == "":
        return None

    try:
        if isinstance(raw_value, str):
            raw_value = raw_value.strip().replace("%", "")
        value = int(float(raw_value))
    except Exception:
        return None

    if value not in _VALID_SIZE_PCTS:
        return None
    return value


def build_controlled_target_sequences(action: Any, size_policy: Any = None) -> List[List[str]]:
    """Return ordered button alternatives for the first controlled real-click stage.

    V1.1.1 intentionally blocks bet/raise real-click sizing. The raise branch will
    be added later as a separate stage because it requires multi-step click safety.
    """
    normalized = normalize_action(action)

    if normalized == "fold":
        return [["FOLD"], ["Check/fold"]]
    if normalized == "check":
        return [["Check"], ["Check/fold"]]
    if normalized == "call":
        return [["Call"]]
    if normalized == "check_fold":
        return [["Check"], ["Check/fold"], ["FOLD"]]
    if normalized == "bet_raise":
        size_pct = _normalize_size_pct_from_policy(size_policy)
        if size_pct is None:
            # Deliberately keep unsupported/no-size raises out of runtime plans.
            return []
        # V1.10.1: allow a sizing sequence to be built for dry-run diagnostics only.
        # Real-click execution for bet/raise remains blocked by resolve_action_button_runtime_policy.
        return [[f"{size_pct}%", "Bet/Raise"]]
    return []


def _first_available_sequence(
    sequences: Sequence[Sequence[str]],
    detected_classes: Sequence[str],
) -> tuple[List[str], List[str]]:
    detected = set(detected_classes)
    last_missing: List[str] = []
    for seq in sequences:
        canonical_seq = [canonical_button_class(item) for item in seq if str(item or "").strip()]
        missing = [item for item in canonical_seq if item not in detected]
        if not missing:
            return canonical_seq, []
        last_missing = missing
    return [], last_missing


def resolve_action_button_runtime_policy(
    *,
    action: Any,
    size_policy: Any = None,
    detected_classes: Optional[Iterable[Any]] = None,
    real_click_enabled: bool = False,
) -> Dict[str, Any]:
    """Resolve whether an action can be executed by Action_Button_Detector.

    If detected_classes is provided, the selected sequence must be present.
    If detected_classes is empty/None, the function returns the primary planned
    sequence for plan-building/dry-run diagnostics without claiming button detection.
    """
    normalized_action = normalize_action(action)
    detected = normalize_detected_classes(detected_classes)
    sequences = build_controlled_target_sequences(normalized_action, size_policy)

    if normalized_action in BLOCKED_FIRST_REAL_CLICK_ACTIONS:
        # V1.10.1: dry-run plan building may publish a non-click executable sequence
        # for supported bet/raise sizes. Any detector-backed or real-click attempt is
        # still blocked until a dedicated real-click safety stage exists.
        if not bool(real_click_enabled) and not detected and sequences:
            return ActionButtonRuntimePolicyResult(
                ok=True,
                action=normalized_action,
                selected_sequence=list(sequences[0]),
                target_sequences=[list(seq) for seq in sequences],
                detected_classes=[],
                real_click_allowed=False,
            ).to_dict()
        return ActionButtonRuntimePolicyResult(
            ok=False,
            action=normalized_action,
            target_sequences=sequences,
            blocked_reason="bet_raise_branch_disabled_for_v1_1_first_real_click_stage",
            detected_classes=detected,
            real_click_allowed=False,
        ).to_dict()

    if normalized_action not in LOW_RISK_REAL_CLICK_ACTIONS:
        return ActionButtonRuntimePolicyResult(
            ok=False,
            action=normalized_action,
            target_sequences=sequences,
            blocked_reason="unsupported_action_for_controlled_action_button_runtime",
            detected_classes=detected,
            real_click_allowed=False,
        ).to_dict()

    if not sequences:
        return ActionButtonRuntimePolicyResult(
            ok=False,
            action=normalized_action,
            target_sequences=[],
            blocked_reason="no_target_sequence_for_action",
            detected_classes=detected,
            real_click_allowed=False,
        ).to_dict()

    if detected:
        selected, missing = _first_available_sequence(sequences, detected)
        if not selected:
            return ActionButtonRuntimePolicyResult(
                ok=False,
                action=normalized_action,
                target_sequences=[list(seq) for seq in sequences],
                blocked_reason="required_action_button_sequence_not_detected",
                detected_classes=detected,
                missing_classes=missing,
                real_click_allowed=False,
            ).to_dict()
        return ActionButtonRuntimePolicyResult(
            ok=True,
            action=normalized_action,
            selected_sequence=selected,
            target_sequences=[list(seq) for seq in sequences],
            detected_classes=detected,
            real_click_allowed=bool(real_click_enabled),
        ).to_dict()

    # Plan/dry-run diagnostics: no detector result supplied yet.
    return ActionButtonRuntimePolicyResult(
        ok=True,
        action=normalized_action,
        selected_sequence=list(sequences[0]),
        target_sequences=[list(seq) for seq in sequences],
        detected_classes=[],
        real_click_allowed=False,
    ).to_dict()
