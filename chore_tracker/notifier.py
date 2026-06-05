import httpx
from .config import AppConfig, Member
from .scheduler import get_assignment, get_day_index


async def send_notification(member: Member, room: str, tasks: list[str], ntfy_base_url: str) -> bool:
    url = f"{ntfy_base_url.rstrip('/')}/{member.ntfy}"
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
        return resp.is_success
    except Exception:
        return False


async def notify_today(config: AppConfig) -> dict[str, bool]:
    idx = get_day_index(config.start_date)
    room_names = [r.name for r in config.rooms]
    assignments = get_assignment(idx, room_names, [m.name for m in config.members])
    member_map = {m.name: m for m in config.members}
    room_map = {r.name: r for r in config.rooms}

    results = {}
    for name, room_name in assignments.items():
        if member := member_map.get(name):
            room = room_map.get(room_name)
            tasks = room.tasks if room else []
            results[name] = await send_notification(member, room_name, tasks, config.ntfy_base_url)
    return results
