"""Lớp dữ liệu dùng trong app (có cache theo phiên)."""
from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from core.scheduler import DEFAULT_FIXED, DEFAULT_SETTINGS
from core.store import AppsScriptStore, LocalStore, StoreError, latest, make_row, new_key

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CACHE_TTL = 120  # giây


def _secret(name: str, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # không có secrets.toml
        return default


@st.cache_resource
def _make_store(url: str | None, token: str | None, version: str = ""):
    """version nằm trong khoá cache → mỗi lần nâng phiên bản code sẽ tạo đối tượng mới
    (tránh dùng lại đối tượng của lớp cũ khi Streamlit Cloud cập nhật nóng)."""
    if url and token:
        return AppsScriptStore(url, token)
    return LocalStore(DATA_DIR)


def store():
    from core.version import __version__

    obj = _make_store(_secret("APPS_SCRIPT_URL"), _secret("APPS_SCRIPT_TOKEN"), __version__)
    if not hasattr(obj, "read_many"):  # phòng hờ: đối tượng cũ trong cache
        _make_store.clear()
        obj = _make_store(_secret("APPS_SCRIPT_URL"), _secret("APPS_SCRIPT_TOKEN"), __version__)
    return obj


def is_local() -> bool:
    return isinstance(store(), LocalStore)


TABLES = [
    "settings", "fixed", "events", "blocks", "tasks", "daily", "habits", "habit_log", "skills", "learn_log",
    "body", "look_items", "look_log", "photos", "wardrobe", "studio_tasks", "studio_budget", "studio_monthly", "goals",
]
LIGHT_TABLES = [t for t in TABLES if t != "photos"]  # ảnh nặng → chỉ tải khi mở trang Vẻ ngoài


def _cache() -> dict:
    return st.session_state.setdefault("_db_cache", {})


def _raw() -> dict:
    """Bộ nhớ đệm dòng thô theo bảng: {table: (thời điểm tải, [rows])}."""
    return st.session_state.setdefault("_db_raw", {})


def _prefetch(names: list[str]):
    raw = _raw()
    try:
        got = store().read_many(names)
    except StoreError as e:
        st.error(str(e))
        got = {n: raw.get(n, (0, []))[1] for n in names}
    t = time.time()
    for n in names:
        raw[n] = (t, got.get(n, []))


def table(name: str) -> list[dict]:
    raw = _raw()
    hit = raw.get(name)
    if not hit or time.time() - hit[0] >= CACHE_TTL:
        # tải gộp mọi bảng nhẹ đã hết hạn trong 1 lần gọi
        names = [n for n in LIGHT_TABLES if not raw.get(n) or time.time() - raw[n][0] >= CACHE_TTL]
        if name not in names:
            names.append(name)
        _prefetch(names)
    return latest(raw[name][1])


def invalidate(name: str | None = None):
    raw = _raw()
    if name is None:
        raw.clear()
    else:
        raw.pop(name, None)


def _append_local(name: str, rows: list[dict]):
    raw = _raw()
    if name in raw:
        raw[name] = (raw[name][0], raw[name][1] + rows)


def put(name: str, records: list[dict]) -> list[str]:
    """Ghi (thêm hoặc sửa) các bản ghi. Bản ghi không có 'key' sẽ được tạo key mới."""
    rows, keys = [], []
    for r in records:
        r = dict(r)
        k = r.pop("key", None) or new_key()
        rows.append(make_row(k, r))
        keys.append(k)
    store().append(name, rows)
    _append_local(name, rows)  # ghi xong cập nhật luôn bộ đệm, không phải đọc lại
    return keys


def delete(name: str, keys: list[str]):
    rows = [make_row(k, None, deleted=True) for k in keys]
    store().append(name, rows)
    _append_local(name, rows)


# ------------------------------------------------------------- cài đặt
def settings() -> dict:
    recs = {r["key"]: r for r in table("settings")}
    s = dict(DEFAULT_SETTINGS)
    s.update({k: v for k, v in recs.get("main", {}).items() if k != "key"})
    return s


def save_settings(values: dict):
    cur = settings()
    cur.update(values)
    cur["key"] = "main"
    put("settings", [cur])


def fixed_schedule() -> list[dict]:
    recs = table("fixed")
    if not recs and not any(r.get("key") == "seeded" for r in table("settings")):
        put("fixed", [dict(r) for r in DEFAULT_FIXED])
        put("settings", [{"key": "seeded", "fixed": True}])
        recs = table("fixed")
    return recs


# ------------------------------------------------------------- Google Calendar
def calendar_names() -> list[str]:
    s = settings()
    names = [s.get("pt_calendar", "PT") or "PT"]
    if s.get("read_primary", True):
        names.append("__primary__")
    return names


def filter_busy_events(evs: list[dict]) -> list[dict]:
    """Bỏ các khối do chính Self OS tạo trên lịch chính (đã có trong bảng blocks) để không tính trùng."""
    return [e for e in evs if not e.get("fromSelfOS") and not str(e.get("title", "")).startswith("[Self OS]")]


def pt_events(start: str, end: str) -> tuple[list[dict], str | None]:
    """Sự kiện bận từ Google Calendar (lịch PT + lịch chính nếu bật). Trả về (sự kiện, lỗi)."""
    names = calendar_names()
    ck = f"_gcal:{','.join(names)}:{start}:{end}"
    c = _cache()
    hit = c.get(ck)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1], None
    try:
        st_ = store()
        if hasattr(st_, "calendar_many"):
            try:
                evs = st_.calendar_many(start, end, names)
            except StoreError as e:
                if "unknown action" not in str(e):
                    raise
                evs = st_.calendar_events(start, end, calendar=names[0])  # Apps Script bản cũ
        else:
            evs = st_.calendar_events(start, end, calendar=names[0])
    except StoreError as e:
        return (hit[1] if hit else []), str(e)
    evs = filter_busy_events(evs)
    c[ck] = (time.time(), evs)
    return evs, None


