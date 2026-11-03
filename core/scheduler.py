"""Bộ máy lịch: dựng lịch từng ngày, tìm giờ trống, đề xuất xếp khối, cảnh báo.

Thuần Python, không phụ thuộc Streamlit -> test được tự động.
Thời gian trong ngày tính bằng phút (0..1440).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta

DAY = 1440
WEEKDAY_NAMES = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
DAY_GROUPS = {
    "Hằng ngày": {0, 1, 2, 3, 4, 5, 6},
    "Thứ 2–Thứ 6": {0, 1, 2, 3, 4},
    "Thứ 2–Thứ 7": {0, 1, 2, 3, 4, 5},
    "Thứ 7–Chủ nhật": {5, 6},
    **{name: {i} for i, name in enumerate(WEEKDAY_NAMES)},
}
DAY_OPTIONS = list(DAY_GROUPS.keys())

# ------------------------------------------------------------- phân loại & màu
# kind: (tên hiển thị, biểu tượng, màu web, màu Google Calendar 1–11)
CATEGORIES = {
    "PT": ("Dạy PT · Khách riêng", "🏋️", "#D4A94F", "5"),  # Banana
    "PT_Atlas": ("Dạy PT · Atlas", "🔴", "#D0453A", "11"),  # Tomato — lịch lễ tân Atlas nhập
    "Atlas": ("Quản lý Atlas", "🏢", "#4F7FBF", "9"),  # Blueberry
    "Công việc": ("Công việc khác", "💼", "#3E9A9A", "7"),  # Peacock
    "Di chuyển": ("Di chuyển", "🛵", "#6E6A62", "8"),
    "Khó": ("Việc tập trung", "🎯", "#B65FA6", "4"),  # Flamingo
    "Học": ("Học kỹ năng", "📚", "#5FA36F", "10"),     # Basil
    "Nhẹ": ("Việc nhẹ", "✉️", "#8C877C", "8"),         # Graphite
    "Tập": ("Tự tập", "💪", "#D9773B", "6"),           # Tangerine
    "Burpee": ("Burpee", "🐶", "#9C6B3E", "4"),
    "Gia đình": ("Gia đình / riêng", "🏠", "#8A6BB8", "3"),  # Grape
    "Ngủ": ("Ngủ", "🌙", "#3F4D72", "1"),
    "Khác": ("Khác", "•", "#7A756B", "1"),
}
PT_KINDS = {"PT", "PT_Atlas"}
TRAVEL_KINDS = {"PT", "PT_Atlas", "Atlas"}  # loại việc phải đi lại (cộng giờ di chuyển trước/sau)
GCAL_COLOR_NAMES = {"1": "Oải hương", "2": "Xanh lá nhạt", "3": "Nho", "4": "Hồng hạc", "5": "Vàng chuối", "6": "Cam",
                    "7": "Xanh công", "8": "Xám", "9": "Xanh việt quất", "10": "Xanh húng", "11": "Đỏ cà chua"}

# Quy tắc phân loại sự kiện Google Calendar (từ trên xuống, khớp quy tắc nào trước thì lấy loại đó)
DEFAULT_RULES = [
    {"match": "Từ khoá", "value": "tự tập", "kind": "Tập", "order": 0},
    {"match": "Từ khoá", "value": "atlas", "kind": "Atlas", "order": 1},
    {"match": "Từ khoá", "value": "họp", "kind": "Công việc", "order": 2},
    {"match": "Từ khoá", "value": "gym", "kind": "PT", "order": 3},
    {"match": "Từ khoá", "value": "pt", "kind": "PT", "order": 4},
    {"match": "Màu Google", "value": "5", "kind": "PT", "order": 5},
    {"match": "Từ khoá", "value": "gia đình", "kind": "Gia đình", "order": 6},
]


def classify_event(ev: dict, rules: list[dict], pt_calendar: str = "PT") -> str:
    """Trả về kind cho 1 sự kiện Google Calendar."""
    if ev.get("kind_override") in CATEGORIES:
        return ev["kind_override"]
    if ev.get("cal") == pt_calendar:
        return "PT"
    title = str(ev.get("title", "")).lower()
    color = str(ev.get("color") or "")
    for r in sorted(rules, key=lambda r: r.get("order", 99)):
        val = str(r.get("value", "")).strip().lower()
        if not val or r.get("kind") not in CATEGORIES:
            continue
        if r.get("match") == "Màu Google" and color == val:
            return r["kind"]
        if r.get("match", "Từ khoá") == "Từ khoá" and val in title:
            return r["kind"]
    if ev.get("cal") is None:  # dữ liệu cũ chỉ đọc lịch PT
        return "PT"
    return "Khác"


FIXED_KINDS = ["Ngủ", "Burpee", "Gia đình", "Atlas", "Công việc", "Tập", "Khác"]
TASK_KINDS = ["Khó", "Học", "Nhẹ", "Tập", "Atlas"]
TASK_KIND_HELP = {
    "Khó": "việc cần tập trung (kế hoạch, tài chính, nội dung...) → giờ tỉnh táo",
    "Học": "học kỹ năng → giờ tỉnh táo",
    "Nhẹ": "việc nhẹ (tin nhắn, dọn dẹp, việc vặt) → giờ hay mệt",
    "Tập": "tự tập → giờ bình thường, tránh giờ mệt",
    "Atlas": "việc quản lý Atlas (báo cáo, doanh thu, marketing) → giờ tỉnh táo",
}
WORK_KINDS = {"PT", "PT_Atlas", "Atlas", "Công việc", "Di chuyển", "Khó", "Nhẹ"}

# Điểm phù hợp năng lượng cho từng loại việc: (tỉnh táo, bình thường, mệt)
ENERGY_WEIGHT = {
    "Khó": (3.0, 1.5, 0.0),
    "Học": (3.0, 1.5, 0.0),
    "Nhẹ": (0.5, 2.0, 3.0),
    "Tập": (1.5, 2.0, 0.5),
    "Atlas": (3.0, 1.5, 0.5),
}

DEFAULT_SETTINGS = {
    "peak_start": "10:00",
    "peak_end": "13:00",
    "low_start": "13:00",
    "low_end": "15:00",
    "day_start": "05:00",
    "day_end": "23:00",
    "buffer_min": 15,
    "commute_min": 15,
    "min_slot": 30,
    "max_deep_min": 180,
    "sleep_target_min": 420,
    "work_week_limit_h": 55,
    "pt_calendar": "PT",
    "atlas_calendar": "pigngo2101@gmail.com",  # lịch chung Atlas do lễ tân nhập
    "atlas_color": "11",                        # chỉ lấy ca màu đỏ (Tomato) = ca của anh
    "read_primary": True,
    "write_gcal": True,
}

# Lịch cố định mặc định — lấy từ câu trả lời của anh Hoàng Anh (02/11/2026)
DEFAULT_FIXED = [
    {"days": "Hằng ngày", "start": "23:00", "end": "05:00", "title": "Ngủ", "kind": "Ngủ"},
    {"days": "Hằng ngày", "start": "05:30", "end": "06:00", "title": "Burpee – sáng", "kind": "Burpee"},
    {"days": "Hằng ngày", "start": "11:00", "end": "11:30", "title": "Burpee – trưa", "kind": "Burpee"},
    {"days": "Hằng ngày", "start": "16:00", "end": "16:30", "title": "Burpee – chiều", "kind": "Burpee"},
    {"days": "Hằng ngày", "start": "22:00", "end": "22:30", "title": "Burpee – tối", "kind": "Burpee"},
]


# ---------------------------------------------------------------- tiện ích giờ
def to_min(s: str) -> int:
    s = str(s).strip()
    if s in ("24:00", "24:0"):
        return DAY
    h, m = s.split(":")[:2]
    return int(h) * 60 + int(m)


def fmt(m: int) -> str:
    m = int(round(m))
    if m >= DAY:
        return "24:00"
    return f"{m // 60:02d}:{m % 60:02d}"


def fmt_dur(m: int) -> str:
    m = int(round(m))
    h, r = divmod(m, 60)
    if h and r:
        return f"{h}g{r:02d}"
    return f"{h} giờ" if h else f"{r} phút"


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_days(d: date) -> list[date]:
    s = week_start(d)
    return [s + timedelta(days=i) for i in range(7)]


def vn_date(d: date, with_year: bool = False) -> str:
    s = f"{WEEKDAY_NAMES[d.weekday()]}, {d.day:02d}/{d.month:02d}"
    return s + f"/{d.year}" if with_year else s


# ---------------------------------------------------------------- dựng lịch
@dataclass
class Item:
    start: int
    end: int
    title: str
    kind: str
    source: str  # fixed | pt | travel | event | block
    ref: str = ""

    @property
    def minutes(self) -> int:
        return self.end - self.start

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_s"], d["end_s"] = fmt(self.start), fmt(self.end)
        return d


def _parse_dt(s: str) -> datetime:
    s = str(s).replace("Z", "")
    if len(s) == 10:
        return datetime.fromisoformat(s)
    return datetime.fromisoformat(s[:16])  # bỏ múi giờ: Apps Script trả giờ VN


def fixed_items(fixed: list[dict], d: date) -> list[Item]:
    out: list[Item] = []
    wd = d.weekday()
    for r in fixed:
        days = DAY_GROUPS.get(r.get("days", ""), set())
        try:
            s, e = to_min(r["start"]), to_min(r["end"])
        except (KeyError, ValueError):
            continue
        title, kind = r.get("title") or r.get("kind", ""), r.get("kind", "Khác")
        if s == e:
            continue
        if e > s:
            if wd in days:
                out.append(Item(s, e, title, kind, "fixed", r.get("key", "")))
        else:  # qua nửa đêm: phần tối hôm nay + phần sáng hôm sau
            if wd in days:
                out.append(Item(s, DAY, title, kind, "fixed", r.get("key", "")))
            if (wd - 1) % 7 in days:
                out.append(Item(0, e, title, kind, "fixed", r.get("key", "")))
    return out


def pt_items(events: list[dict], d: date, commute: int, chain_gap: int | None = None,
             rules: list[dict] | None = None, pt_calendar: str = "PT") -> list[Item]:
    """Sự kiện Google Calendar → Item đã phân loại.
    Loại cần đi lại (PT, Atlas) được cộng thời gian di chuyển trước/sau mỗi chuỗi ca liền nhau."""
    if chain_gap is None:
        chain_gap = 2 * commute
    rules = DEFAULT_RULES if rules is None else rules
    day0 = datetime(d.year, d.month, d.day)
    sessions = []
    for ev in events:
        if ev.get("allDay"):
            continue
        try:
            s, e = _parse_dt(ev["start"]), _parse_dt(ev["end"])
        except (KeyError, ValueError):
            continue
        sm = (s - day0).total_seconds() / 60
        em = (e - day0).total_seconds() / 60
        if em <= 0 or sm >= DAY:
            continue
        kind = classify_event(ev, rules, pt_calendar)
        sessions.append((max(0, int(sm)), min(DAY, int(em)), ev.get("title") or "Sự kiện", ev.get("id", ""), kind))
    sessions.sort()
    out: list[Item] = []
    travel = [x for x in sessions if x[4] in TRAVEL_KINDS]
    for x in sessions:
        out.append(Item(x[0], x[1], x[2], x[4], "pt" if x[4] in PT_KINDS else "gcal", x[3]))
    prev_end = None
    for i, (s, e, _t, _r, _k) in enumerate(travel):
        if commute and (prev_end is None or s - prev_end > chain_gap):
            out.append(Item(max(0, s - commute), s, "Di chuyển", "Di chuyển", "travel"))
        nxt = travel[i + 1][0] if i + 1 < len(travel) else None
        if commute and (nxt is None or nxt - e > chain_gap):
            out.append(Item(e, min(DAY, e + commute), "Di chuyển", "Di chuyển", "travel"))
        prev_end = e
    return sorted(out, key=lambda it: (it.start, it.end))


def event_items(events: list[dict], d: date) -> list[Item]:
    ds = d.isoformat()
    out = []
    for r in events:
        if str(r.get("date", ""))[:10] != ds:
            continue
        try:
            s, e = to_min(r["start"]), to_min(r["end"])
        except (KeyError, ValueError):
            continue
        if e > s:
            out.append(Item(s, e, r.get("title", "Việc phát sinh"), r.get("kind", "Khác"), "event", r.get("key", "")))
    return out


def block_items(blocks: list[dict], d: date) -> list[Item]:
    ds = d.isoformat()
    out = []
    for r in blocks:
        if str(r.get("date", ""))[:10] != ds:
            continue
        try:
            s, e = to_min(r["start"]), to_min(r["end"])
        except (KeyError, ValueError):
            continue
        out.append(Item(s, e, r.get("title", ""), r.get("kind", "Khó"), "block", r.get("key", "")))
    return out


def day_items(d: date, fixed, pt_events, events, blocks, settings: dict) -> list[Item]:
    items = (
        fixed_items(fixed, d)
        + pt_items(pt_events, d, int(settings.get("commute_min", 15)), rules=settings.get("_rules"),
                   pt_calendar=settings.get("pt_calendar", "PT"))
        + event_items(events, d)
        + block_items(blocks, d)
    )
    return sorted(items, key=lambda it: (it.start, it.end))


# ---------------------------------------------------------------- giờ trống
def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for s, e in sorted(intervals):
        if e <= s:
            continue
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(a, b) for a, b in out]


def free_slots(busy: list[tuple[int, int]], window: tuple[int, int] = (0, DAY), min_len: int = 30) -> list[tuple[int, int]]:
    ws, we = window
    slots, cur = [], ws
    for s, e in merge([(max(ws, s), min(we, e)) for s, e in busy]):
        if s > cur and s - cur >= min_len:
            slots.append((cur, s))
        cur = max(cur, e)
    if we - cur >= min_len:
        slots.append((cur, we))
    return slots


def energy_label(s: int, e: int, settings: dict) -> str:
    ps, pe = to_min(settings["peak_start"]), to_min(settings["peak_end"])
    ls, le = to_min(settings["low_start"]), to_min(settings["low_end"])
    dur = max(1, e - s)
    peak = max(0, min(e, pe) - max(s, ps))
    low = max(0, min(e, le) - max(s, ls))
    if peak * 2 >= dur:
        return "Tỉnh táo"
    if low * 2 >= dur:
        return "Mệt"
    return "Bình thường"


def _score(kind: str, s: int, e: int, settings: dict) -> float:
    ps, pe = to_min(settings["peak_start"]), to_min(settings["peak_end"])
    ls, le = to_min(settings["low_start"]), to_min(settings["low_end"])
    wp, wn, wl = ENERGY_WEIGHT.get(kind, ENERGY_WEIGHT["Khó"])
    dur = e - s
    peak = max(0, min(e, pe) - max(s, ps))
    low = max(0, min(e, le) - max(s, ls))
    normal = dur - peak - low
    return (wp * peak + wn * normal + wl * low) / dur


@dataclass
class Proposal:
    task_key: str
    title: str
    kind: str
    date: str
    start: int
    end: int
    energy: str
    note: str = ""
    pid: str = field(default="")

    def __post_init__(self):
        if not self.pid:
            self.pid = f"{self.task_key}@{self.date}T{fmt(self.start)}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_s"], d["end_s"] = fmt(self.start), fmt(self.end)
        return d


def propose(
    days: list[date],
    items_by_day: dict[date, list[Item]],
    tasks: list[dict],
    settings: dict,
    now: datetime | None = None,
    step: int = 15,
) -> tuple[list[Proposal], list[dict]]:
    """Xếp các việc vào giờ trống (tham lam, ưu tiên việc khó trước).

    - Mỗi khối cách việc khác ít nhất `buffer_min` phút.
    - Việc Khó/Học ưu tiên giờ tỉnh táo; Nhẹ ưu tiên giờ mệt.
    - Giới hạn tổng việc Khó+Học mỗi ngày = max_deep_min.
    - Không xếp vào quá khứ.
    Trả về (đề xuất, việc chưa xếp được kèm lý do).
    """
    buf = int(settings.get("buffer_min", 15))
    window = (to_min(settings["day_start"]), to_min(settings["day_end"]))
    max_deep = int(settings.get("max_deep_min", 180))

    busy: dict[date, list[tuple[int, int]]] = {}
    deep_used: dict[date, int] = {}
    for d in days:
        its = items_by_day.get(d, [])
        busy[d] = [(it.start, it.end) for it in its]
        deep_used[d] = sum(it.minutes for it in its if it.source == "block" and it.kind in ("Khó", "Học"))

    def not_before(d: date) -> int:
        if now is None or d > now.date():
            return 0
        if d < now.date():
            return DAY
        return now.hour * 60 + now.minute

    order = {"Khó": 0, "Học": 1, "Tập": 2, "Nhẹ": 3}
    todo = sorted(
        tasks,
        key=lambda t: (0 if t.get("date") else 1, order.get(t.get("kind"), 9), -int(t.get("minutes") or 0)),
    )
    proposals: list[Proposal] = []
    unplaced: list[dict] = []
    for t in todo:
        dur = int(t.get("minutes") or 0)
        kind = t.get("kind") or "Khó"
        if dur <= 0:
            unplaced.append({**t, "reason": "Chưa nhập số phút"})
            continue
        cand_days = days
        if t.get("date"):
            cand_days = [d for d in days if d.isoformat() == str(t["date"])[:10]]
            if not cand_days:
                unplaced.append({**t, "reason": "Ngày mong muốn không nằm trong tuần này"})
                continue
        best = None  # (score, -day_idx, -start, d, s)
        deep_blocked = False
        for di, d in enumerate(cand_days):
            if kind in ("Khó", "Học") and deep_used[d] + dur > max_deep:
                deep_blocked = True
                continue
            padded = [(s - buf, e + buf) for s, e in busy[d]]
            lo = max(window[0], not_before(d))
            for fs, fe in free_slots(padded, (lo, window[1]), min_len=dur):
                s = -(-fs // step) * step  # làm tròn lên mốc 15'
                while s + dur <= fe:
                    sc = _score(kind, s, s + dur, settings)
                    key = (round(sc, 3), -di, -s)
                    if best is None or key > best[0]:
                        best = (key, d, s)
                    s += step
        if best is None:
            reason = "Không còn khoảng trống đủ dài trong tuần"
            if deep_blocked:
                reason += f" (hoặc đã chạm giới hạn {fmt_dur(max_deep)} việc khó/học mỗi ngày)"
            unplaced.append({**t, "reason": reason})
            continue
        _, d, s = best
        e = s + dur
        busy[d].append((s, e))
        if kind in ("Khó", "Học"):
            deep_used[d] += dur
        en = energy_label(s, e, settings)
        note = ""
        if kind in ("Khó", "Học") and en == "Mệt":
            note = "Chỉ còn giờ hay mệt — cân nhắc dời sang tuần sau"
        elif kind == "Nhẹ" and en == "Tỉnh táo":
            note = "Đang dùng giờ tỉnh táo cho việc nhẹ"
        proposals.append(Proposal(t.get("key", ""), t.get("title", ""), kind, d.isoformat(), s, e, en, note))
    proposals.sort(key=lambda p: (p.date, p.start))
    return proposals, unplaced


# ---------------------------------------------------------------- phân tích tuần
def analyze_week(days: list[date], items_by_day: dict[date, list[Item]], settings: dict) -> dict:
    window = (to_min(settings["day_start"]), to_min(settings["day_end"]))
    min_slot = int(settings.get("min_slot", 30))
    sleep_target = int(settings.get("sleep_target_min", 420))
    limit_min = int(float(settings.get("work_week_limit_h", 55)) * 60)

    per_day = []
    work_total = 0
    has_sleep = False
    for d in days:
        its = items_by_day.get(d, [])
        sleep = sum(it.minutes for it in its if it.kind == "Ngủ")
        has_sleep = has_sleep or sleep > 0
        work = sum(it.minutes for it in its if it.kind in WORK_KINDS)
        learn = sum(it.minutes for it in its if it.kind == "Học")
        pt = sum(it.minutes for it in its if it.kind in PT_KINDS)
        slots = free_slots([(it.start, it.end) for it in its], window, min_slot)
        free = sum(e - s for s, e in slots)
        work_total += work
        per_day.append({"date": d, "sleep": sleep, "work": work, "pt": pt, "learn": learn, "free": free, "slots": slots})

    warnings: list[str] = []
    clashes = []
    for p in per_day:
        its = [it for it in items_by_day.get(p["date"], []) if it.kind != "Ngủ"]
        for i, a in enumerate(its):
            for b in its[i + 1:]:
                if a.start < b.end and b.start < a.end:
                    clashes.append(f"{vn_date(p['date'])} {fmt(max(a.start, b.start))}: {a.title} ↔ {b.title}")
    if clashes:
        shown = "; ".join(clashes[:4]) + (f" (+{len(clashes) - 4} chỗ khác)" if len(clashes) > 4 else "")
        warnings.append("Trùng giờ: " + shown + ".")
    if not has_sleep:
        warnings.append("Chưa nhập giờ ngủ trong Lịch cố định — web không kiểm tra được thiếu ngủ.")
    else:
        short = [p for p in per_day if p["sleep"] < sleep_target]
        if short:
            avg = sum(p["sleep"] for p in short) / len(short)
            warnings.append(
                f"Thiếu ngủ: {len(short)}/7 ngày dưới {fmt_dur(sleep_target)} (trung bình {fmt_dur(avg)}). "
                "Khuyến nghị chung cho người trưởng thành là ≥ 7 giờ/đêm "
                "(đồng thuận AASM & Sleep Research Society, 2015) — mang tính tham khảo."
            )
    if work_total > limit_min:
        warnings.append(
            f"Tuần quá tải: {fmt_dur(work_total)} làm việc (ngưỡng anh đặt: {fmt_dur(limit_min)}). "
            "Mốc 55 giờ/tuần được WHO/ILO (2021) dùng khi đánh giá rủi ro sức khoẻ của làm việc kéo dài — tham khảo."
        )
    zero = [p for p in per_day if p["free"] < 60]
    if zero:
        warnings.append(
            "Ngày gần như kín lịch (< 1 giờ trống): " + ", ".join(vn_date(p["date"]) for p in zero) + "."
        )
    return {"per_day": per_day, "work_total": work_total, "warnings": warnings, "clashes": clashes}
