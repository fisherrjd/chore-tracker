import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .checks import get_done, set_done
from .config import AppConfig, Member, Room, load_config, save_config
from .notifier import notify_today
from .scheduler import get_assignment, get_day_index, get_schedule

BASE_DIR = Path(os.environ.get("CHORE_BASE", Path.cwd()))
CONFIG_PATH = Path(os.environ.get("CHORE_CONFIG", BASE_DIR / "config.yaml"))

scheduler = AsyncIOScheduler()


def _reschedule(config: AppConfig) -> None:
    scheduler.remove_all_jobs()
    h, m = map(int, config.notify_time.split(":"))
    scheduler.add_job(
        lambda: __import__("asyncio").ensure_future(notify_today(load_config(CONFIG_PATH))),
        "cron",
        hour=h,
        minute=m,
        id="daily_notify",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _reschedule(load_config(CONFIG_PATH))
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="Chore Tracker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def redirect(url: str, msg: str = "", kind: str = "success") -> RedirectResponse:
    if msg:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}msg={msg}&kind={kind}"
    return RedirectResponse(url, status_code=303)


# ── Schedule / home ──────────────────────────────────────────────────────────

@app.get("/")
async def home(request: Request, msg: str = "", kind: str = "success"):
    config = load_config(CONFIG_PATH)
    schedule = get_schedule(config, days=14)
    today_idx = get_day_index(config.start_date)
    n_rooms = len(config.rooms)
    n_members = len(config.members)
    half_cycle = (n_rooms // n_members) if n_members else 0
    room_map = {r.name: r for r in config.rooms}
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "schedule": schedule,
            "today_idx": today_idx,
            "half_cycle": half_cycle,
            "notify_time": config.notify_time,
            "room_map": room_map,
            "msg": msg,
            "kind": kind,
        },
    )


# ── Rooms ────────────────────────────────────────────────────────────────────

@app.get("/rooms")
async def rooms_page(request: Request, msg: str = "", kind: str = "success"):
    config = load_config(CONFIG_PATH)
    return templates.TemplateResponse(
        request=request, name="rooms.html",
        context={"rooms": config.rooms, "msg": msg, "kind": kind},
    )


@app.post("/rooms")
async def add_room(name: str = Form(...)):
    config = load_config(CONFIG_PATH)
    name = name.strip()
    if name and not any(r.name == name for r in config.rooms):
        config.rooms.append(Room(name=name))
        save_config(config, CONFIG_PATH)
        return redirect("/rooms", f"Added room '{name}'")
    return redirect("/rooms", "Room already exists or name is empty", "warning")


@app.post("/rooms/delete")
async def delete_room(name: str = Form(...)):
    config = load_config(CONFIG_PATH)
    config.rooms = [r for r in config.rooms if r.name != name]
    save_config(config, CONFIG_PATH)
    return redirect("/rooms", f"Removed room '{name}'")


@app.post("/rooms/{room_name}/tasks")
async def add_task(room_name: str, task: str = Form(...)):
    config = load_config(CONFIG_PATH)
    task = task.strip()
    for room in config.rooms:
        if room.name == room_name and task and task not in room.tasks:
            room.tasks.append(task)
            save_config(config, CONFIG_PATH)
            return redirect(f"/rooms#{room_name}", f"Added task to {room_name}")
    return redirect("/rooms", "Room not found or task already exists", "warning")


@app.post("/rooms/{room_name}/tasks/delete")
async def delete_task(room_name: str, task: str = Form(...)):
    config = load_config(CONFIG_PATH)
    for room in config.rooms:
        if room.name == room_name:
            room.tasks = [t for t in room.tasks if t != task]
            save_config(config, CONFIG_PATH)
            break
    return redirect("/rooms", f"Removed task from {room_name}")


# ── Members ───────────────────────────────────────────────────────────────────

@app.get("/members")
async def members_page(request: Request, msg: str = "", kind: str = "success"):
    config = load_config(CONFIG_PATH)
    return templates.TemplateResponse(
        request=request, name="members.html",
        context={
            "members": config.members,
            "ntfy_base_url": config.ntfy_base_url,
            "msg": msg,
            "kind": kind,
        },
    )


@app.post("/members")
async def add_member(name: str = Form(...)):
    config = load_config(CONFIG_PATH)
    name = name.strip()
    if name and not any(m.name == name for m in config.members):
        config.members.append(Member(name=name))
        save_config(config, CONFIG_PATH)
        return redirect("/members", f"Added '{name}'")
    return redirect("/members", "Member already exists or name is empty", "warning")


@app.post("/members/delete")
async def delete_member(name: str = Form(...)):
    config = load_config(CONFIG_PATH)
    config.members = [m for m in config.members if m.name != name]
    save_config(config, CONFIG_PATH)
    return redirect("/members", f"Removed '{name}'")


# ── Notifications ─────────────────────────────────────────────────────────────

@app.post("/notify/today")
async def send_today():
    config = load_config(CONFIG_PATH)
    results = await notify_today(config)
    if not results:
        return redirect("/", "No assignments to notify (check rooms and members)", "warning")
    sent = [n for n, ok in results.items() if ok]
    failed = [n for n, ok in results.items() if not ok]
    parts = []
    if sent:
        parts.append(f"Sent to: {', '.join(sent)}")
    if failed:
        parts.append(f"Failed: {', '.join(failed)}")
    return redirect("/", " | ".join(parts), "success" if not failed else "warning")


# ── Daily checklist ───────────────────────────────────────────────────────────

def _todays_room(config: AppConfig, member: str) -> str | None:
    idx = get_day_index(config.start_date)
    assignments = get_assignment(
        idx, [r.name for r in config.rooms], [m.name for m in config.members]
    )
    return assignments.get(member)


@app.get("/checklist/{member}")
async def checklist(request: Request, member: str, msg: str = "", kind: str = "success"):
    config = load_config(CONFIG_PATH)
    if not any(m.name == member for m in config.members):
        return redirect("/", f"Unknown member '{member}'", "warning")
    idx = get_day_index(config.start_date)
    room_name = _todays_room(config, member)
    room = next((r for r in config.rooms if r.name == room_name), None)
    tasks = room.tasks if room else []
    return templates.TemplateResponse(
        request=request, name="checklist.html",
        context={
            "member": member,
            "room_name": room_name,
            "tasks": tasks,
            "done": get_done(idx, member),
            "msg": msg,
            "kind": kind,
        },
    )


@app.post("/checklist/{member}")
async def update_checklist(member: str, tasks: list[str] = Form(default=[])):
    config = load_config(CONFIG_PATH)
    if not any(m.name == member for m in config.members):
        return redirect("/", f"Unknown member '{member}'", "warning")
    idx = get_day_index(config.start_date)
    room = next((r for r in config.rooms if r.name == _todays_room(config, member)), None)
    valid = set(room.tasks) if room else set()
    # Only record tasks that actually belong to today's assigned room.
    set_done(idx, member, [t for t in tasks if t in valid])
    return redirect(f"/checklist/{member}")


# ── JSON API ──────────────────────────────────────────────────────────────────

@app.get("/api/schedule")
async def api_schedule():
    config = load_config(CONFIG_PATH)
    schedule = get_schedule(config, days=14)
    return [
        {"date": str(day["date"]), "assignments": day["assignments"]}
        for day in schedule
    ]