def invalidate_calendar():
    c = _cache()
    for k in [k for k in c if k.startswith("_gcal:")]:
        c.pop(k)


# ------------------------------------------------------------- dữ liệu khởi tạo các phần 2–8
def _seed_once(flag: str, table_name: str, records: list[dict]):
    if not any(r.get("key") == f"seeded_{flag}" for r in table("settings")):
        if not table(table_name):
            put(table_name, records)
        put("settings", [{"key": f"seeded_{flag}", "done": True}])


def habits() -> list[dict]:
    from core.progress import DEFAULT_HABITS

    _seed_once("habits", "habits", [{**h, "active": True, "order": i} for i, h in enumerate(DEFAULT_HABITS)])
    return sorted(table("habits"), key=lambda h: (h.get("order", 99), h.get("name", "")))


def skills() -> list[dict]:
    from core.progress import DEFAULT_SKILLS

    _seed_once("skills", "skills", [{"name": n, "hours_week": 1.0, "resources": "", "practice": "", "order": i}
                                    for i, n in enumerate(DEFAULT_SKILLS)])
    return sorted(table("skills"), key=lambda s: (s.get("order", 99), s.get("name", "")))


def studio_tasks() -> list[dict]:
    from core.studio import STUDIO_CHECKLIST

    _seed_once("studio", "studio_tasks", [{"quarter": q, "area": a, "task": t, "done": False, "order": i}
                                          for i, (q, a, t) in enumerate(STUDIO_CHECKLIST)])
    return sorted(table("studio_tasks"), key=lambda r: (r.get("quarter", "Q9"), r.get("order", 999)))


def daily(day: str) -> dict:
    rec = next((r for r in table("daily") if r["key"] == day), None)
    return rec or {"key": day, "top3": [{"text": "", "done": False} for _ in range(3)], "review": ["", "", ""]}


def progress_data():
    from core.progress import Data

    return Data(
        daily=table("daily"), habits=habits(), habit_log=table("habit_log"), skills=skills(),
        learn_log=table("learn_log"), body=table("body"), look_log=table("look_log"),
        studio_tasks=studio_tasks(), goals=table("goals"),
    )
