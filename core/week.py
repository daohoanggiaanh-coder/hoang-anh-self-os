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


def skill_tasks(skills: list[dict], blocks: list[dict], learn_log: list[dict], days: list[date],
                session_min: int = 60) -> list[dict]:
    """Tạo các buổi học còn thiếu trong tuần để web tự chèn vào giờ trống.
    Còn thiếu = mục tiêu giờ/tuần − giờ đã học (nhật ký) − giờ đã nhận lịch (chưa học)."""
    lo, hi = days[0].isoformat(), days[-1].isoformat()
    out = []
    for sk in skills:
        target = float(sk.get("hours_week") or 0) * 60
        if target <= 0:
            continue
        learned = sum(float(r.get("minutes") or 0) for r in learn_log
                      if r.get("skill") == sk["key"] and lo <= str(r.get("date", ""))[:10] <= hi)
        planned = sum(S.to_min(b["end"]) - S.to_min(b["start"]) for b in blocks
                      if str(b.get("task_key", "")).startswith(f"skill:{sk['key']}:") and lo <= b.get("date", "") <= hi
                      and not b.get("learned"))
        remain = target - learned - planned
        i = 0
        while remain >= 15:
            dur = int(min(session_min, remain) // 15 * 15)
            out.append({"key": f"skill:{sk['key']}:{lo}:{i}", "title": f"Học: {sk['name']}", "kind": "Học",
                        "minutes": dur, "status": "Chờ xếp"})
            remain -= dur
            i += 1
    return out


def load_week(ref: date) -> Week:
    st_ = db.settings()
    st_["_rules"] = db.cal_rules()
    days = S.week_days(ref)
    fixed = db.fixed_schedule()
    events = db.table("events")
    blocks = db.table("blocks")
    tasks = db.table("tasks")
    pt, err = db.pt_events(days[0].isoformat(), days[-1].isoformat())
    items = {d: S.day_items(d, fixed, pt, events, blocks, st_) for d in days}
    analysis = S.analyze_week(days, items, st_)
    return Week(days, items, analysis, st_, err, blocks, tasks)
