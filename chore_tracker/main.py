import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .checks import get_done, set_done
from .config import AppConfig, Member, Room, config_to_dict, load_config, save_config
from .logging_config import configure_logging
from .notifier import notify_today
from .scheduler import get_assignment, get_day_index, get_schedule

BASE_DIR = Path(os.environ.get("CHORE_BASE", Path.cwd()))
CONFIG_PATH = Path(os.environ.get("CHORE_CONFIG", BASE_DIR / "config.yaml"))
DIST = BASE_DIR / "frontend" / "dist"

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _daily_notify() -> None:
    await notify_today(load_config(CONFIG_PATH), trigger="scheduled")


def _reschedule(config: AppConfig) -> None:
    scheduler.remove_all_jobs()
    for t in config.notify_times:
        h, m = map(int, t.split(":"))
        scheduler.add_job(
            _daily_notify,
            "cron",
            hour=h,
            minute=m,
            timezone=config.tzinfo,
            id=f"daily_notify_{h:02d}{m:02d}",
        )
    log.info(
        "scheduler.jobs_scheduled",
        extra={"times": ",".join(config.notify_times) or "(none)", "timezone": config.timezone},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("app.startup")
    _reschedule(load_config(CONFIG_PATH))
    scheduler.start()
    yield
    scheduler.shutdown()
    log.info("app.shutdown")


app = FastAPI(title="Chore Tracker", lifespan=lifespan)

# Serve built frontend assets; absent during dev/tests — skip gracefully.
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


# ── Request models ────────────────────────────────────────────────────────────

class AddRoomReq(BaseModel):
    name: str

class AddTaskReq(BaseModel):
    task: str

class AddMemberReq(BaseModel):
    name: str

class AddNotifyTimeReq(BaseModel):
    time: str

class UpdateChecklistReq(BaseModel):
    tasks: list[str]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _todays_room(config: AppConfig, member: str) -> str | None:
    idx = get_day_index(config.start_date, config.today)
    assignments = get_assignment(
        idx, [r.name for r in config.rooms], [m.name for m in config.members]
    )
    return assignments.get(member)


def _save_notify_times(config: AppConfig, times: list[str]) -> AppConfig | None:
    try:
        updated = AppConfig.model_validate({**config_to_dict(config), "notify_times": times})
    except ValidationError:
        return None
    save_config(updated, CONFIG_PATH)
    _reschedule(updated)
    return updated


def _member_json(m: Member, ntfy_base_url: str) -> dict:
    topic = m.name.lower()
    return {"name": m.name, "topic": topic, "ntfy_url": f"{ntfy_base_url.rstrip('/')}/{topic}"}


# ── JSON API ──────────────────────────────────────────────────────────────────

@app.get("/api/home")
async def api_home():
    config = load_config(CONFIG_PATH)
    schedule = get_schedule(config, days=14)
    today_idx = get_day_index(config.start_date, config.today)
    n_rooms = len(config.rooms)
    n_members = len(config.members)
    half_cycle = (n_rooms // n_members) if n_members else 0
    room_map = {r.name: r for r in config.rooms}
    done_map: dict[str, dict[str, int]] = {}
    if schedule:
        for person, room_name in schedule[0]["assignments"].items():
            room = room_map.get(room_name)
            tasks = set(room.tasks) if room else set()
            done_map[person] = {
                "done": len(get_done(today_idx, person) & tasks),
                "total": len(tasks),
            }
    return {
        "schedule": [
            {"date": str(day["date"]), "assignments": day["assignments"]}
            for day in schedule
        ],
        "today_idx": today_idx,
        "half_cycle": half_cycle,
        "notify_times": config.notify_times,
        "done_map": done_map,
    }


@app.get("/api/schedule")
async def api_schedule():
    config = load_config(CONFIG_PATH)
    return [
        {"date": str(day["date"]), "assignments": day["assignments"]}
        for day in get_schedule(config, days=14)
    ]


@app.get("/api/rooms")
async def api_rooms():
    config = load_config(CONFIG_PATH)
    return [{"name": r.name, "tasks": r.tasks} for r in config.rooms]


@app.post("/api/rooms", status_code=201)
async def api_add_room(req: AddRoomReq):
    config = load_config(CONFIG_PATH)
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=409, detail="Room name is empty")
    if any(r.name == name for r in config.rooms):
        raise HTTPException(status_code=409, detail=f"Room '{name}' already exists")
    config.rooms.append(Room(name=name))
    save_config(config, CONFIG_PATH)
    log.info("room.added", extra={"room": name})
    return {"name": name, "tasks": []}


@app.delete("/api/rooms/{name}")
async def api_delete_room(name: str):
    config = load_config(CONFIG_PATH)
    if not any(r.name == name for r in config.rooms):
        raise HTTPException(status_code=404, detail=f"Room '{name}' not found")
    config.rooms = [r for r in config.rooms if r.name != name]
    save_config(config, CONFIG_PATH)
    log.info("room.deleted", extra={"room": name})
    return {"detail": f"Removed room '{name}'"}


@app.post("/api/rooms/{room_name}/tasks", status_code=201)
async def api_add_task(room_name: str, req: AddTaskReq):
    config = load_config(CONFIG_PATH)
    task = req.task.strip()
    room = next((r for r in config.rooms if r.name == room_name), None)
    if room is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_name}' not found")
    if not task:
        raise HTTPException(status_code=409, detail="Task name is empty")
    if task in room.tasks:
        raise HTTPException(status_code=409, detail=f"Task '{task}' already exists in '{room_name}'")
    room.tasks.append(task)
    save_config(config, CONFIG_PATH)
    log.info("task.added", extra={"room": room_name, "task": task})
    return {"task": task}


