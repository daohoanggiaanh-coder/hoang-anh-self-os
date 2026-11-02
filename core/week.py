"""Gom dữ liệu 1 tuần cho các trang."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core import db
from core import scheduler as S


@dataclass
class Week:
    days: list[date]
    items: dict
    analysis: dict
    settings: dict
    pt_error: str | None
    blocks: list[dict]
    tasks: list[dict]


def load_week(ref: date) -> Week:
    st_ = db.settings()
    days = S.week_days(ref)
    fixed = db.fixed_schedule()
    events = db.table("events")
    blocks = db.table("blocks")
    tasks = db.table("tasks")
    pt, err = db.pt_events(days[0].isoformat(), days[-1].isoformat())
    items = {d: S.day_items(d, fixed, pt, events, blocks, st_) for d in days}
    analysis = S.analyze_week(days, items, st_)
    return Week(days, items, analysis, st_, err, blocks, tasks)
