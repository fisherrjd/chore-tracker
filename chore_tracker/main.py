import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .checks import get_done, set_done
from .config import AppConfig, FullClean, Member, Room, config_to_dict, load_config, save_config
from .lists import ListItem, ShoppingList, load_lists, save_lists
from . import photos
from .logging_config import configure_logging
from .notifier import notify_disabled, notify_today
from .scheduler import get_day_index, get_full_clean, get_schedule, todays_rooms

BASE_DIR = Path(os.environ.get("CHORE_BASE", Path.cwd()))
CONFIG_PATH = Path(os.environ.get("CHORE_CONFIG", BASE_DIR / "config.yaml"))
DIST = BASE_DIR / "frontend" / "dist"
# Shopping lists live beside the config by default so they share its durable mount.
LISTS_PATH = Path(os.environ.get("CHORE_LISTS", CONFIG_PATH.with_name("lists.yaml")))
# Item photos sit beside the lists file; the dir is created on first upload.
PHOTOS_DIR = Path(os.environ.get("CHORE_PHOTOS", LISTS_PATH.with_name("list-photos")))

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _daily_notify() -> None:
    await notify_today(load_config(CONFIG_PATH), trigger="scheduled")


def _reschedule(config: AppConfig) -> None:
    scheduler.remove_all_jobs()
    if notify_disabled():
        log.info("scheduler.disabled", extra={"reason": "CHORE_NOTIFY=off"})
        return
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
    if not notify_disabled():
        scheduler.start()
    yield
    if scheduler.running:
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
    tasks: list[str] | None = None
    rooms: dict[str, list[str]] | None = None

class AddListReq(BaseModel):
    name: str

class AddListItemReq(BaseModel):
    item: str

class SetListItemReq(BaseModel):
    item: str
    done: bool


# ── Internal helpers ──────────────────────────────────────────────────────────

def _member_rooms(config: AppConfig, member: str) -> list[Room]:
    """The member's rooms today (normal mode: one), in assignment order."""
    room_map = {r.name: r for r in config.rooms}
    return [room_map[n] for n in todays_rooms(config).get(member, []) if n in room_map]


def _rooms_json(config: AppConfig, idx: int, member: str) -> list[dict]:
    return [
        {"name": r.name, "tasks": r.tasks, "done": sorted(get_done(idx, r.name) & set(r.tasks))}
        for r in _member_rooms(config, member)
    ]


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


