"""Tính chuỗi ngày, điểm, cấp độ, huy hiệu, tổng kết tuần/tháng. Thuần Python → test được."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# ------------------------------------------------------------- mặc định (theo yêu cầu của anh)
DEFAULT_HABITS = [
    {"name": "Dậy lúc 5h", "icon": "🌅", "per_week": 7},
    {"name": "Đọc 20 trang", "icon": "📖", "per_week": 7},
    {"name": "Thiền / thở 10 phút", "icon": "🧘", "per_week": 7},
    {"name": "Không lướt mạng xã hội trước 9h", "icon": "📵", "per_week": 7},
    {"name": "Uống đủ nước", "icon": "💧", "per_week": 7},
    {"name": "Ngủ trước 23h", "icon": "🌙", "per_week": 7},
]
DEFAULT_SKILLS = [
    "Quản trị tài chính doanh nghiệp",
    "Marketing & quảng cáo Facebook",
    "Bán hàng & chốt khách",
    "Tuyển dụng & quản lý nhân sự",
    "Xây quy trình vận hành (SOP)",
    "Tiếng Anh",
    "Nói trước đám đông",
    "Chụp / quay video",
]

# ------------------------------------------------------------- điểm
POINTS = {
    "top3_done": 10,      # mỗi việc Top 3 hoàn thành
    "top3_set": 5,        # chọn Top 3 trong ngày
    "review": 10,         # viết tổng kết cuối ngày
    "habit": 5,           # mỗi thói quen hoàn thành
    "learn_10min": 1,     # mỗi 10 phút học
    "body_log": 5,        # cập nhật số đo
    "look_day": 3,        # hoàn thành checklist vẻ ngoài trong ngày
    "studio_task": 15,    # mỗi việc chuẩn bị studio hoàn thành
}
LEVELS = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 5200, 6600, 8200, 10000]
LEVEL_NAMES = ["Khởi động", "Kỷ luật", "Bền bỉ", "Vững vàng", "Bứt phá", "Chuyên nghiệp",
               "Bản lĩnh", "Dẫn dắt", "Tinh hoa", "Bậc thầy", "Huyền thoại", "Đế chế", "Sovereign"]


def level_of(points: int) -> dict:
    lv = 0
    for i, need in enumerate(LEVELS):
        if points >= need:
            lv = i
    cur = LEVELS[lv]
    nxt = LEVELS[lv + 1] if lv + 1 < len(LEVELS) else None
    pct = 1.0 if nxt is None else (points - cur) / (nxt - cur)
    return {"level": lv + 1, "name": LEVEL_NAMES[lv], "points": points, "next": nxt, "pct": round(pct, 3)}


# ------------------------------------------------------------- chuỗi ngày
def streak(done_dates: set[date], today: date, grace_today: bool = True) -> int:
    """Số ngày liên tiếp có làm, tính đến hôm nay.
    Nếu hôm nay chưa làm (grace_today) thì vẫn tính chuỗi đến hôm qua — không phạt khi ngày chưa hết."""
    d = today
    if d not in done_dates:
        if not grace_today:
            return 0
        d = today - timedelta(days=1)
    n = 0
    while d in done_dates:
        n += 1
        d -= timedelta(days=1)
    return n


def best_streak(done_dates: set[date]) -> int:
    best = cur = 0
    prev = None
    for d in sorted(done_dates):
        cur = cur + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best = max(best, cur)
        prev = d
    return best


def _d(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


# ------------------------------------------------------------- tổng hợp
@dataclass
class Data:
    daily: list[dict]          # {key=date, top3:[{text,done}], review:[...]}
    habits: list[dict]         # {key, name, per_week, active}
    habit_log: list[dict]      # {date, habit, done}
    skills: list[dict]         # {key, name, hours_week}
    learn_log: list[dict]      # {date, skill, minutes, note}
    body: list[dict]           # {date, weight, bodyfat, waist}
    look_log: list[dict]       # {date, done:[...], total}
    studio_tasks: list[dict]   # {done, done_date}
    goals: list[dict]          # {level, progress}


def habit_done_map(d: Data) -> dict[str, set[date]]:
    out: dict[str, set[date]] = {}
    for r in d.habit_log:
        if r.get("done"):
            dt = _d(r.get("date"))
            if dt:
                out.setdefault(r.get("habit"), set()).add(dt)
    return out


def total_points(d: Data) -> int:
    p = 0
    for r in d.daily:
        top = [t for t in (r.get("top3") or []) if str(t.get("text", "")).strip()]
        if top:
            p += POINTS["top3_set"]
        p += POINTS["top3_done"] * sum(1 for t in top if t.get("done"))
        if any(str(s).strip() for s in (r.get("review") or [])):
            p += POINTS["review"]
    p += POINTS["habit"] * sum(1 for r in d.habit_log if r.get("done"))
    p += POINTS["learn_10min"] * int(sum(float(r.get("minutes") or 0) for r in d.learn_log) // 10)
    p += POINTS["body_log"] * len(d.body)
    p += POINTS["look_day"] * sum(1 for r in d.look_log if r.get("total") and len(r.get("done") or []) >= r["total"])
    p += POINTS["studio_task"] * sum(1 for r in d.studio_tasks if r.get("done"))
    return p


def period_stats(d: Data, start: date, end: date) -> dict:
    """Thống kê trong [start, end] (tính cả 2 đầu)."""
    days = (end - start).days + 1
    inrange = lambda s: (x := _d(s)) is not None and start <= x <= end  # noqa: E731
    daily = [r for r in d.daily if inrange(r.get("key"))]
    top_total = top_done = reviews = days_with_top = 0
    for r in daily:
        top = [t for t in (r.get("top3") or []) if str(t.get("text", "")).strip()]
        if top:
            days_with_top += 1
        top_total += len(top)
        top_done += sum(1 for t in top if t.get("done"))
        if any(str(s).strip() for s in (r.get("review") or [])):
            reviews += 1
    active = [h for h in d.habits if h.get("active", True)]
    target = sum(min(7, int(h.get("per_week") or 7)) for h in active) * days / 7
    hdone = sum(1 for r in d.habit_log if r.get("done") and inrange(r.get("date")) and r.get("habit") in {h["key"] for h in active})
    per_habit = {}
    for h in active:
        n = sum(1 for r in d.habit_log if r.get("done") and r.get("habit") == h["key"] and inrange(r.get("date")))
        tgt = min(7, int(h.get("per_week") or 7)) * days / 7
        per_habit[h["name"]] = (n, tgt)
    learn = [r for r in d.learn_log if inrange(r.get("date"))]
    learn_min = sum(float(r.get("minutes") or 0) for r in learn)
    learn_target = sum(float(s.get("hours_week") or 0) for s in d.skills) * 60 * days / 7
    per_skill = {}
    for s in d.skills:
        m = sum(float(r.get("minutes") or 0) for r in learn if r.get("skill") == s["key"])
        per_skill[s["name"]] = (m, float(s.get("hours_week") or 0) * 60 * days / 7)
    studio_done = sum(1 for r in d.studio_tasks if r.get("done") and inrange(r.get("done_date")))
    studio_total = len(d.studio_tasks)
    studio_all_done = sum(1 for r in d.studio_tasks if r.get("done"))
    return {
        "days": days,
        "top3_rate": top_done / top_total if top_total else None,
        "top3_done": top_done, "top3_total": top_total, "days_with_top": days_with_top, "reviews": reviews,
        "habit_rate": hdone / target if target else None, "habit_done": hdone, "habit_target": target,
        "per_habit": per_habit,
        "learn_min": learn_min, "learn_target": learn_target, "per_skill": per_skill,
        "studio_done": studio_done, "studio_progress": studio_all_done / studio_total if studio_total else None,
        "body_logs": sum(1 for r in d.body if inrange(r.get("date"))),
    }


def review_comments(s: dict) -> dict:
    """Nhận xét dựa trên quy tắc (không phải AI đoán): điểm mạnh, điểm cần cải thiện, đề xuất tuần sau."""
    strong, weak, tips = [], [], []
    tr = s["top3_rate"]
    if tr is None or s["days_with_top"] < s["days"] * 0.5:
        weak.append(f"Mới có {s['days_with_top']}/{s['days']} ngày chọn Top 3.")
        tips.append("Đặt Top 3 ngay khi mở web buổi sáng (trước cữ Burpee 5h30 là đẹp).")
    elif tr >= 0.8:
        strong.append(f"Hoàn thành {tr:.0%} việc Top 3 — rất tốt.")
    elif tr >= 0.5:
        strong.append(f"Hoàn thành {tr:.0%} việc Top 3.")
        tips.append("Chọn Top 3 vừa sức hơn hoặc xếp việc khó nhất vào giờ tỉnh táo (10h–13h).")
    else:
        weak.append(f"Top 3 mới đạt {tr:.0%}.")
        tips.append("Giảm còn 1–2 việc thật quan trọng/ngày và nhận đề xuất xếp lịch cho chúng.")
    hr = s["habit_rate"]
    if hr is not None:
        if hr >= 0.8:
            strong.append(f"Thói quen đạt {hr:.0%} mục tiêu.")
        elif hr < 0.5:
            weak.append(f"Thói quen chỉ đạt {hr:.0%} mục tiêu.")
        worst = sorted(((n / t if t else 1, name) for name, (n, t) in s["per_habit"].items()))[:1]
        if worst and worst[0][0] < 0.5:
            tips.append(f"Tập trung lại 1 thói quen yếu nhất: “{worst[0][1]}” — gắn nó vào việc đã cố định (VD ngay sau cữ Burpee).")
    if s["learn_target"] > 0:
        lr = s["learn_min"] / s["learn_target"]
        if lr >= 0.9:
            strong.append(f"Học {s['learn_min'] / 60:.1f}/{s['learn_target'] / 60:.1f} giờ mục tiêu.")
        else:
            weak.append(f"Học {s['learn_min'] / 60:.1f}/{s['learn_target'] / 60:.1f} giờ mục tiêu ({lr:.0%}).")
            lag = [name for name, (m, t) in s["per_skill"].items() if t and m / t < 0.5]
            if lag:
                tips.append("Bấm “Tạo đề xuất” có giờ học để web tự chèn: " + ", ".join(lag[:3]) + ".")
            if lr < 0.4:
                tips.append("Mục tiêu giờ học có thể đang quá cao so với lịch PT — cân nhắc giảm ở trang Kỹ năng.")
    if s["reviews"] >= s["days"] * 0.7:
        strong.append(f"Viết tổng kết {s['reviews']}/{s['days']} ngày.")
    else:
        tips.append("Dành 3 phút cuối ngày ghi 3 câu tổng kết — đó là dữ liệu để tuần sau tốt hơn.")
    if s["studio_done"]:
        strong.append(f"Hoàn thành {s['studio_done']} việc chuẩn bị studio.")
    elif s["studio_progress"] is not None and s["studio_progress"] < 1:
        tips.append("Chọn 1 việc chuẩn bị studio đưa vào Top 3 tuần sau.")
    return {"strong": strong, "weak": weak, "tips": tips[:5]}


def badges(d: Data, today: date) -> list[dict]:
    hm = habit_done_map(d)
    best_h = max((best_streak(v) for v in hm.values()), default=0)
    learn_h = sum(float(r.get("minutes") or 0) for r in d.learn_log) / 60
    top_done = sum(1 for r in d.daily for t in (r.get("top3") or []) if t.get("done"))
    reviews = sum(1 for r in d.daily if any(str(x).strip() for x in (r.get("review") or [])))
    studio = sum(1 for r in d.studio_tasks if r.get("done"))
    defs = [
        ("🔥", "Lửa 7 ngày", "Giữ 1 thói quen 7 ngày liền", best_h >= 7),
        ("🔥", "Lửa 30 ngày", "Giữ 1 thói quen 30 ngày liền", best_h >= 30),
        ("🎯", "Top 3 × 10", "Hoàn thành 10 việc Top 3", top_done >= 10),
        ("🎯", "Top 3 × 100", "Hoàn thành 100 việc Top 3", top_done >= 100),
        ("📚", "10 giờ học", "Tích luỹ 10 giờ học kỹ năng", learn_h >= 10),
        ("📚", "100 giờ học", "Tích luỹ 100 giờ học kỹ năng", learn_h >= 100),
        ("✍️", "Người tự soi", "Viết 7 bản tổng kết cuối ngày", reviews >= 7),
        ("📏", "Có số liệu", "Cập nhật số đo cơ thể 4 lần", len(d.body) >= 4),
        ("🏗️", "Viên gạch đầu", "Hoàn thành việc chuẩn bị studio đầu tiên", studio >= 1),
        ("🏛️", "Nền móng", "Hoàn thành 20 việc chuẩn bị studio", studio >= 20),
    ]
    return [{"icon": i, "name": n, "desc": de, "earned": ok} for i, n, de, ok in defs]
