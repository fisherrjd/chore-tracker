import logging

import httpx

from .config import AppConfig, Member
from .scheduler import get_assignment, get_day_index

log = logging.getLogger(__name__)


async def send_notification(member: Member, room: str, tasks: list[str], ntfy_base_url: str) -> bool:
    url = f"{ntfy_base_url.rstrip('/')}/{member.topic}"
    task_list = "\n".join(f"• {t}" for t in tasks) if tasks else "(no tasks defined)"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                content=f"{task_list}",
                headers={
                    "Title": f"Today: {room}",
                    "Priority": "default",
                    "Tags": "broom",
                },
            )
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
    idx = get_day_index(config.start_date, config.today)
    room_names = [r.name for r in config.rooms]
    assignments = get_assignment(idx, room_names, [m.name for m in config.members])
    member_map = {m.name: m for m in config.members}
    room_map = {r.name: r for r in config.rooms}

    log.info(
        "notify.run_start",
        extra={"trigger": trigger, "day_index": idx, "recipients": len(assignments)},
    )

    results = {}
    for name, room_name in assignments.items():
        if member := member_map.get(name):
            room = room_map.get(room_name)
            tasks = room.tasks if room else []
            results[name] = await send_notification(member, room_name, tasks, config.ntfy_base_url)

    failed = [n for n, ok in results.items() if not ok]
    log.info(
        "notify.run_complete",
        extra={"trigger": trigger, "sent": len(results) - len(failed), "failed": len(failed)},
    )
    return results
