"""End-to-end HTTP behavior for every /api/* route, via TestClient."""
import pytest
import yaml

from chore_tracker.config import load_config
from tests.helpers import config_path, default_config, write_config


# ── /api/home ─────────────────────────────────────────────────────────────────

def test_api_home_returns_schedule_and_progress(client):
    r = client.get("/api/home")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["schedule"], list) and len(data["schedule"]) == 14
    assert "today_idx" in data and "half_cycle" in data
    assert "notify_times" in data and "done_map" in data
    assert set(data["done_map"]) == {"Alice", "Bob"}


def test_api_home_empty_state(client):
    write_config({"start_date": "2026-01-01", "members": [], "rooms": []})
    r = client.get("/api/home")
    assert r.status_code == 200
    data = r.json()
    assert data["done_map"] == {}
    assert data["half_cycle"] == 0


# ── /api/rooms ────────────────────────────────────────────────────────────────

def test_api_rooms_list(client):
    r = client.get("/api/rooms")
    assert r.status_code == 200
    rooms = r.json()
    assert isinstance(rooms, list)
    names = [room["name"] for room in rooms]
    assert "Kitchen" in names and "Bath" in names


def test_api_add_room_persists(client):
    r = client.post("/api/rooms", json={"name": "Garage"})
    assert r.status_code == 201
    assert r.json()["name"] == "Garage"
    assert any(room.name == "Garage" for room in load_config(config_path()).rooms)


def test_api_add_room_duplicate_returns_409(client):
    r = client.post("/api/rooms", json={"name": "Kitchen"})
    assert r.status_code == 409
    names = [room.name for room in load_config(config_path()).rooms]
    assert names.count("Kitchen") == 1


def test_api_add_room_empty_name_returns_409(client):
    r = client.post("/api/rooms", json={"name": "   "})
    assert r.status_code == 409


def test_api_delete_room(client):
    r = client.delete("/api/rooms/Den")
    assert r.status_code == 200
    assert not any(room.name == "Den" for room in load_config(config_path()).rooms)


def test_api_delete_room_not_found_returns_404(client):
    r = client.delete("/api/rooms/Nonexistent")
    assert r.status_code == 404


# ── /api/rooms/{room}/tasks ───────────────────────────────────────────────────

def test_api_add_task_persists(client):
    r = client.post("/api/rooms/Kitchen/tasks", json={"task": "Mop"})
    assert r.status_code == 201
    assert r.json()["task"] == "Mop"
    rooms = {r.name: r for r in load_config(config_path()).rooms}
    assert "Mop" in rooms["Kitchen"].tasks


def test_api_add_task_duplicate_returns_409(client):
    r = client.post("/api/rooms/Kitchen/tasks", json={"task": "Dishes"})
    assert r.status_code == 409


def test_api_add_task_unknown_room_returns_404(client):
    r = client.post("/api/rooms/Nonexistent/tasks", json={"task": "Mop"})
    assert r.status_code == 404


def test_api_delete_task(client):
    r = client.delete("/api/rooms/Kitchen/tasks/Dishes")
    assert r.status_code == 200
    rooms = {r.name: r for r in load_config(config_path()).rooms}
    assert "Dishes" not in rooms["Kitchen"].tasks


# ── /api/members ──────────────────────────────────────────────────────────────

def test_api_members_list(client):
    r = client.get("/api/members")
    assert r.status_code == 200
    data = r.json()
    assert "members" in data and "ntfy_base_url" in data
    names = [m["name"] for m in data["members"]]
    assert "Alice" in names and "Bob" in names
    alice = next(m for m in data["members"] if m["name"] == "Alice")
    assert alice["ntfy_url"] == "https://ntfy.example.com/alice"
    assert alice["topic"] == "alice"


def test_api_add_member_persists(client):
    r = client.post("/api/members", json={"name": "Carol"})
    assert r.status_code == 201
    assert r.json()["name"] == "Carol"
    assert any(m.name == "Carol" for m in load_config(config_path()).members)
    # Persisted YAML carries only the name — no extra fields.
    raw = yaml.safe_load(config_path().read_text())
    carol = next(m for m in raw["members"] if m["name"] == "Carol")
    assert carol == {"name": "Carol"}


def test_api_add_member_duplicate_returns_409(client):
    r = client.post("/api/members", json={"name": "Alice"})
    assert r.status_code == 409


def test_api_delete_member(client):
    r = client.delete("/api/members/Bob")
    assert r.status_code == 200
    assert not any(m.name == "Bob" for m in load_config(config_path()).members)


