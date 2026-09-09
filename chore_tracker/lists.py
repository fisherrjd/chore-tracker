"""Household shopping lists — durable, shared, and kept apart from config.

Lists (e.g. "Groceries", "Costco", "Target") live in their own YAML file
(``lists.yaml`` beside the config by default, or wherever ``CHORE_LISTS``
points) so day-to-day shopping churn never rewrites ``config.yaml``. Unlike the
daily checklist this state persists across restarts: an item stays on its list
until someone removes it or clears the bought ones.
"""
from pathlib import Path

import yaml
from pydantic import BaseModel

DEFAULT_LIST = "Groceries"


class ListItem(BaseModel):
    name: str
    done: bool = False


class ShoppingList(BaseModel):
    name: str
    items: list[ListItem] = []

    def find(self, item_name: str) -> ListItem | None:
        return next((i for i in self.items if i.name == item_name), None)

    @property
    def remaining(self) -> int:
        return sum(1 for i in self.items if not i.done)

    @property
    def bought(self) -> int:
        return sum(1 for i in self.items if i.done)


class ShoppingLists(BaseModel):
    lists: list[ShoppingList] = []

    def find(self, list_name: str) -> ShoppingList | None:
        return next((sl for sl in self.lists if sl.name == list_name), None)


def load_lists(path: Path) -> ShoppingLists:
    """Load lists from disk. A missing file seeds one empty default list so the
    page has somewhere to add items on first visit; an existing-but-empty file
    means the household removed every list, and stays empty."""
    if not path.exists():
        return ShoppingLists(lists=[ShoppingList(name=DEFAULT_LIST)])
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return ShoppingLists.model_validate(data)


def save_lists(store: ShoppingLists, path: Path) -> None:
    data = store.model_dump()
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    tmp.replace(path)