def _list_json(sl: ShoppingList) -> dict:
    return {
        "name": sl.name,
        "items": [
            {"name": i.name, "done": i.done, "image_url": f"/api/photos/{i.image}" if i.image else None}
            for i in sl.items
        ],
        "remaining": sl.remaining,
        "bought": sl.bought,
    }


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
    assignments = todays_rooms(config)
    done_map: dict[str, dict[str, int]] = {}
    for person, room_names in assignments.items():
        done = total = 0
        for name in room_names:
            room = room_map.get(name)
            tasks = set(room.tasks) if room else set()
            done += len(get_done(today_idx, name) & tasks)
            total += len(tasks)
        done_map[person] = {"done": done, "total": total}
    return {
        "schedule": [
            {"date": str(day["date"]), "assignments": day["assignments"]}
            for day in schedule
        ],
        "today_idx": today_idx,
        "half_cycle": half_cycle,
        "notify_times": config.notify_times,
        "done_map": done_map,
        "full_clean": config.full_clean_active,
        "full_clean_rooms": assignments if config.full_clean_active else {},
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


def _checklist_json(config: AppConfig, idx: int, member: str) -> dict:
    rooms = _rooms_json(config, idx, member)
    first = rooms[0] if rooms else None
    return {
        "member": member,
        "full_clean": config.full_clean_active,
        "room_name": first["name"] if first else None,
        "tasks": first["tasks"] if first else [],
        "done": first["done"] if first else [],
        "rooms": rooms,
    }


@app.get("/api/checklist/{member}")
async def api_checklist_get(member: str):
    config = load_config(CONFIG_PATH)
    if not any(m.name == member for m in config.members):
        raise HTTPException(status_code=404, detail=f"Unknown member '{member}'")
    idx = get_day_index(config.start_date, config.today)
    return _checklist_json(config, idx, member)


@app.post("/api/checklist/{member}")
async def api_checklist_post(member: str, req: UpdateChecklistReq):
    config = load_config(CONFIG_PATH)
    if not any(m.name == member for m in config.members):
        raise HTTPException(status_code=404, detail=f"Unknown member '{member}'")
    if req.tasks is None and req.rooms is None:
        raise HTTPException(status_code=422, detail="Send tasks or rooms")
    idx = get_day_index(config.start_date, config.today)
    mine = {r.name: r for r in _member_rooms(config, member)}
    wanted = dict(req.rooms or {})
    if req.tasks is not None and mine:
        wanted.setdefault(next(iter(mine)), req.tasks)
    for name, tasks in wanted.items():
        room = mine.get(name)
        if room is None:
            continue
        recorded = [t for t in tasks if t in set(room.tasks)]
        set_done(idx, name, recorded)
        log.info(
            "checklist.updated",
            extra={"member": member, "room": name, "done": len(recorded)},
        )
    out = _checklist_json(config, idx, member)
    return {k: out[k] for k in ("member", "full_clean", "done", "rooms")}


@app.post("/api/full-clean")
async def api_full_clean_start():
    config = load_config(CONFIG_PATH)
    if not config.rooms or not config.members:
        raise HTTPException(status_code=409, detail="Add rooms and members first")
    if config.full_clean_active:
        return {"active": True, "assignments": todays_rooms(config), "sent": [], "failed": []}
    idx = get_day_index(config.start_date, config.today)
    config.full_clean = FullClean(
        date=config.today,
        assignments=get_full_clean(idx, config.rooms, [m.name for m in config.members]),
    )
    save_config(config, CONFIG_PATH)
    log.info("full_clean.started", extra={"date": str(config.today)})
    results = await notify_today(config, trigger="full_clean")
    return {
        "active": True,
        "assignments": todays_rooms(config),
        "sent": [n for n, ok in results.items() if ok],
        "failed": [n for n, ok in results.items() if not ok],
    }


@app.delete("/api/full-clean")
async def api_full_clean_stop():
    config = load_config(CONFIG_PATH)
    config.full_clean = None
    save_config(config, CONFIG_PATH)
    log.info("full_clean.stopped")
    return {"active": False}


# ── Shopping lists ────────────────────────────────────────────────────────────

@app.get("/api/lists")
async def api_lists():
    return [_list_json(sl) for sl in load_lists(LISTS_PATH).lists]


@app.post("/api/lists", status_code=201)
async def api_add_list(req: AddListReq):
    store = load_lists(LISTS_PATH)
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=409, detail="List name is empty")
    if store.find(name) is not None:
        raise HTTPException(status_code=409, detail=f"List '{name}' already exists")
    store.lists.append(ShoppingList(name=name))
    save_lists(store, LISTS_PATH)
    log.info("list.added", extra={"list": name})
    return _list_json(store.lists[-1])


@app.delete("/api/lists/{list_name}")
async def api_delete_list(list_name: str):
    store = load_lists(LISTS_PATH)
    if store.find(list_name) is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    gone = [i.image for i in store.find(list_name).items if i.image]
    store.lists = [sl for sl in store.lists if sl.name != list_name]
    save_lists(store, LISTS_PATH)
    for name in gone:
        photos.remove(PHOTOS_DIR, name)
    log.info("list.deleted", extra={"list": list_name})
    return {"detail": f"Removed list '{list_name}'"}


@app.post("/api/lists/{list_name}/items", status_code=201)
async def api_add_list_item(list_name: str, req: AddListItemReq):
    store = load_lists(LISTS_PATH)
    slist = store.find(list_name)
    if slist is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    item = req.item.strip()
    if not item:
        raise HTTPException(status_code=409, detail="Item name is empty")
    existing = slist.find(item)
    if existing is not None and not existing.done:
        raise HTTPException(status_code=409, detail=f"'{item}' is already on {list_name}")
    if existing is not None:
        # Re-adding something already bought just puts it back on the list.
        existing.done = False
    else:
        slist.items.append(ListItem(name=item))
    save_lists(store, LISTS_PATH)
    log.info("list_item.added", extra={"list": list_name, "item": item})
    return _list_json(slist)


