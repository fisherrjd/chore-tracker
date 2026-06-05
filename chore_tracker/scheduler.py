from datetime import date, timedelta
from .config import AppConfig


def get_day_index(start_date: date, today: date | None = None) -> int:
    return ((today or date.today()) - start_date).days


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


def get_schedule(config: AppConfig, days: int = 14) -> list[dict]:
    room_names = [r.name for r in config.rooms]
    member_names = [m.name for m in config.members]
    today = date.today()
    schedule = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        idx = get_day_index(config.start_date, day)
        assignments = get_assignment(idx, room_names, member_names)
        schedule.append({"date": day, "day_index": idx, "assignments": assignments})
    return schedule
