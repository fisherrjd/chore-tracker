"""Config model + persistence. Pins the ntfy-topic-from-name behavior."""
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

import chore_tracker.config as config_mod
from chore_tracker.config import AppConfig, Member, Room, load_config, save_config


def test_member_topic_is_lowercased_name():
    assert Member(name="Jade").topic == "jade"
    assert Member(name="Hannah").topic == "hannah"
    assert Member(name="Bob").topic == "bob"


def test_member_has_no_ntfy_field():
    # The per-member ntfy topic was removed; only `name` is a real field.
    assert Member(name="X").model_dump() == {"name": "X"}


def test_appconfig_defaults():
    cfg = AppConfig(start_date=date(2026, 1, 1))
    assert cfg.ntfy_base_url == "https://ntfy.sh"
    assert cfg.notify_time == "08:00"
    assert cfg.members == []
    assert cfg.rooms == []


def test_timezone_defaults_to_denver():
    assert AppConfig(start_date=date(2026, 1, 1)).timezone == "America/Denver"


def test_today_uses_configured_timezone(monkeypatch):
    """8pm on June 7 in Denver is already June 8 in UTC.

    ``today`` must report the local (Denver) date, not the server's UTC date.
    """

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 2026-06-08 02:00 UTC == 2026-06-07 20:00 America/Denver (MDT, UTC-6)
            instant = datetime(2026, 6, 8, 2, 0, tzinfo=timezone.utc)
            return instant.astimezone(tz)

    monkeypatch.setattr(config_mod, "datetime", FrozenDateTime)

    cfg = AppConfig(start_date=date(2026, 1, 1), timezone="America/Denver")
    assert cfg.today == date(2026, 6, 7)


def test_start_date_parsed_from_string():
    cfg = AppConfig.model_validate({"start_date": "2026-03-04"})
    assert cfg.start_date == date(2026, 3, 4)


def test_load_missing_file_returns_default(tmp_path: Path):
    cfg = load_config(tmp_path / "nope.yaml")
    assert cfg.start_date == date.today()
    assert cfg.members == []


def test_save_then_load_round_trips(tmp_path: Path):
    path = tmp_path / "config.yaml"
    cfg = AppConfig(
        start_date=date(2026, 1, 1),
        ntfy_base_url="https://ntfy.example.com/",
        notify_time="07:30",
        members=[Member(name="Alice"), Member(name="Bob")],
        rooms=[Room(name="Kitchen", tasks=["Dishes"])],
    )
    save_config(cfg, path)
    loaded = load_config(path)
    assert loaded == cfg


def test_saved_yaml_has_no_ntfy_key(tmp_path: Path):
    path = tmp_path / "config.yaml"
    save_config(
        AppConfig(start_date=date(2026, 1, 1), members=[Member(name="Alice")]),
        path,
    )
    raw = yaml.safe_load(path.read_text())
    assert raw["members"] == [{"name": "Alice"}]
    assert "ntfy" not in raw["members"][0]


def test_save_is_atomic_no_tmp_left_behind(tmp_path: Path):
    path = tmp_path / "config.yaml"
    save_config(AppConfig(start_date=date(2026, 1, 1)), path)
    assert path.exists()
    assert not (tmp_path / "config.yaml.tmp").exists()