@app.put("/api/lists/{list_name}/items")
async def api_set_list_item(list_name: str, req: SetListItemReq):
    """Set (not flip) an item's bought state, so taps from two phones at once
    land on the same answer."""
    store = load_lists(LISTS_PATH)
    slist = store.find(list_name)
    entry = slist.find(req.item) if slist else None
    if entry is None:
        raise HTTPException(status_code=404, detail=f"'{req.item}' is not on {list_name}")
    entry.done = req.done
    save_lists(store, LISTS_PATH)
    log.info("list_item.toggled", extra={"list": list_name, "item": req.item, "done": req.done})
    return _list_json(slist)


# `:path` so an item like "1/2 gallon milk" still routes
@app.delete("/api/lists/{list_name}/items/{item:path}")
async def api_delete_list_item(list_name: str, item: str):
    store = load_lists(LISTS_PATH)
    slist = store.find(list_name)
    if slist is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    gone = [i.image for i in slist.items if i.name == item and i.image]
    slist.items = [i for i in slist.items if i.name != item]
    save_lists(store, LISTS_PATH)
    for name in gone:
        photos.remove(PHOTOS_DIR, name)
    log.info("list_item.deleted", extra={"list": list_name, "item": item})
    return _list_json(slist)


@app.post("/api/lists/{list_name}/clear")
async def api_clear_bought(list_name: str):
    store = load_lists(LISTS_PATH)
    slist = store.find(list_name)
    if slist is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    removed = slist.bought
    gone = [i.image for i in slist.items if i.done and i.image]
    slist.items = [i for i in slist.items if not i.done]
    save_lists(store, LISTS_PATH)
    for name in gone:
        photos.remove(PHOTOS_DIR, name)
    log.info("list.cleared", extra={"list": list_name, "removed": removed})
    return {**_list_json(slist), "removed": removed}


_PHOTO_TYPES = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}


@app.put("/api/lists/{list_name}/photo")
async def api_set_list_photo(list_name: str, item: str = Form(...), file: UploadFile = File(...)):
    store = load_lists(LISTS_PATH)
    slist = store.find(list_name)
    if slist is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    entry = slist.find(item)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"'{item}' is not on {list_name}")
    data = await file.read(photos.MAX_BYTES + 1)
    if len(data) > photos.MAX_BYTES:
        raise HTTPException(status_code=413, detail="Photo is too big (max 10 MB)")
    ext = photos.sniff(data)
    if ext is None:
        raise HTTPException(
            status_code=415, detail="That file isn't a photo. Use JPEG, PNG, WebP or GIF."
        )
    old = entry.image
    entry.image = photos.save(PHOTOS_DIR, data, ext)
    save_lists(store, LISTS_PATH)
    photos.remove(PHOTOS_DIR, old)
    log.info("list_item.photo_set", extra={"list": list_name, "item": item})
    return _list_json(slist)


@app.delete("/api/lists/{list_name}/photo/{item:path}")
async def api_remove_list_photo(list_name: str, item: str):
    store = load_lists(LISTS_PATH)
    slist = store.find(list_name)
    if slist is None:
        raise HTTPException(status_code=404, detail=f"List '{list_name}' not found")
    entry = slist.find(item)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"'{item}' is not on {list_name}")
    old = entry.image
    entry.image = None
    save_lists(store, LISTS_PATH)
    photos.remove(PHOTOS_DIR, old)
    log.info("list_item.photo_removed", extra={"list": list_name, "item": item})
    return _list_json(slist)


# `:path` so an encoded "..%2F" (decoded to "/") still lands here, not on the SPA catch-all
@app.get("/api/photos/{name:path}")
async def api_photo(name: str):
    path = PHOTOS_DIR / name
    if not photos.NAME_RE.fullmatch(name) or not path.is_file():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(
        path,
        media_type=_PHOTO_TYPES[name.rsplit(".", 1)[1]],
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


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
