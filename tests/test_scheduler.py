from datetime import date, datetime

from core import scheduler as S
from core.scheduler import DEFAULT_FIXED, DEFAULT_SETTINGS, Item

MON = date(2026, 11, 2)  # Thứ 2


def test_time_helpers():
    assert S.to_min("05:30") == 330
    assert S.fmt(330) == "05:30"
    assert S.fmt(1440) == "24:00"
    assert S.fmt_dur(90) == "1g30"
    assert S.week_start(date(2026, 11, 8)) == MON
    assert S.vn_date(MON) == "Thứ 2, 02/11"


def test_sleep_crosses_midnight():
    its = S.fixed_items(DEFAULT_FIXED, MON)
    sleep = sorted([i for i in its if i.kind == "Ngủ"], key=lambda i: i.start)
    assert [(i.start, i.end) for i in sleep] == [(0, 300), (1380, 1440)]
    assert sum(i.minutes for i in sleep) == 360  # 23h–5h = 6 tiếng


def test_day_groups():
    fixed = [{"days": "Thứ 2–Thứ 6", "start": "08:00", "end": "09:00", "title": "x", "kind": "Khác"}]
    assert S.fixed_items(fixed, MON)
    assert not S.fixed_items(fixed, date(2026, 11, 8))  # Chủ nhật


def test_free_slots_default_day():
    its = S.fixed_items(DEFAULT_FIXED, MON)
    slots = S.free_slots([(i.start, i.end) for i in its], (0, 1440), 30)
    got = [(S.fmt(a), S.fmt(b)) for a, b in slots]
    assert got == [
        ("05:00", "05:30"),
        ("06:00", "11:00"),
        ("11:30", "16:00"),
        ("16:30", "22:00"),
        ("22:30", "23:00"),
    ]


def test_pt_commute_chain():
    evs = [
        {"id": "a", "title": "PT A", "start": "2026-11-02T06:00", "end": "2026-11-02T07:00"},
        {"id": "b", "title": "PT B", "start": "2026-11-02T07:15", "end": "2026-11-02T08:15"},
        {"id": "c", "title": "PT C", "start": "2026-11-02T18:00", "end": "2026-11-02T19:00"},
        {"id": "d", "title": "Hôm khác", "start": "2026-11-03T06:00", "end": "2026-11-03T07:00"},
    ]
    its = S.pt_items(evs, MON, commute=15)
    got = [(S.fmt(i.start), S.fmt(i.end), i.kind) for i in its]
    assert got == [
        ("05:45", "06:00", "Di chuyển"),
        ("06:00", "07:00", "PT"),
        ("07:15", "08:15", "PT"),  # 2 ca sát nhau: không đi lại giữa ca
        ("08:15", "08:30", "Di chuyển"),
        ("17:45", "18:00", "Di chuyển"),
        ("18:00", "19:00", "PT"),
        ("19:00", "19:15", "Di chuyển"),
    ]


def test_pt_all_day_ignored():
    evs = [{"id": "x", "title": "Nghỉ", "start": "2026-11-02", "end": "2026-11-03", "allDay": True}]
    assert S.pt_items(evs, MON, 15) == []


def test_energy_label():
    st = DEFAULT_SETTINGS
    assert S.energy_label(600, 690, st) == "Tỉnh táo"
    assert S.energy_label(780, 870, st) == "Mệt"
    assert S.energy_label(1020, 1080, st) == "Bình thường"


def _items(days):
    return {d: S.day_items(d, DEFAULT_FIXED, [], [], [], DEFAULT_SETTINGS) for d in days}


def test_propose_hard_to_peak_light_to_low_with_buffer():
    days = [MON]
    tasks = [
        {"key": "h", "title": "Kế hoạch tài chính", "kind": "Khó", "minutes": 60},
        {"key": "l", "title": "Trả lời tin nhắn", "kind": "Nhẹ", "minutes": 30},
    ]
    props, un = S.propose(days, _items(days), tasks, DEFAULT_SETTINGS)
    assert not un
    p = {x.task_key: x for x in props}
    assert p["h"].energy == "Tỉnh táo"
    # Burpee 11:00–11:30 + đệm 15' -> việc khó bắt đầu sớm nhất 11:45
    assert p["h"].start >= S.to_min("11:45") or p["h"].end <= S.to_min("10:45")
    assert p["l"].energy == "Mệt"
    # 2 khối cách nhau ít nhất 15'
    a, b = sorted([p["h"], p["l"]], key=lambda x: x.start)
    assert b.start - a.end >= 15


