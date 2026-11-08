import logging
import os
from urllib.parse import quote

import httpx2

from .config import AppConfig, Member
from .scheduler import get_day_index, todays_rooms

log = logging.getLogger(__name__)


def notify_disabled() -> bool:
    """True when CHORE_NOTIFY=off: nothing is scheduled and nothing is POSTed."""
    return os.environ.get("CHORE_NOTIFY", "").strip().lower() == "off"


async def send_notification(
    member: Member,
    room: str,
    tasks: list[str],
    ntfy_base_url: str,
    dashboard_url: str = "",
    *,
    title: str | None = None,
    body: str | None = None,
) -> bool:
    url = f"{ntfy_base_url.rstrip('/')}/{member.topic}"
    task_list = body or ("\n".join(f"• {t}" for t in tasks) if tasks else "(no tasks defined)")
    headers = {
        "Title": title or f"Today: {room}",
        "Priority": "default",
        "Tags": "broom",
    }
    if dashboard_url:
        # Tapping the notification opens this member's checklist directly.
        headers["Click"] = f"{dashboard_url.rstrip('/')}/checklist/{quote(member.name)}"
    try:
        async with httpx2.AsyncClient(timeout=10) as client:
            resp = await client.post(url, content=f"{task_list}", headers=headers)
        ok = resp.is_success
        log.info(
            "notify.sent",
            extra={"member": member.name, "room": room, "status": resp.status_code, "ok": ok},
        )
        return ok
    except Exception:
        # Previously swallowed silently — log it so failures are traceable.
        log.exception(
            "notify.send_failed", extra={"member": member.name, "room": room, "url": url}
        )
        return False


async def notify_today(config: AppConfig, *, trigger: str = "manual") -> dict[str, bool]:
    if notify_disabled():
        log.info("notify.disabled", extra={"trigger": trigger})
        return {}
    idx = get_day_index(config.start_date, config.today)
    assignments = todays_rooms(config)
    member_map = {m.name: m for m in config.members}
    room_map = {r.name: r for r in config.rooms}

    log.info(
        "notify.run_start",
        extra={"trigger": trigger, "day_index": idx, "recipients": len(assignments)},
    )

    results = {}
    for name, room_names in assignments.items():
        member = member_map.get(name)
        if member is None or not room_names:
            continue
        if config.full_clean_active:
            body = "\n\n".join(
                "\n".join([n, *(f"• {t}" for t in room_map[n].tasks)])
                for n in room_names
                if n in room_map
            )
            results[name] = await send_notification(
                member,
                ", ".join(room_names),
                [],
                config.ntfy_base_url,
                config.dashboard_url,
                title=f"Full house clean: {len(room_names)} rooms",
                body=body,
            )
        else:
            room_name = room_names[0]
            room = room_map.get(room_name)
            tasks = room.tasks if room else []
            results[name] = await send_notification(
                member, room_name, tasks, config.ntfy_base_url, config.dashboard_url
            )

    failed = [n for n, ok in results.items() if not ok]
    log.info(
        "notify.run_complete",
        extra={"trigger": trigger, "sent": len(results) - len(failed), "failed": len(failed)},
    )
    return results
