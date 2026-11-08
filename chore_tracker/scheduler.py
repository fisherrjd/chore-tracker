from datetime import date, timedelta
from .config import AppConfig, Room


def get_day_index(start_date: date, today: date) -> int:
    return (today - start_date).days


def get_assignment(day_index: int, rooms: list[str], people: list[str]) -> dict[str, str]:
    """
    Assign one room per person per day using a round-robin rotation.

    Every (n_rooms // n_people) days all rooms are covered once (half cycle).
    Over the full cycle (n_rooms days) each person cleans every room exactly once.
    Requires len(rooms) % len(people) == 0.
    """
    n_rooms = len(rooms)
    n_people = len(people)
    if n_rooms == 0 or n_people == 0:
        return {}

    half_cycle = n_rooms // n_people
    if half_cycle == 0:
        # More people than rooms — wrap room list
        return {person: rooms[i % n_rooms] for i, person in enumerate(people)}

    day_in_cycle = day_index % n_rooms
    section = day_in_cycle // half_cycle   # rotation phase (0..n_people-1)
    group = day_in_cycle % half_cycle      # room group within the phase

    return {
        person: rooms[group * n_people + (p + section) % n_people]
        for p, person in enumerate(people)
    }


def get_full_clean(day_index: int, rooms: list[Room], people: list[str]) -> dict[str, list[str]]:
    """
    Split every room between all people (catch-up "full house clean").

    Greedy: biggest rooms (by task count) first, each to the person with the
    fewest tasks so far, ties -> fewest rooms, then member order rotated by day.
    Every room lands exactly once; lists are in config room order.
    """
    if not rooms or not people:
        return {}

    shift = day_index % len(people)
    order = people[shift:] + people[:shift]
    tasks = {p: 0 for p in people}
    count = {p: 0 for p in people}
    got: dict[str, set[str]] = {p: set() for p in people}

    for room in sorted(rooms, key=lambda r: -len(r.tasks)):
        who = min(order, key=lambda p: (tasks[p], count[p], order.index(p)))
        got[who].add(room.name)
        tasks[who] += len(room.tasks)
        count[who] += 1

    return {p: [r.name for r in rooms if r.name in got[p]] for p in people}


def resolve_full_clean(
    saved: dict[str, list[str]], rooms: list[Room], people: list[str]
) -> dict[str, list[str]]:
    """
    Reconcile a saved split with the current config: drop gone members/rooms,
    add new members (empty) and hand unassigned rooms to the lightest person.
    Rooms already assigned never move.
    """
    if not rooms or not people:
        return {}

    by_name = {r.name: r for r in rooms}
    got: dict[str, set[str]] = {
        p: {n for n in saved.get(p, []) if n in by_name} for p in people
    }
    assigned = set().union(*got.values())
    tasks = {p: sum(len(by_name[n].tasks) for n in got[p]) for p in people}

    for room in rooms:
        if room.name in assigned:
            continue
        who = min(people, key=lambda p: (tasks[p], people.index(p)))
        got[who].add(room.name)
        tasks[who] += len(room.tasks)

    return {p: [r.name for r in rooms if r.name in got[p]] for p in people}


def get_schedule(config: AppConfig, days: int = 14) -> list[dict]:
    room_names = [r.name for r in config.rooms]
    member_names = [m.name for m in config.members]
    today = config.today
    schedule = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        idx = get_day_index(config.start_date, day)
        assignments = get_assignment(idx, room_names, member_names)
        schedule.append({"date": day, "day_index": idx, "assignments": assignments})
    return schedule


def todays_rooms(config: AppConfig) -> dict[str, list[str]]:
    """Rooms per member for today: the saved full clean if active, else the rotation."""
    members = [m.name for m in config.members]
    if config.full_clean_active:
        return resolve_full_clean(config.full_clean.assignments, config.rooms, members)
    idx = get_day_index(config.start_date, config.today)
    assignments = get_assignment(idx, [r.name for r in config.rooms], members)
    return {m: [room] for m, room in assignments.items()}
