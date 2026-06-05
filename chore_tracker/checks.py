"""In-memory, shared daily checklist state.

Completion is tracked per day-index, so checked-off tasks are shared across
everyone using the app but reset automatically when the day (and thus the
chore assignment) changes. State lives only in this process — a restart
clears it, which is exactly the "no longer than a day" persistence the
checklist needs.
"""
from threading import Lock

_lock = Lock()
# day_index -> member name -> set of completed task names
_state: dict[int, dict[str, set[str]]] = {}


def get_done(day_index: int, member: str) -> set[str]:
    """Return the set of tasks `member` has checked off for the given day."""
    with _lock:
        return set(_state.get(day_index, {}).get(member, set()))


def set_done(day_index: int, member: str, tasks: list[str]) -> None:
    """Replace `member`'s completed tasks for the given day.

    Other days are dropped so state never lingers past the current one.
    """
    with _lock:
        for idx in [i for i in _state if i != day_index]:
            del _state[idx]
        _state.setdefault(day_index, {})[member] = set(tasks)
