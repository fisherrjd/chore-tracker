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
    assert schedule[0]["date"] == date.today()
    for day in schedule:
        assert set(day) == {"date", "day_index", "assignments"}
        assert set(day["assignments"]) == {"Alice", "Bob"}