@app.delete("/api/rooms/{room_name}/tasks/{task}")
async def api_delete_task(room_name: str, task: str):
    config = load_config(CONFIG_PATH)
    room = next((r for r in config.rooms if r.name == room_name), None)
    if room is None:
        raise HTTPException(status_code=404, detail=f"Room '{room_name}' not found")
    room.tasks = [t for t in room.tasks if t != task]
    save_config(config, CONFIG_PATH)
    log.info("task.deleted", extra={"room": room_name, "task": task})
    return {"detail": f"Removed task '{task}' from '{room_name}'"}


@app.get("/api/members")
async def api_members():
    config = load_config(CONFIG_PATH)
    return {
        "members": [_member_json(m, config.ntfy_base_url) for m in config.members],
        "ntfy_base_url": config.ntfy_base_url,
    }


@app.post("/api/members", status_code=201)
async def api_add_member(req: AddMemberReq):
    config = load_config(CONFIG_PATH)
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=409, detail="Member name is empty")
    if any(m.name == name for m in config.members):
        raise HTTPException(status_code=409, detail=f"Member '{name}' already exists")
    config.members.append(Member(name=name))
    save_config(config, CONFIG_PATH)
    log.info("member.added", extra={"member": name})
    return _member_json(config.members[-1], config.ntfy_base_url)


@app.delete("/api/members/{name}")
async def api_delete_member(name: str):
    config = load_config(CONFIG_PATH)
    if not any(m.name == name for m in config.members):
        raise HTTPException(status_code=404, detail=f"Member '{name}' not found")
    config.members = [m for m in config.members if m.name != name]
    save_config(config, CONFIG_PATH)
    log.info("member.deleted", extra={"member": name})
    return {"detail": f"Removed member '{name}'"}


@app.get("/api/settings")
async def api_settings():
    config = load_config(CONFIG_PATH)
    return {"notify_times": config.notify_times, "timezone": config.timezone}


@app.post("/api/settings/notify-times", status_code=201)
async def api_add_notify_time(req: AddNotifyTimeReq):
    config = load_config(CONFIG_PATH)
    time = req.time.strip()
    updated = _save_notify_times(config, config.notify_times + [time])
    if updated is None:
        raise HTTPException(status_code=400, detail=f"Invalid time '{time}' — use HH:MM")
    log.info("notify_time.added", extra={"time": time})
    return {"notify_times": updated.notify_times}


@app.delete("/api/settings/notify-times/{time}")
async def api_delete_notify_time(time: str):
    config = load_config(CONFIG_PATH)
    remaining = [t for t in config.notify_times if t != time]
    updated = _save_notify_times(config, remaining)
    log.info("notify_time.deleted", extra={"time": time})
    return {"notify_times": updated.notify_times if updated else remaining}


@app.get("/api/checklist/{member}")
async def api_checklist_get(member: str):
    config = load_config(CONFIG_PATH)
    if not any(m.name == member for m in config.members):
        raise HTTPException(status_code=404, detail=f"Unknown member '{member}'")
    idx = get_day_index(config.start_date, config.today)
    room_name = _todays_room(config, member)
    room = next((r for r in config.rooms if r.name == room_name), None)
    tasks = room.tasks if room else []
    done = sorted(get_done(idx, member) & set(tasks))
    return {"member": member, "room_name": room_name, "tasks": tasks, "done": done}


@app.post("/api/checklist/{member}")
async def api_checklist_post(member: str, req: UpdateChecklistReq):
    config = load_config(CONFIG_PATH)
    if not any(m.name == member for m in config.members):
        raise HTTPException(status_code=404, detail=f"Unknown member '{member}'")
    idx = get_day_index(config.start_date, config.today)
    room = next((r for r in config.rooms if r.name == _todays_room(config, member)), None)
    valid = set(room.tasks) if room else set()
    recorded = [t for t in req.tasks if t in valid]
    set_done(idx, member, recorded)
    log.info(
        "checklist.updated",
        extra={"member": member, "room": room.name if room else None, "done": len(recorded)},
    )
    return {"member": member, "done": recorded}


@app.post("/api/notify/today")
async def api_notify_today():
    config = load_config(CONFIG_PATH)
    results = await notify_today(config)
    sent = [n for n, ok in results.items() if ok]
    failed = [n for n, ok in results.items() if not ok]
    return {"sent": sent, "failed": failed}


# ── SPA catch-all (registered last) ──────────────────────────────────────────

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"detail": "Frontend not built"}, status_code=404)
