"""Shopping-list store: durable YAML beside the config, seeded with one default list."""
from pathlib import Path

import yaml

from chore_tracker.lists import (
    DEFAULT_LIST,
    ListItem,
    ShoppingList,
    ShoppingLists,
    load_lists,
    save_lists,
)


def test_missing_file_seeds_one_empty_default_list(tmp_path: Path):
    store = load_lists(tmp_path / "lists.yaml")
    assert [sl.name for sl in store.lists] == [DEFAULT_LIST]
    assert store.lists[0].items == []
    # Seeding is in-memory only — nothing is written until the first save.
    assert not (tmp_path / "lists.yaml").exists()


def test_existing_empty_file_stays_empty(tmp_path: Path):
    path = tmp_path / "lists.yaml"
    path.write_text("")
    assert load_lists(path).lists == []


def test_save_and_load_roundtrip_preserves_order_and_done(tmp_path: Path):
    path = tmp_path / "lists.yaml"
    store = ShoppingLists(lists=[
        ShoppingList(name="Costco", items=[
            ListItem(name="Eggs", done=True),
            ListItem(name="Milk"),
        ]),
        ShoppingList(name="Target"),
    ])
    save_lists(store, path)
    assert load_lists(path) == store
    # Atomic write leaves no temp file behind.
    assert not path.with_suffix(".yaml.tmp").exists()


def test_saved_yaml_is_plain_and_readable(tmp_path: Path):
    path = tmp_path / "lists.yaml"
    save_lists(ShoppingLists(lists=[ShoppingList(name="Kroger", items=[ListItem(name="Bread")])]), path)
    raw = yaml.safe_load(path.read_text())
    assert raw == {"lists": [{"name": "Kroger", "items": [{"name": "Bread", "done": False}]}]}


def test_find_helpers_and_counts():
    sl = ShoppingList(name="G", items=[ListItem(name="A", done=True), ListItem(name="B")])
    store = ShoppingLists(lists=[sl])
    assert store.find("G") is sl
    assert store.find("Nope") is None
    assert sl.find("A").done is True
    assert sl.find("Zzz") is None
    assert sl.remaining == 1
    assert sl.bought == 1


def test_done_defaults_false_when_omitted_in_yaml(tmp_path: Path):
    path = tmp_path / "lists.yaml"
    path.write_text("lists:\n- name: Groceries\n  items:\n  - name: Milk\n")
    assert load_lists(path).lists[0].items[0].done is False