def test_api_delete_member_not_found_returns_404(client):
    r = client.delete("/api/members/Nobody")
    assert r.status_code == 404


# ── /api/settings ─────────────────────────────────────────────────────────────

def test_api_settings(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert "notify_times" in data and "timezone" in data
    assert "08:00" in data["notify_times"]


def test_api_add_notify_time_persists_and_sorts(client):
    write_config({**default_config(), "notify_times": ["08:00"]})
    r = client.post("/api/settings/notify-times", json={"time": "17:00"})
    assert r.status_code == 201
    client.post("/api/settings/notify-times", json={"time": "10:00"})
    assert load_config(config_path()).notify_times == ["08:00", "10:00", "17:00"]


def test_api_add_invalid_notify_time_returns_400(client):
    r = client.post("/api/settings/notify-times", json={"time": "99:99"})
    assert r.status_code == 400
    assert load_config(config_path()).notify_times == ["08:00"]


def test_api_delete_notify_time(client):
    write_config({**default_config(), "notify_times": ["08:00", "17:00"]})
    r = client.delete("/api/settings/notify-times/08:00")
    assert r.status_code == 200
    assert load_config(config_path()).notify_times == ["17:00"]


# ── /api/checklist ────────────────────────────────────────────────────────────

def test_api_checklist_get_shows_todays_tasks(client):
    # Day 0: Alice → Kitchen (Dishes, Sweep).
    r = client.get("/api/checklist/Alice")
    assert r.status_code == 200
    data = r.json()
    assert data["member"] == "Alice"
    assert data["room_name"] == "Kitchen"
    assert set(data["tasks"]) == {"Dishes", "Sweep"}
    assert data["done"] == []


def test_api_checklist_unknown_member_returns_404(client):
    r = client.get("/api/checklist/Nobody")
    assert r.status_code == 404


def test_api_checklist_post_persists(client):
    r = client.post("/api/checklist/Alice", json={"tasks": ["Dishes"]})
    assert r.status_code == 200
    assert "Dishes" in r.json()["done"]


def test_api_checklist_toggle_visible_on_get(client):
    client.post("/api/checklist/Alice", json={"tasks": ["Dishes"]})
    r = client.get("/api/checklist/Alice")
    assert "Dishes" in r.json()["done"]


def test_api_checklist_only_records_valid_tasks(client):
    client.post("/api/checklist/Alice", json={"tasks": ["Dishes", "NotARealTask"]})
    from chore_tracker import checks
    from chore_tracker.scheduler import get_day_index

    cfg = load_config(config_path())
    idx = get_day_index(cfg.start_date, cfg.today)
    room = client.get("/api/checklist/Alice").json()["room_name"]
    assert checks.get_done(idx, room) == {"Dishes"}


def test_api_checklist_empty_submit_clears(client):
    client.post("/api/checklist/Alice", json={"tasks": ["Dishes"]})
    client.post("/api/checklist/Alice", json={"tasks": []})
    from chore_tracker import checks
    from chore_tracker.scheduler import get_day_index

    cfg = load_config(config_path())
    idx = get_day_index(cfg.start_date, cfg.today)
    room = client.get("/api/checklist/Alice").json()["room_name"]
    assert checks.get_done(idx, room) == set()


def test_api_checklist_post_unknown_member_returns_404(client):
    r = client.post("/api/checklist/Nobody", json={"tasks": []})
    assert r.status_code == 404


# ── /api/notify/today ─────────────────────────────────────────────────────────

def test_api_notify_today_returns_sent_and_failed(client, monkeypatch):
    async def fake_notify(config, **kwargs):
        return {"Alice": True, "Bob": False}

    monkeypatch.setattr("chore_tracker.main.notify_today", fake_notify)
    r = client.post("/api/notify/today")
    assert r.status_code == 200
    data = r.json()
    assert "Alice" in data["sent"]
    assert "Bob" in data["failed"]


def test_api_notify_today_no_assignments(client, monkeypatch):
    async def fake_notify(config, **kwargs):
        return {}

    monkeypatch.setattr("chore_tracker.main.notify_today", fake_notify)
    r = client.post("/api/notify/today")
    assert r.status_code == 200
    assert r.json() == {"sent": [], "failed": []}


# ── /api/schedule ─────────────────────────────────────────────────────────────

def test_api_schedule_returns_json(client):
    r = client.get("/api/schedule")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 14
    assert set(data[0]) == {"date", "assignments"}
    assert set(data[0]["assignments"]) == {"Alice", "Bob"}


# ── SPA catch-all ─────────────────────────────────────────────────────────────

def test_spa_fallback_serves_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_spa_fallback_on_spa_path(client):
    r = client.get("/checklist/Alice")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


# ── /api/lists ────────────────────────────────────────────────────────────────

def _lists():
    from chore_tracker.lists import load_lists
    from tests.helpers import lists_path
    return {sl.name: sl for sl in load_lists(lists_path()).lists}


def test_api_lists_seeds_default_list(client):
    r = client.get("/api/lists")
    assert r.status_code == 200
    assert r.json() == [{"name": "Groceries", "items": [], "remaining": 0, "bought": 0}]


def test_api_add_list_persists_and_rejects_duplicate(client):
    r = client.post("/api/lists", json={"name": "Costco"})
    assert r.status_code == 201 and r.json()["name"] == "Costco"
    assert "Costco" in _lists()

    r = client.post("/api/lists", json={"name": "Costco"})
    assert r.status_code == 409
    assert list(_lists()) == ["Groceries", "Costco"]


def test_api_add_list_rejects_empty_name(client):
    r = client.post("/api/lists", json={"name": "   "})
    assert r.status_code == 409


def test_api_add_list_item_persists_in_order(client):
    client.post("/api/lists/Groceries/items", json={"item": "Milk"})
    r = client.post("/api/lists/Groceries/items", json={"item": "Eggs"})
    assert r.status_code == 201
    assert [i["name"] for i in r.json()["items"]] == ["Milk", "Eggs"]
    assert [i.name for i in _lists()["Groceries"].items] == ["Milk", "Eggs"]


def test_api_add_duplicate_unbought_item_conflicts(client):
    client.post("/api/lists/Groceries/items", json={"item": "Milk"})
    r = client.post("/api/lists/Groceries/items", json={"item": "Milk"})
    assert r.status_code == 409
    assert len(_lists()["Groceries"].items) == 1


def test_api_readding_bought_item_puts_it_back(client):
    client.post("/api/lists/Groceries/items", json={"item": "Milk"})
    client.put("/api/lists/Groceries/items", json={"item": "Milk", "done": True})
    assert _lists()["Groceries"].find("Milk").done is True

    r = client.post("/api/lists/Groceries/items", json={"item": "Milk"})
    assert r.status_code == 201
    assert _lists()["Groceries"].find("Milk").done is False
    assert len(_lists()["Groceries"].items) == 1


def test_api_set_item_done_is_idempotent(client):
    client.post("/api/lists/Groceries/items", json={"item": "Bread"})
    for _ in range(2):  # two phones tapping at once land on the same state
        r = client.put("/api/lists/Groceries/items", json={"item": "Bread", "done": True})
        assert r.status_code == 200
    assert r.json()["bought"] == 1 and r.json()["remaining"] == 0

    r = client.put("/api/lists/Groceries/items", json={"item": "Bread", "done": False})
    assert r.json()["remaining"] == 1


def test_api_set_unknown_item_404s(client):
    r = client.put("/api/lists/Groceries/items", json={"item": "Ghost", "done": True})
    assert r.status_code == 404


def test_api_delete_list_item(client):
    client.post("/api/lists/Groceries/items", json={"item": "Milk"})
    client.post("/api/lists/Groceries/items", json={"item": "Eggs"})
    r = client.delete("/api/lists/Groceries/items/Milk")
    assert r.status_code == 200
    assert [i.name for i in _lists()["Groceries"].items] == ["Eggs"]


def test_api_delete_item_with_a_slash(client):
    client.post("/api/lists/Groceries/items", json={"item": "1/2 gallon milk"})
    r = client.delete("/api/lists/Groceries/items/1/2 gallon milk")
    assert r.status_code == 200
    assert _lists()["Groceries"].items == []


def test_api_clear_bought_removes_only_done_items(client):
    for name in ("Milk", "Eggs", "Bread"):
        client.post("/api/lists/Groceries/items", json={"item": name})
    client.put("/api/lists/Groceries/items", json={"item": "Milk", "done": True})
    client.put("/api/lists/Groceries/items", json={"item": "Bread", "done": True})

    r = client.post("/api/lists/Groceries/clear")
    assert r.status_code == 200 and r.json()["removed"] == 2
    assert [i.name for i in _lists()["Groceries"].items] == ["Eggs"]


def test_api_delete_list(client):
    client.post("/api/lists", json={"name": "Costco"})
    r = client.delete("/api/lists/Groceries")
    assert r.status_code == 200
    assert list(_lists()) == ["Costco"]


def test_api_deleting_last_list_stays_empty_across_reloads(client):
    client.delete("/api/lists/Groceries")
    assert client.get("/api/lists").json() == []
    assert client.get("/api/lists").json() == []


def test_api_unknown_list_routes_404(client):
    assert client.delete("/api/lists/Nope").status_code == 404
    assert client.post("/api/lists/Nope/items", json={"item": "x"}).status_code == 404
    assert client.put("/api/lists/Nope/items", json={"item": "x", "done": True}).status_code == 404
    assert client.delete("/api/lists/Nope/items/x").status_code == 404
    assert client.post("/api/lists/Nope/clear").status_code == 404


def test_api_list_writes_never_touch_config(client):
    before = config_path().read_text()
    client.post("/api/lists", json={"name": "Costco"})
    client.post("/api/lists/Costco/items", json={"item": "Paper towels"})
    client.put("/api/lists/Costco/items", json={"item": "Paper towels", "done": True})
    assert config_path().read_text() == before


def test_spa_fallback_serves_lists_path(client):
    r = client.get("/lists")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


# ── full clean ────────────────────────────────────────────────────────────────

def test_full_clean_start_stop_and_ticks_follow_room(client, monkeypatch):
    async def fake_notify(config, *, trigger="manual"):
        return {"Alice": True, "Bob": False}

    monkeypatch.setattr("chore_tracker.main.notify_today", fake_notify)
    client.post("/api/checklist/Alice", json={"tasks": ["Dishes"]})
    r = client.post("/api/full-clean")
    assert r.status_code == 200
    data = r.json()
    assert data["active"] and data["sent"] == ["Alice"] and data["failed"] == ["Bob"]
    assert sorted(sum(data["assignments"].values(), [])) == sorted(
        r["name"] for r in client.get("/api/rooms").json()
    )
    again = client.post("/api/full-clean").json()
    assert again["sent"] == [] and again["failed"] == []
    home = client.get("/api/home").json()
    assert home["full_clean"] is True and home["full_clean_rooms"] == data["assignments"]
    chk = client.get("/api/checklist/Alice").json()
    assert chk["full_clean"] is True and len(chk["rooms"]) == len(data["assignments"]["Alice"])
    assert client.delete("/api/full-clean").json() == {"active": False}
    assert client.get("/api/home").json()["full_clean_rooms"] == {}


def test_checklist_post_requires_tasks_or_rooms(client):
    r = client.post("/api/checklist/Alice", json={})
    assert r.status_code == 422 and r.json() == {"detail": "Send tasks or rooms"}


# ── full clean: behaviour ─────────────────────────────────────────────────────

@pytest.fixture
def notify_calls(monkeypatch):
    calls = []

    async def fake_notify(config, *, trigger="manual"):
        calls.append(trigger)
        return {m.name: True for m in config.members}

    monkeypatch.setattr("chore_tracker.main.notify_today", fake_notify)
    return calls


def _start(client):
    r = client.post("/api/full-clean")
    assert r.status_code == 200
    return r.json()["assignments"]


def test_full_clean_start_notifies_once_and_stop_does_not(client, notify_calls):
    r = client.post("/api/full-clean").json()
    assert r["sent"] == ["Alice", "Bob"] and notify_calls == ["full_clean"]
    assert client.delete("/api/full-clean").json() == {"active": False}
    assert notify_calls == ["full_clean"]


def test_full_clean_409_without_rooms_or_members(client, notify_calls):
    write_config({**default_config(), "rooms": []})
    r = client.post("/api/full-clean")
    assert r.status_code == 409 and r.json() == {"detail": "Add rooms and members first"}
    write_config({**default_config(), "members": []})
    assert client.post("/api/full-clean").status_code == 409
    assert notify_calls == []


def test_full_clean_repost_keeps_split_and_sends_nothing(client, notify_calls):
    first = _start(client)
    client.post("/api/rooms/Bath/tasks", json={"task": "Mop"})
    notify_calls.clear()
    r = client.post("/api/full-clean").json()
    assert r["assignments"] == first
    assert r["sent"] == [] and r["failed"] == []
    assert notify_calls == []


def test_full_clean_room_added_after_start_goes_to_lighter_person(client, notify_calls):
    before = _start(client)
    room_map = {r["name"]: len(r["tasks"]) for r in client.get("/api/rooms").json()}
    load = {m: sum(room_map[n] for n in rooms) for m, rooms in before.items()}
    lighter = min(load, key=lambda m: (load[m], list(before).index(m)))
    client.post("/api/rooms", json={"name": "Garage"})
    after = client.get("/api/home").json()["full_clean_rooms"]
    assert "Garage" in after[lighter]
    for m in before:
        assert set(before[m]) <= set(after[m])


def test_full_clean_deleted_room_and_member_are_dropped(client, notify_calls):
    before = _start(client)
    gone = before["Alice"][0]
    client.delete(f"/api/rooms/{gone}")
    home = client.get("/api/home").json()
    assert gone not in sum(home["full_clean_rooms"].values(), [])
    client.delete("/api/members/Bob")
    home = client.get("/api/home").json()
    assert list(home["full_clean_rooms"]) == ["Alice"]
    assert home["full_clean"] is True


def test_full_clean_schedule_unchanged_while_active(client, notify_calls):
    normal = client.get("/api/schedule").json()
    _start(client)
    assert client.get("/api/schedule").json() == normal
    home = client.get("/api/home").json()
    assert home["schedule"] == normal


def test_full_clean_same_task_name_in_two_rooms_ticks_separately(client, notify_calls):
    write_config({
        **default_config(),
        "members": [{"name": "Alice"}],
        "rooms": [
            {"name": "Kitchen", "tasks": ["Sweep", "Dishes"]},
            {"name": "Den", "tasks": ["Sweep"]},
        ],
    })
    _start(client)
    r = client.post("/api/checklist/Alice", json={"rooms": {"Kitchen": ["Sweep"]}}).json()
    by_room = {x["name"]: x["done"] for x in r["rooms"]}
    assert by_room == {"Kitchen": ["Sweep"], "Den": []}
    done = client.get("/api/home").json()["done_map"]["Alice"]
    assert done == {"done": 1, "total": 3}


def test_full_clean_keeps_ticks_made_in_normal_mode(client, notify_calls):
    chk = client.get("/api/checklist/Alice").json()
    room = chk["room_name"]
    client.post("/api/checklist/Alice", json={"tasks": [chk["tasks"][0]]})
    assignments = _start(client)
    holder = next(m for m, rooms in assignments.items() if room in rooms)
    mine = {r["name"]: r for r in client.get(f"/api/checklist/{holder}").json()["rooms"]}
    assert mine[room]["done"] == [chk["tasks"][0]]
    assert client.get("/api/home").json()["done_map"][holder]["done"] == 1


def test_checklist_post_empty_body_is_422(client):
    r = client.post("/api/checklist/Alice", json={})
    assert r.status_code == 422


def test_checklist_normal_mode_drops_rooms_not_held(client):
    other = "Bath"  # Alice holds Kitchen today
    r = client.post("/api/checklist/Alice", json={"rooms": {other: ["Toilet"]}})
    assert r.status_code == 200
    assert client.get("/api/checklist/Bob").json()["done"] == []


def test_full_clean_round_trips_through_config(client, notify_calls):
    assignments = _start(client)
    cfg = load_config(config_path())
    assert cfg.full_clean_active and cfg.full_clean.assignments == assignments
    raw = yaml.safe_load(config_path().read_text())
    assert raw["full_clean"]["date"] == str(cfg.today)
    client.delete("/api/full-clean")
    assert "full_clean" not in yaml.safe_load(config_path().read_text())


def test_full_clean_survives_notify_time_and_member_changes(client, notify_calls):
    saved = _start(client)
    client.post("/api/settings/notify-times", json={"time": "17:00"})
    home = client.get("/api/home").json()
    assert home["full_clean"] is True and home["full_clean_rooms"] == saved
    client.post("/api/members", json={"name": "Cara"})
    home = client.get("/api/home").json()
    assert home["full_clean"] is True
    assert home["full_clean_rooms"] == {**saved, "Cara": []}


def test_two_members_on_one_room_share_ticks(client):
    write_config({
        **default_config(),
        "members": [{"name": "Alice"}, {"name": "Bob"}, {"name": "Cara"}],
        "rooms": [
            {"name": "Kitchen", "tasks": ["Dishes", "Sweep"]},
            {"name": "Bath", "tasks": ["Toilet"]},
        ],
    })
    rooms = {m: client.get(f"/api/checklist/{m}").json()["room_name"] for m in ("Alice", "Bob", "Cara")}
    shared = next(r for r in set(rooms.values()) if list(rooms.values()).count(r) == 2)
    a, b = [m for m, r in rooms.items() if r == shared]
    tasks = client.get(f"/api/checklist/{a}").json()["tasks"]
    client.post(f"/api/checklist/{a}", json={"tasks": [tasks[0]]})
    assert client.get(f"/api/checklist/{b}").json()["done"] == [tasks[0]]
