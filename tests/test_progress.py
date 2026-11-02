from datetime import date

from core import progress as P
from core import studio as ST

T = date(2026, 11, 8)


def _data(**kw):
    base = dict(daily=[], habits=[], habit_log=[], skills=[], learn_log=[], body=[], look_log=[], studio_tasks=[], goals=[])
    base.update(kw)
    return P.Data(**base)


def test_streak_grace_today():
    done = {date(2026, 11, d) for d in (5, 6, 7)}
    assert P.streak(done, T) == 3            # hôm nay chưa làm → không phạt
    assert P.streak(done | {T}, T) == 4
    assert P.streak(done, T, grace_today=False) == 0
    assert P.best_streak(done | {date(2026, 11, 1)}) == 3


def test_level():
    assert P.level_of(0)["level"] == 1
    lv = P.level_of(350)
    assert lv["level"] == 3 and 0 < lv["pct"] < 1
    assert P.level_of(10**6)["next"] is None


def test_points_and_period_stats():
    d = _data(
        daily=[{"key": "2026-11-03", "top3": [{"text": "a", "done": True}, {"text": "b", "done": False}, {"text": "", "done": True}],
                "review": ["tốt", "", ""]}],
        habits=[{"key": "h1", "name": "Đọc", "per_week": 7, "active": True}],
        habit_log=[{"date": "2026-11-03", "habit": "h1", "done": True}, {"date": "2026-11-04", "habit": "h1", "done": False}],
        skills=[{"key": "s1", "name": "Tiếng Anh", "hours_week": 2}],
        learn_log=[{"date": "2026-11-03", "skill": "s1", "minutes": 60}],
        studio_tasks=[{"done": True, "done_date": "2026-11-04"}, {"done": False}],
    )
    # Top3: set 5 + 1 xong 10; review 10; habit 5; học 60' = 6; studio 15
    assert P.total_points(d) == 5 + 10 + 10 + 5 + 6 + 15
    s = P.period_stats(d, date(2026, 11, 2), T)
    assert s["top3_rate"] == 0.5 and s["top3_total"] == 2
    assert s["habit_done"] == 1 and round(s["habit_target"]) == 7
    assert s["learn_min"] == 60 and s["learn_target"] == 120
    assert s["studio_done"] == 1 and s["studio_progress"] == 0.5
    c = P.review_comments(s)
    assert c["tips"] and isinstance(c["strong"], list)


def test_badges():
    d = _data(habit_log=[{"date": f"2026-11-0{i}", "habit": "h", "done": True} for i in range(1, 8)])
    b = {x["name"]: x["earned"] for x in P.badges(d, T)}
    assert b["Lửa 7 ngày"] and not b["Lửa 30 ngày"]


def test_breakeven_and_kpis():
    assert ST.breakeven(30, 5, 2) == 10
    assert ST.breakeven(30, 2, 2) is None
    k = ST.monthly_kpis({"revenue": 100, "cost": 60, "clients": 20, "due_renew": 10, "renewed": 7, "new_clients": 4, "marketing": 8})
    assert k["profit"] == 40 and k["renew_rate"] == 0.7 and k["cost_per_client"] == 3 and k["cac"] == 2
    assert ST.monthly_kpis({})["renew_rate"] is None


def test_compress_photo_fits_sheet_cell():
    import io
    import random

    from PIL import Image

    from core.images import MAX_CHARS, b64_to_bytes, compress_to_b64

    random.seed(1)
    img = Image.new("RGB", (3000, 4000))
    img.putdata([(random.randrange(256), random.randrange(256), random.randrange(256)) for _ in range(3000 * 4000 // 50)] * 50)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    b64 = compress_to_b64(buf.getvalue())
    assert len(b64) <= MAX_CHARS
    assert Image.open(io.BytesIO(b64_to_bytes(b64))).size[1] <= 640
