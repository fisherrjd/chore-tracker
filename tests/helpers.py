"""Pure test helpers — no import-time side effects.

These read ``CHORE_CONFIG`` from the environment (set by conftest) lazily, so
the module is safe to import from any test without spawning a second temp dir.
"""
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

# Mirror AppConfig's default timezone so a default-config ``start_date`` lines up
# with the date the app computes via ``AppConfig.today`` (day_index 0).
DEFAULT_TZ = "America/Denver"


def config_path() -> Path:
    return Path(os.environ["CHORE_CONFIG"])


def write_config(data: dict) -> None:
    """Write a raw config dict to the temp config file the app reads."""
    config_path().write_text(yaml.dump(data, sort_keys=False))


def default_config(start: date | None = None) -> dict:
    """A known-good config: 2 members, 4 rooms (half cycle = 2).

    ``start_date`` defaults to *today* so ``get_day_index`` is 0 and today's
    assignment is deterministic: Alice -> Kitchen, Bob -> Bath.
    """
    today = datetime.now(ZoneInfo(DEFAULT_TZ)).date()
    return {
        "start_date": (start or today).isoformat(),
        "ntfy_base_url": "https://ntfy.example.com",
        "notify_times": ["08:00"],
        "members": [{"name": "Alice"}, {"name": "Bob"}],
        "rooms": [
            {"name": "Kitchen", "tasks": ["Dishes", "Sweep"]},
            {"name": "Bath", "tasks": ["Toilet"]},
            {"name": "Office", "tasks": []},
            {"name": "Den", "tasks": ["Vacuum"]},
        ],
    }
