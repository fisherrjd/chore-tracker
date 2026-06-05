"""In-memory checklist store: shared across callers, scoped to one day."""
from chore_tracker import checks


def test_set_and_get_done():
    checks.set_done(5, "Alice", ["Dishes", "Sweep"])
    assert checks.get_done(5, "Alice") == {"Dishes", "Sweep"}


def test_get_done_returns_a_copy():
    checks.set_done(5, "Alice", ["Dishes"])
    got = checks.get_done(5, "Alice")
    got.add("Mutated")
    assert checks.get_done(5, "Alice") == {"Dishes"}


def test_unknown_member_or_day_is_empty():
    assert checks.get_done(99, "Nobody") == set()


def test_set_done_replaces_previous():
    checks.set_done(5, "Alice", ["Dishes", "Sweep"])
    checks.set_done(5, "Alice", ["Sweep"])
    assert checks.get_done(5, "Alice") == {"Sweep"}


def test_state_is_scoped_to_day_and_resets():
    checks.set_done(1, "Alice", ["Dishes"])
    # Writing for a new day drops all previous days' state.
    checks.set_done(2, "Alice", ["Vacuum"])
    assert checks.get_done(2, "Alice") == {"Vacuum"}
    assert checks.get_done(1, "Alice") == set()


def test_members_share_a_day_but_track_separately():
    checks.set_done(3, "Alice", ["Dishes"])
    checks.set_done(3, "Bob", ["Toilet"])
    assert checks.get_done(3, "Alice") == {"Dishes"}
    assert checks.get_done(3, "Bob") == {"Toilet"}