def test_propose_respects_deep_cap_and_spreads():
    days = S.week_days(MON)
    tasks = [{"key": f"k{i}", "title": f"Học {i}", "kind": "Học", "minutes": 90} for i in range(4)]
    st = {**DEFAULT_SETTINGS, "max_deep_min": 180}
    props, un = S.propose(days, _items(days), tasks, st)
    assert not un
    per_day = {}
    for p in props:
        per_day[p.date] = per_day.get(p.date, 0) + (p.end - p.start)
    assert max(per_day.values()) <= 180
    # giờ tỉnh táo 10–13h bị Burpee 11h cắt -> mỗi ngày 1 khối 90' vào ngày kế tiếp thay vì giờ kém hơn
    assert all(p.energy != "Mệt" for p in props)


def test_propose_not_in_past():
    days = [MON]
    now = datetime(2026, 11, 2, 14, 0)
    props, _ = S.propose(days, _items(days), [{"key": "x", "title": "x", "kind": "Khó", "minutes": 60}], DEFAULT_SETTINGS, now=now)
    assert props[0].start >= 14 * 60


def test_propose_unplaceable():
    days = [MON]
    props, un = S.propose(days, _items(days), [{"key": "x", "title": "x", "kind": "Khó", "minutes": 600}], {**DEFAULT_SETTINGS, "max_deep_min": 999})
    assert not props and un and "Không còn" in un[0]["reason"]


def test_analyze_week_sleep_warning():
    days = S.week_days(MON)
    res = S.analyze_week(days, _items(days), DEFAULT_SETTINGS)
    assert any("Thiếu ngủ" in w for w in res["warnings"])
    assert res["per_day"][0]["sleep"] == 360


def test_analyze_week_overload():
    days = S.week_days(MON)
    items = _items(days)
    for d in days:
        items[d].append(Item(360, 1020, "Làm", "Công việc", "event"))  # 11h/ngày
    res = S.analyze_week(days, items, DEFAULT_SETTINGS)
    assert any("quá tải" in w for w in res["warnings"])


def test_clash_detected():
    days = [MON]
    items = _items(days)
    items[MON].append(Item(330, 360, "PT sớm", "PT", "pt"))
    res = S.analyze_week(days, items, DEFAULT_SETTINGS)
    assert res["clashes"] and any("Trùng giờ" in w for w in res["warnings"])


def test_skill_tasks_remaining():
    from core.week import skill_tasks

    days = S.week_days(MON)
    skills = [{"key": "en", "name": "Tiếng Anh", "hours_week": 2.5}, {"key": "x", "name": "X", "hours_week": 0}]
    learn = [{"date": "2026-11-03", "skill": "en", "minutes": 30}]
    blocks = [{"date": "2026-11-04", "start": "10:00", "end": "11:00", "task_key": "skill:en:2026-11-02:0"}]
    tasks = skill_tasks(skills, blocks, learn, days)
    assert [t["minutes"] for t in tasks] == [60]   # 150 - 30 - 60 = 60
    assert tasks[0]["kind"] == "Học" and tasks[0]["title"] == "Học: Tiếng Anh"


