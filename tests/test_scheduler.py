"""Rotation logic — the heart of the app. These pin the fairness guarantees."""
from datetime import date

from chore_tracker.scheduler import get_assignment, get_day_index, get_schedule


def test_get_day_index_counts_days_from_start():
    start = date(2026, 1, 1)
    assert get_day_index(start, date(2026, 1, 1)) == 0
    assert get_day_index(start, date(2026, 1, 2)) == 1
    assert get_day_index(start, date(2026, 1, 11)) == 10


def test_get_day_index_before_start_is_negative():
    assert get_day_index(date(2026, 1, 10), date(2026, 1, 8)) == -2


def test_assignment_day_zero_is_deterministic():
    rooms = ["Kitchen", "Bath", "Office", "Den"]
    people = ["Alice", "Bob"]
    assert get_assignment(0, rooms, people) == {"Alice": "Kitchen", "Bob": "Bath"}


def test_assignment_one_per_person_each_day():
    rooms = ["A", "B", "C", "D"]
    people = ["P1", "P2"]
    for day in range(10):
        assignment = get_assignment(day, rooms, people)
        assert set(assignment) == set(people)
        # No two people get the same room on the same day.
        assert len(set(assignment.values())) == len(people)


def test_half_cycle_covers_every_room_once():
    rooms = ["A", "B", "C", "D"]
    people = ["P1", "P2"]
    half_cycle = len(rooms) // len(people)  # 2
    covered = set()
    for day in range(half_cycle):
        covered.update(get_assignment(day, rooms, people).values())
    assert covered == set(rooms)


def test_full_cycle_each_person_cleans_every_room_once():
    rooms = ["A", "B", "C", "D"]
    people = ["P1", "P2"]
    cycle = len(rooms)
    seen = {p: [] for p in people}
    for day in range(cycle):
        for person, room in get_assignment(day, rooms, people).items():
            seen[person].append(room)
    for person, room_list in seen.items():
        assert sorted(room_list) == sorted(rooms), person


def test_rotation_is_periodic_over_full_cycle():
    rooms = ["A", "B", "C", "D"]
    people = ["P1", "P2"]
    assert get_assignment(0, rooms, people) == get_assignment(4, rooms, people)
    assert get_assignment(1, rooms, people) == get_assignment(5, rooms, people)


def test_more_people_than_rooms_wraps():
    rooms = ["Only"]
    people = ["P1", "P2", "P3"]
    assignment = get_assignment(0, rooms, people)
    assert assignment == {"P1": "Only", "P2": "Only", "P3": "Only"}


def test_empty_inputs_return_empty():
    assert get_assignment(0, [], ["P1"]) == {}
    assert get_assignment(0, ["A"], []) == {}


def test_get_schedule_shape_and_dates():
    from chore_tracker.config import AppConfig
    from tests.helpers import default_config

    cfg = AppConfig.model_validate(default_config(start=date(2026, 1, 1)))
    schedule = get_schedule(cfg, days=5)
    assert len(schedule) == 5
    assert schedule[0]["date"] == cfg.today
    for day in schedule:
        assert set(day) == {"date", "day_index", "assignments"}
        assert set(day["assignments"]) == {"Alice", "Bob"}


# --- full house clean ---------------------------------------------------------

from chore_tracker.config import Room
from chore_tracker.scheduler import get_full_clean, resolve_full_clean


def _rooms(*sizes):
    return [Room(name=f"R{i}", tasks=[f"t{j}" for j in range(n)]) for i, n in enumerate(sizes)]


def _total(rooms, names):
    by = {r.name: len(r.tasks) for r in rooms}
    return sum(by[n] for n in names)


def test_full_clean_every_room_once_and_balanced():
    rooms = _rooms(5, 3, 2, 4, 1)
    split = get_full_clean(0, rooms, ["A", "B"])
    flat = [n for v in split.values() for n in v]
    assert sorted(flat) == sorted(r.name for r in rooms)
    totals = [_total(rooms, v) for v in split.values()]
    assert abs(totals[0] - totals[1]) <= 5
    for v in split.values():
        assert v == [r.name for r in rooms if r.name in v]


def test_full_clean_odd_room_count():
    rooms = _rooms(2, 2, 2)
    split = get_full_clean(0, rooms, ["A", "B"])
    assert sorted(len(v) for v in split.values()) == [1, 2]


def test_full_clean_single_member_gets_everything():
    rooms = _rooms(1, 2)
    assert get_full_clean(3, rooms, ["A"]) == {"A": ["R0", "R1"]}


def test_full_clean_empty():
    assert get_full_clean(0, [], ["A", "B"]) == {}
    assert get_full_clean(0, _rooms(1), []) == {}


def test_full_clean_more_people_than_rooms_keeps_every_member():
    split = get_full_clean(0, _rooms(1), ["A", "B"])
    assert set(split) == {"A", "B"}
    assert sorted(len(v) for v in split.values()) == [0, 1]


def test_resolve_keeps_saved_and_adds_new_room_to_lighter():
    rooms = _rooms(3, 1, 1)
    saved = {"A": ["R0"], "B": ["R1"]}
    assert resolve_full_clean(saved, rooms, ["A", "B"]) == {"A": ["R0"], "B": ["R1", "R2"]}


def test_resolve_drops_deleted_room_and_member():
    rooms = _rooms(1, 1)
    saved = {"A": ["R0", "Gone"], "B": ["R1"], "Z": ["R0"]}
    assert resolve_full_clean(saved, rooms, ["A", "B"]) == {"A": ["R0"], "B": ["R1"]}
    # B removed: its room goes to the remaining member
    assert resolve_full_clean(saved, rooms, ["A"]) == {"A": ["R0", "R1"]}


def test_resolve_adds_new_member_empty():
    rooms = _rooms(1)
    assert resolve_full_clean({"A": ["R0"]}, rooms, ["A", "C"]) == {"A": ["R0"], "C": []}
