"""Notifier: URL building from base + name-topic, and result mapping."""
import asyncio
from datetime import date

import pytest

from chore_tracker import notifier
from chore_tracker.config import AppConfig, Member, Room


class _FakeResp:
    def __init__(self, status: int):
        self.status_code = status

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class _FakeClient:
    """Records POSTs; behavior controlled by class-level knobs."""

    calls: list[dict] = []
    status: int = 200
    raise_exc: bool = False

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, content=None, headers=None):
        if type(self).raise_exc:
            raise RuntimeError("network down")
        type(self).calls.append({"url": url, "content": content, "headers": headers})
        return _FakeResp(type(self).status)


@pytest.fixture
def fake_http(monkeypatch):
    _FakeClient.calls = []
    _FakeClient.status = 200
    _FakeClient.raise_exc = False
    monkeypatch.setattr(notifier.httpx, "AsyncClient", _FakeClient)
    return _FakeClient


def test_send_notification_builds_url_from_base_and_topic(fake_http):
    member = Member(name="Jade")
    ok = asyncio.run(
        notifier.send_notification(member, "Kitchen", ["Dishes"], "https://ntfy.example.com")
    )
    assert ok is True
    call = fake_http.calls[0]
    assert call["url"] == "https://ntfy.example.com/jade"
    assert call["headers"]["Title"] == "Today: Kitchen"
    assert "Dishes" in call["content"]


def test_send_notification_strips_trailing_slash_on_base(fake_http):
    asyncio.run(
        notifier.send_notification(Member(name="Bob"), "Bath", ["Toilet"], "https://ntfy.example.com/")
    )
    assert fake_http.calls[0]["url"] == "https://ntfy.example.com/bob"


def test_send_notification_handles_empty_tasks(fake_http):
    asyncio.run(notifier.send_notification(Member(name="A"), "Den", [], "https://n"))
    assert "no tasks defined" in fake_http.calls[0]["content"]


def test_send_notification_non_2xx_returns_false(fake_http):
    fake_http.status = 500
    ok = asyncio.run(notifier.send_notification(Member(name="A"), "Den", ["x"], "https://n"))
    assert ok is False


def test_send_notification_swallows_exceptions(fake_http):
    fake_http.raise_exc = True
    ok = asyncio.run(notifier.send_notification(Member(name="A"), "Den", ["x"], "https://n"))
    assert ok is False


def _config_today():
    return AppConfig(
        start_date=date.today(),
        ntfy_base_url="https://ntfy.example.com",
        members=[Member(name="Alice"), Member(name="Bob")],
        rooms=[
            Room(name="Kitchen", tasks=["Dishes"]),
            Room(name="Bath", tasks=["Toilet"]),
        ],
    )


def test_notify_today_sends_to_each_assigned_member(fake_http):
    results = asyncio.run(notifier.notify_today(_config_today()))
    assert set(results) == {"Alice", "Bob"}
    assert all(results.values())
    # Each member got exactly one notification at base/<name>.
    urls = sorted(c["url"] for c in fake_http.calls)
    assert urls == ["https://ntfy.example.com/alice", "https://ntfy.example.com/bob"]


def test_notify_today_no_members_or_rooms_returns_empty(fake_http):
    cfg = AppConfig(start_date=date.today())
    assert asyncio.run(notifier.notify_today(cfg)) == {}
    assert fake_http.calls == []
