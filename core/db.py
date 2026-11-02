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
def _make_store(url: str | None, token: str | None):
    if url and token:
        return AppsScriptStore(url, token)
    return LocalStore(DATA_DIR)


def store():
    return _make_store(_secret("APPS_SCRIPT_URL"), _secret("APPS_SCRIPT_TOKEN"))


def is_local() -> bool:
    return isinstance(store(), LocalStore)


def _cache() -> dict:
    return st.session_state.setdefault("_db_cache", {})


def table(name: str) -> list[dict]:
    c = _cache()
    hit = c.get(name)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        recs = latest(store().read(name))
    except StoreError as e:
        st.error(str(e))
        recs = hit[1] if hit else []
    c[name] = (time.time(), recs)
    return recs


def invalidate(name: str | None = None):
    c = _cache()
    if name is None:
        c.clear()
    else:
        c.pop(name, None)


def put(name: str, records: list[dict]) -> list[str]:
    """Ghi (thêm hoặc sửa) các bản ghi. Bản ghi không có 'key' sẽ được tạo key mới."""
    rows, keys = [], []
    for r in records:
        r = dict(r)
        k = r.pop("key", None) or new_key()
        rows.append(make_row(k, r))
        keys.append(k)
    store().append(name, rows)
    invalidate(name)
    return keys


def delete(name: str, keys: list[str]):
    store().append(name, [make_row(k, None, deleted=True) for k in keys])
    invalidate(name)


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
def pt_events(start: str, end: str) -> tuple[list[dict], str | None]:
    """Trả về (sự kiện, lỗi). Cache theo phiên."""
    cal = settings().get("pt_calendar", "PT")
    ck = f"_gcal:{cal}:{start}:{end}"
    c = _cache()
    hit = c.get(ck)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1], None
    try:
        evs = store().calendar_events(start, end, calendar=cal)
    except StoreError as e:
        return (hit[1] if hit else []), str(e)
    c[ck] = (time.time(), evs)
    return evs, None


def invalidate_calendar():
    c = _cache()
    for k in [k for k in c if k.startswith("_gcal:")]:
        c.pop(k)
