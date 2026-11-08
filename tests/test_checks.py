"""In-memory checklist store: shared across callers, scoped to one day."""
from chore_tracker import checks


def test_set_and_get_done():
    checks.set_done(5, "Kitchen", ["Dishes", "Sweep"])
    assert checks.get_done(5, "Kitchen") == {"Dishes", "Sweep"}


def test_get_done_returns_a_copy():
    checks.set_done(5, "Kitchen", ["Dishes"])
    got = checks.get_done(5, "Kitchen")
    got.add("Mutated")
    assert checks.get_done(5, "Kitchen") == {"Dishes"}


def test_unknown_room_or_day_is_empty():
    assert checks.get_done(99, "Nowhere") == set()


def test_set_done_replaces_previous():
    checks.set_done(5, "Kitchen", ["Dishes", "Sweep"])
    checks.set_done(5, "Kitchen", ["Sweep"])
    assert checks.get_done(5, "Kitchen") == {"Sweep"}


def test_state_is_scoped_to_day_and_resets():
    checks.set_done(1, "Kitchen", ["Dishes"])
    # Writing for a new day drops all previous days' state.
    checks.set_done(2, "Kitchen", ["Vacuum"])
    assert checks.get_done(2, "Kitchen") == {"Vacuum"}
    assert checks.get_done(1, "Kitchen") == set()


def test_rooms_share_a_day_but_track_separately():
    checks.set_done(3, "Kitchen", ["Dishes"])
    checks.set_done(3, "Bathroom", ["Toilet"])
    assert checks.get_done(3, "Kitchen") == {"Dishes"}
    assert checks.get_done(3, "Bathroom") == {"Toilet"}
