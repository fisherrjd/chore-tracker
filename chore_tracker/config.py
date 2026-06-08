import yaml
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, field_validator, model_validator


class Member(BaseModel):
    name: str

    @property
    def topic(self) -> str:
        # ntfy topic derived from the member's name, e.g. "Jade" → <base>/jade
        return self.name.lower()


class Room(BaseModel):
    name: str
    tasks: list[str] = []


class AppConfig(BaseModel):
    start_date: date
    timezone: str = "America/Denver"
    ntfy_base_url: str = "https://ntfy.sh"
    dashboard_url: str = ""
    notify_times: list[str] = ["08:00"]
    members: list[Member] = []
    rooms: list[Room] = []

    @model_validator(mode="before")
    @classmethod
    def migrate_notify_time(cls, data):
        # Back-compat: older configs had a single `notify_time` string.
        if isinstance(data, dict) and "notify_time" in data and "notify_times" not in data:
            data = {**data, "notify_times": [data["notify_time"]]}
        return data

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v

    @field_validator("notify_times", mode="before")
    @classmethod
    def normalize_times(cls, v):
        """Accept a single "HH:MM" or a list; validate, zero-pad, dedupe, sort."""
        if isinstance(v, str):
            v = [v]
        normalized = []
        for raw in v:
            try:
                hh, mm = str(raw).strip().split(":")
                h, m = int(hh), int(mm)
            except ValueError:
                raise ValueError(f"notify time must be HH:MM, got {raw!r}")
            if not (0 <= h < 24 and 0 <= m < 60):
                raise ValueError(f"notify time out of range: {raw!r}")
            normalized.append(f"{h:02d}:{m:02d}")
        return sorted(set(normalized))

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def today(self) -> date:
        """Current calendar date in the configured timezone.

        Using this instead of ``date.today()`` keeps the notion of "today" tied
        to the household's wall clock rather than the server's (UTC) clock.
        """
        return datetime.now(self.tzinfo).date()


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig(start_date=date.today())
    with open(path) as f:
        data = yaml.safe_load(f)
    return AppConfig.model_validate(data)


def config_to_dict(config: AppConfig) -> dict:
    return {
        "start_date": config.start_date.isoformat(),
        "timezone": config.timezone,
        "ntfy_base_url": config.ntfy_base_url,
        "dashboard_url": config.dashboard_url,
        "notify_times": config.notify_times,
        "members": [m.model_dump() for m in config.members],
        "rooms": [r.model_dump() for r in config.rooms],
    }


def save_config(config: AppConfig, path: Path) -> None:
    data = config_to_dict(config)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    tmp.replace(path)
