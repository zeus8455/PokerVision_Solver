from __future__ import annotations

from functools import wraps
from time import perf_counter
from typing import Any, Callable, Dict

ENABLE_PERF = False
PERF_STATS: Dict[str, float] = {}
CALL_COUNTS: Dict[str, int] = {}


def is_perf_enabled() -> bool:
    return bool(ENABLE_PERF)


def enable_perf(*, reset: bool = True) -> None:
    global ENABLE_PERF
    ENABLE_PERF = True
    if reset:
        reset_perf()


def disable_perf() -> None:
    global ENABLE_PERF
    ENABLE_PERF = False


def reset_perf() -> None:
    PERF_STATS.clear()
    CALL_COUNTS.clear()


def add_time(name: str, value: float) -> None:
    PERF_STATS[name] = PERF_STATS.get(name, 0.0) + float(value)


def count_call(name: str, increment: int = 1) -> None:
    if ENABLE_PERF:
        CALL_COUNTS[name] = CALL_COUNTS.get(name, 0) + int(increment)


class PerfScope:
    def __init__(self, name: str, sink: Dict[str, float] | None = None):
        self.name = name
        self.sink = PERF_STATS if sink is None else sink
        self.t0 = 0.0
        self.enabled = False

    def __enter__(self):
        self.enabled = ENABLE_PERF
        if self.enabled:
            self.t0 = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.enabled:
            self.sink[self.name] = self.sink.get(self.name, 0.0) + (perf_counter() - self.t0)


def profile_function(metric_name: str, *, count_name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    counter = count_name or f"{metric_name}.calls"
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not ENABLE_PERF:
                return func(*args, **kwargs)
            count_call(counter)
            t0 = perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                add_time(metric_name, perf_counter() - t0)
        return wrapper
    return decorator


def snapshot_perf() -> dict[str, dict[str, float] | dict[str, int]]:
    return {"timings_seconds": dict(PERF_STATS), "call_counts": dict(CALL_COUNTS)}
