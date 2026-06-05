import yaml
from datetime import date
from pathlib import Path
from pydantic import BaseModel, field_validator


class Member(BaseModel):
    name: str
    ntfy: str  # ntfy.sh topic, e.g. "jade" → ntfy.sh/jade


class Room(BaseModel):
    name: str
    tasks: list[str] = []


class AppConfig(BaseModel):
    start_date: date
    ntfy_base_url: str = "https://ntfy.sh"
    notify_time: str = "08:00"
    members: list[Member] = []
    rooms: list[Room] = []

    @field_validator("start_date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v


def load_config(path: Path) -> AppConfig:
    if not path.exists():
        return AppConfig(start_date=date.today())
    with open(path) as f:
        data = yaml.safe_load(f)
    return AppConfig.model_validate(data)


def save_config(config: AppConfig, path: Path) -> None:
    data = {
        "start_date": config.start_date.isoformat(),
        "ntfy_base_url": config.ntfy_base_url,
        "notify_time": config.notify_time,
        "members": [m.model_dump() for m in config.members],
        "rooms": [r.model_dump() for r in config.rooms],
    }
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    tmp.replace(path)
