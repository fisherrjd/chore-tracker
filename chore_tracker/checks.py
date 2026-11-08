"""In-memory, shared daily checklist state.

Completion is tracked per day-index, so checked-off tasks are shared across
everyone using the app, and keyed by room (not person) so progress follows the
room. It resets automatically when the day changes. State lives only in this process — a restart
clears it, which is exactly the "no longer than a day" persistence the
checklist needs.
"""
from threading import Lock

_lock = Lock()
# day_index -> room name -> set of completed task names
_state: dict[int, dict[str, set[str]]] = {}


def get_done(day_index: int, room: str) -> set[str]:
    """Return the set of tasks `room` has checked off for the given day."""
    with _lock:
        return set(_state.get(day_index, {}).get(room, set()))


def set_done(day_index: int, room: str, tasks: list[str]) -> None:
    """Replace `room`'s completed tasks for the given day.

    Other days are dropped so state never lingers past the current one.
    """
    with _lock:
        for idx in [i for i in _state if i != day_index]:
            del _state[idx]
        _state.setdefault(day_index, {})[room] = set(tasks)