def test_classify_and_travel_only_for_pt_atlas():
    evs = [
        {"id": "1", "title": "A Đại (gold gym)", "start": "2026-11-02T15:00", "end": "2026-11-02T16:00", "cal": "__primary__"},
        {"id": "2", "title": "Họp Atlas tháng", "start": "2026-11-02T18:00", "end": "2026-11-02T19:00", "cal": "__primary__"},
        {"id": "3", "title": "Ăn cưới", "start": "2026-11-02T20:00", "end": "2026-11-02T21:00", "cal": "__primary__"},
        {"id": "4", "title": "Khách X", "start": "2026-11-02T06:00", "end": "2026-11-02T07:00", "cal": "PT"},
        {"id": "5", "title": "Tự tập ở gym", "start": "2026-11-02T08:00", "end": "2026-11-02T09:00", "cal": "__primary__"},
        {"id": "6", "title": "Không từ khoá", "color": "5", "start": "2026-11-02T10:00", "end": "2026-11-02T11:00", "cal": "__primary__"},
    ]
    its = S.pt_items(evs, MON, commute=15)
    kinds = {it.title: it.kind for it in its if it.source != "travel"}
    assert kinds == {"A Đại (gold gym)": "PT", "Họp Atlas tháng": "Atlas", "Ăn cưới": "Khác", "Khách X": "PT",
                     "Tự tập ở gym": "Tập", "Không từ khoá": "PT"}
    travel = [(S.fmt(i.start), S.fmt(i.end)) for i in its if i.source == "travel"]
    assert ("20:45", "21:00") not in travel and ("21:00", "21:15") not in travel  # đám cưới không cộng đi lại
    assert ("14:45", "15:00") in travel and ("19:00", "19:15") in travel


def test_work_shifts_and_early_client_chain():
    st = {**DEFAULT_SETTINGS, "_rules": None}
    evs = [{"id": "x", "title": "H.Anh - Dũng 6h", "start": "2026-11-03T06:00", "end": "2026-11-03T07:00",
            "cal": "atlas", "kind_override": "PT_Atlas"},
           {"id": "y", "title": "H.Anh - Kiệt", "start": "2026-11-03T17:30", "end": "2026-11-03T18:30",
            "cal": "atlas", "kind_override": "PT_Atlas"}]
    d = date(2026, 11, 3)
    its = S.day_items(d, [], evs, [], [], st)
    shifts = [(S.fmt(i.start), S.fmt(i.end)) for i in its if i.kind == "Ca làm"]
    assert shifts == [("07:00", "10:00"), ("17:00", "21:00")]
    travel = sorted((S.fmt(i.start), S.fmt(i.end)) for i in its if i.kind == "Di chuyển")
    # ca 6h nối liền giờ làm 7h → chỉ đi trước 5:45 và về lúc 10:00; chiều 16:45 và 21:00
    assert travel == [("05:45", "06:00"), ("10:00", "10:15"), ("16:45", "17:00"), ("21:00", "21:15")]
    res = S.analyze_week([d], {d: its}, st)
    assert not res["clashes"]  # dạy trong giờ làm không phải trùng
    assert res["per_day"][0]["work"] == 270 + 270  # 5:45–10:15 và 16:45–21:15 (gồm đi lại)


def test_day_off_and_week_override():
    tpl = {"shifts": [["07:00", "10:00"], ["17:00", "21:00"]], "off": [6]}
    sun = date(2026, 11, 8)
    assert S.work_plan_for(sun, tpl, None) == []
    rec = {"off": [2], "days": {"0": [["08:00", "11:00"]]}}
    assert S.work_plan_for(MON, tpl, rec) == [(480, 660)]
    assert S.work_plan_for(date(2026, 11, 4), tpl, rec) == []        # T4 nghỉ tuần này
    assert S.work_plan_for(sun, tpl, rec) == [(420, 600), (1020, 1260)]  # tuần này CN đi làm


def test_routine_tasks_window_and_done():
    from core.week import routine_tasks

    days = S.week_days(MON)  # 02–08/11
    r = [{"key": "v", "title": "Quay video", "kind": "Content", "minutes": 90, "per_week": 2, "start": "2026-11-09", "active": True},
         {"key": "w", "title": "Dựng", "kind": "Content", "minutes": 60, "per_week": 2, "active": True}]
    assert [t["title"] for t in routine_tasks(r, [], days)] == ["Dựng", "Dựng"]  # series chưa bắt đầu
    nxt = S.week_days(date(2026, 11, 9))
    blocks = [{"task_key": "routine:v:2026-11-09:0", "date": "2026-11-10"}]
    got = routine_tasks(r, blocks, nxt)
    assert sum(1 for t in got if t["title"] == "Quay video") == 1
