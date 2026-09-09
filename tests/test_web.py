"""End-to-end HTTP behavior for every route, via TestClient."""
import yaml

from chore_tracker.config import load_config
from tests.helpers import config_path, default_config, write_config


# ── Schedule / home ───────────────────────────────────────────────────────────

def test_home_renders_today_and_links_to_checklist(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Alice" in r.text and "Bob" in r.text
    assert "/checklist/Alice" in r.text  # names link to their checklist


def test_home_empty_state_when_unconfigured(client):
    write_config({"start_date": "2026-01-01", "members": [], "rooms": []})
    r = client.get("/")
    assert r.status_code == 200
    assert "No rooms or members set up yet." in r.text


# ── Rooms ─────────────────────────────────────────────────────────────────────

def test_add_room_persists(client):
    r = client.post("/rooms", data={"name": "Garage"}, follow_redirects=False)
    assert r.status_code == 303
    assert any(room.name == "Garage" for room in load_config(config_path()).rooms)


def test_add_duplicate_room_is_rejected(client):
    r = client.post("/rooms", data={"name": "Kitchen"}, follow_redirects=True)
    assert r.status_code == 200
    names = [room.name for room in load_config(config_path()).rooms]
    assert names.count("Kitchen") == 1


def test_add_and_delete_task(client):
    r = client.post("/rooms/Kitchen/tasks", data={"task": "Mop"}, follow_redirects=False)
    # Redirect to a clean /rooms?msg=... — no '#anchor' that would swallow the
    # query string (scroll position is restored client-side instead).
    loc = r.headers["location"]
    assert loc.startswith("/rooms?") and "#" not in loc
    rooms = {r.name: r for r in load_config(config_path()).rooms}
    assert "Mop" in rooms["Kitchen"].tasks

    client.post("/rooms/Kitchen/tasks/delete", data={"task": "Mop"})
    rooms = {r.name: r for r in load_config(config_path()).rooms}
    assert "Mop" not in rooms["Kitchen"].tasks


def test_delete_room(client):
    client.post("/rooms/delete", data={"name": "Den"})
    assert not any(r.name == "Den" for r in load_config(config_path()).rooms)


# ── Members ───────────────────────────────────────────────────────────────────

def test_add_member_name_only(client):
    r = client.post("/members", data={"name": "Carol"}, follow_redirects=False)
    assert r.status_code == 303
    members = load_config(config_path()).members
    assert any(m.name == "Carol" for m in members)
    # Persisted YAML carries only the name — no ntfy field.
    raw = yaml.safe_load(config_path().read_text())
    carol = next(m for m in raw["members"] if m["name"] == "Carol")
    assert carol == {"name": "Carol"}


def test_add_duplicate_member_rejected(client):
    client.post("/members", data={"name": "Alice"})
    names = [m.name for m in load_config(config_path()).members]
    assert names.count("Alice") == 1


def test_delete_member(client):
    client.post("/members/delete", data={"name": "Bob"})
    assert not any(m.name == "Bob" for m in load_config(config_path()).members)


def test_members_page_uses_config_base_url(client):
    r = client.get("/members")
    assert r.status_code == 200
    # Derived from ntfy_base_url + lowercased name; no per-member topic input.
    assert "https://ntfy.example.com/alice" in r.text
    assert 'name="ntfy"' not in r.text


# ── Checklist ─────────────────────────────────────────────────────────────────

def test_checklist_shows_todays_tasks_with_checkboxes(client):
    # Today (day 0): Alice -> Kitchen (Dishes, Sweep).
    r = client.get("/checklist/Alice")
    assert r.status_code == 200
    assert 'type="checkbox"' in r.text
    assert 'value="Dishes"' in r.text and 'value="Sweep"' in r.text


def test_checklist_unknown_member_redirects_home(client):
    r = client.get("/checklist/Nobody", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/?")
    assert "Unknown+member" in r.headers["location"].replace("%20", "+")


def test_checklist_toggle_persists_and_is_shared(client):
    client.post("/checklist/Alice", data={"tasks": ["Dishes"]}, follow_redirects=False)
    # A second, independent request sees the same checked state (shared store).
    r = client.get("/checklist/Alice")
    assert "checked" in r.text
    # The checked task renders with the done styling hook.
    assert "is-done" in r.text


def test_checklist_only_records_valid_tasks(client):
    client.post("/checklist/Alice", data={"tasks": ["Dishes", "NotARealTask"]})
    from chore_tracker import checks
    from chore_tracker.scheduler import get_day_index

    cfg = load_config(config_path())
    idx = get_day_index(cfg.start_date, cfg.today)
    assert checks.get_done(idx, "Alice") == {"Dishes"}


def test_checklist_empty_submit_clears(client):
    client.post("/checklist/Alice", data={"tasks": ["Dishes"]})
    client.post("/checklist/Alice", data={})  # nothing checked
    from chore_tracker import checks
    from chore_tracker.scheduler import get_day_index

    cfg = load_config(config_path())
    idx = get_day_index(cfg.start_date, cfg.today)
    assert checks.get_done(idx, "Alice") == set()


def test_checklist_post_unknown_member_redirects_home(client):
    r = client.post("/checklist/Nobody", data={"tasks": ["x"]}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/?")


# ── Notifications ─────────────────────────────────────────────────────────────

def test_notify_today_reports_sent_and_failed(client, monkeypatch):
    async def fake_notify(config):
        return {"Alice": True, "Bob": False}

    monkeypatch.setattr("chore_tracker.main.notify_today", fake_notify)
    r = client.post("/notify/today", follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers["location"]
    assert "Alice" in loc and "Bob" in loc
    assert "kind=warning" in loc  # a failure flips the flash to warning


def test_notify_today_no_assignments_warns(client, monkeypatch):
    async def fake_notify(config):
        return {}

    monkeypatch.setattr("chore_tracker.main.notify_today", fake_notify)
    r = client.post("/notify/today", follow_redirects=False)
    assert "No+assignments" in r.headers["location"].replace("%20", "+")
    assert "kind=warning" in r.headers["location"]


# ── Settings: notification times ──────────────────────────────────────────────

def test_settings_page_lists_notify_times(client):
    write_config({**default_config(), "notify_times": ["08:00", "17:00"]})
    r = client.get("/settings")
    assert r.status_code == 200
    assert "08:00" in r.text and "17:00" in r.text


def test_add_notify_time_persists_and_sorts(client):
    write_config({**default_config(), "notify_times": ["08:00"]})
    client.post("/settings/notify-times", data={"time": "17:00"})
    client.post("/settings/notify-times", data={"time": "10:00"})
    assert load_config(config_path()).notify_times == ["08:00", "10:00", "17:00"]


def test_add_invalid_notify_time_warns_and_keeps_existing(client):
    write_config({**default_config(), "notify_times": ["08:00"]})
    r = client.post("/settings/notify-times", data={"time": "99:99"}, follow_redirects=False)
    assert "kind=warning" in r.headers["location"]
    assert load_config(config_path()).notify_times == ["08:00"]


def test_delete_notify_time(client):
    write_config({**default_config(), "notify_times": ["08:00", "17:00"]})
    client.post("/settings/notify-times/delete", data={"time": "08:00"})
    assert load_config(config_path()).notify_times == ["17:00"]


# ── JSON API ──────────────────────────────────────────────────────────────────

def test_api_schedule_returns_json(client):
    r = client.get("/api/schedule")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 14
    assert set(data[0]) == {"date", "assignments"}
    assert set(data[0]["assignments"]) == {"Alice", "Bob"}


# ── Static assets / cache-busting ─────────────────────────────────────────────

def test_stylesheet_is_cache_busted(client):
    r = client.get("/")
    assert "/static/style.css?v=" in r.text


def test_checklist_css_is_served(client):
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert ".checklist" in r.text


# ── Shopping lists ────────────────────────────────────────────────────────────

def _lists():
    from chore_tracker.lists import load_lists
    from tests.helpers import lists_path
    return {gl.name: gl for gl in load_lists(lists_path()).lists}


def test_lists_page_seeds_default_list_and_nav_link(client):
    r = client.get("/lists")
    assert r.status_code == 200
    assert "Groceries" in r.text
    assert 'href="/lists"' in r.text
    assert "Nothing on the list." in r.text


def test_add_list_persists_and_rejects_duplicate(client):
    r = client.post("/lists", data={"name": "Costco"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/lists?")
    assert "Costco" in _lists()

    r = client.post("/lists", data={"name": "Costco"}, follow_redirects=False)
    assert "kind=warning" in r.headers["location"]
    assert list(_lists()) == ["Groceries", "Costco"]


def test_add_list_item_persists_in_order(client):
    client.post("/lists/Groceries/items", data={"item": "Milk"})
    client.post("/lists/Groceries/items", data={"item": "Eggs"})
    items = _lists()["Groceries"].items
    assert [(i.name, i.done) for i in items] == [("Milk", False), ("Eggs", False)]


def test_add_duplicate_unbought_item_warns(client):
    client.post("/lists/Groceries/items", data={"item": "Milk"})
    r = client.post("/lists/Groceries/items", data={"item": "Milk"}, follow_redirects=False)
    assert "kind=warning" in r.headers["location"]
    assert len(_lists()["Groceries"].items) == 1


def test_readding_bought_item_puts_it_back_on_the_list(client):
    client.post("/lists/Groceries/items", data={"item": "Milk"})
    client.post("/lists/Groceries/items/toggle", data={"item": "Milk", "done": "1"})
    assert _lists()["Groceries"].find("Milk").done is True

    r = client.post("/lists/Groceries/items", data={"item": "Milk"}, follow_redirects=False)
    assert "kind=warning" not in r.headers["location"]
    items = _lists()["Groceries"].items
    assert len(items) == 1 and items[0].done is False


def test_toggle_sets_done_and_unchecked_submit_clears_it(client):
    client.post("/lists/Groceries/items", data={"item": "Bread"})
    client.post("/lists/Groceries/items/toggle", data={"item": "Bread", "done": "1"})
    assert _lists()["Groceries"].find("Bread").done is True
    r = client.get("/lists")
    assert "checked" in r.text and "is-done" in r.text and "all bought" in r.text

    # An unchecked checkbox is simply absent from the form body.
    client.post("/lists/Groceries/items/toggle", data={"item": "Bread"})
    assert _lists()["Groceries"].find("Bread").done is False
    assert "1 to buy" in client.get("/lists").text


def test_toggle_unknown_item_warns(client):
    r = client.post(
        "/lists/Groceries/items/toggle", data={"item": "Ghost", "done": "1"},
        follow_redirects=False,
    )
    assert "kind=warning" in r.headers["location"]


def test_delete_list_item(client):
    client.post("/lists/Groceries/items", data={"item": "Milk"})
    client.post("/lists/Groceries/items", data={"item": "Eggs"})
    client.post("/lists/Groceries/items/delete", data={"item": "Milk"})
    assert [i.name for i in _lists()["Groceries"].items] == ["Eggs"]


def test_clear_bought_removes_only_done_items(client):
    for name in ("Milk", "Eggs", "Bread"):
        client.post("/lists/Groceries/items", data={"item": name})
    client.post("/lists/Groceries/items/toggle", data={"item": "Milk", "done": "1"})
    client.post("/lists/Groceries/items/toggle", data={"item": "Bread", "done": "1"})
    assert "Clear 2 bought" in client.get("/lists").text

    r = client.post("/lists/Groceries/clear", follow_redirects=False)
    assert "Cleared+2+bought+items" in r.headers["location"].replace("%20", "+")
    assert [i.name for i in _lists()["Groceries"].items] == ["Eggs"]
    assert "Clear " not in client.get("/lists").text.split("Add a list")[0].split("card-body")[1]


def test_delete_list(client):
    client.post("/lists", data={"name": "Costco"})
    client.post("/lists/delete", data={"name": "Groceries"})
    assert list(_lists()) == ["Costco"]


def test_deleting_last_list_stays_empty_across_reloads(client):
    client.post("/lists/delete", data={"name": "Groceries"})
    assert _lists() == {}
    assert "No lists yet." in client.get("/lists").text


def test_unknown_list_routes_warn(client):
    for path, data in (
        ("/lists/Nope/items", {"item": "x"}),
        ("/lists/Nope/clear", {}),
    ):
        r = client.post(path, data=data, follow_redirects=False)
        assert r.status_code == 303 and "kind=warning" in r.headers["location"], path


def test_list_writes_never_touch_config(client):
    before = config_path().read_text()
    client.post("/lists", data={"name": "Costco"})
    client.post("/lists/Costco/items", data={"item": "Paper towels"})
    client.post("/lists/Costco/items/toggle", data={"item": "Paper towels", "done": "1"})
    assert config_path().read_text() == before
    from tests.helpers import lists_path
    assert lists_path().exists()


def test_list_css_is_served(client):
    r = client.get("/static/style.css")
    assert ".list-row" in r.text
