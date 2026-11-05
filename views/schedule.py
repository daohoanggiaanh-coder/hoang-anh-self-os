from datetime import datetime, timedelta

import streamlit as st

from core import db
from core import scheduler as S
from core import ui
from core.editors import edit_table, from_date, from_time, to_date, to_time
from core.quick import quick_add, work_week_editor
from core.week import load_week, routine_tasks, skill_tasks

cc = st.column_config
now = ui.now_vn()

ui.nav_row()
ui.header("Lịch & giờ trống", "Lịch tuần", "Lịch cố định + ca PT trên Google Calendar → web tìm giờ trống và đề xuất xếp việc.")

flash = st.session_state.pop("_flash", None)
if flash:
    st.success(flash)

# ------------------------------------------------------------- chọn tuần
ref = st.session_state.setdefault("week_ref", now.date())
days = S.week_days(ref)
with st.container(horizontal=True, wrap=False, vertical_alignment="center"):
    if st.button("‹", key="wk_prev", help="Tuần trước"):
        st.session_state.week_ref = ref - timedelta(days=7)
        st.rerun()
    st.markdown(
        f"<div style='text-align:center;font-weight:600;white-space:nowrap'>{days[0].strftime('%d/%m')} – {days[-1].strftime('%d/%m/%Y')}</div>",
        unsafe_allow_html=True, width="stretch",
    )
    if st.button("›", key="wk_next", help="Tuần sau"):
        st.session_state.week_ref = ref + timedelta(days=7)
        st.rerun()
    if st.button("↻", key="reload_gcal", help="Đọc lại lịch PT từ Google Calendar"):
        db.invalidate_calendar()
        st.rerun()

wk = load_week(ref)
if wk.pt_error:
    st.warning(f"Chưa đọc được lịch PT: {wk.pt_error}")

tab_week, tab_work, tab_add, tab_prop, tab_tasks, tab_fixed, tab_events = st.tabs(
    ["Tuần này", "🗓 Lịch làm tuần", "＋ Thêm việc", "Đề xuất xếp lịch", "Việc cần xếp", "Lịch cố định", "Việc phát sinh"]
)

with tab_work:
    work_week_editor(days)

with tab_add:
    quick_add("sched", now.date())

# ------------------------------------------------------------- Tuần này
with tab_week:
    pdays = wk.analysis["per_day"]
    ui.stats(
        [
            ("Giờ trống cả tuần", S.fmt_dur(sum(p["free"] for p in pdays))),
            ("Giờ dạy PT", S.fmt_dur(sum(p["pt"] for p in pdays))),
            ("Giờ làm việc", S.fmt_dur(wk.analysis["work_total"])),
            ("Ngủ TB / ngày", S.fmt_dur(sum(p["sleep"] for p in pdays) / 7)),
        ]
    )
    st.write("")
    ui.warnings(wk.analysis["warnings"])
    st.markdown("**Bản đồ màu cả tuần** · 5h–23h")
    st.html(ui.legend_html())
    st.html(ui.week_map_html(days, wk.items, {p["date"]: p["slots"] for p in pdays}, today=now.date()))
    by_kind = {}
    for d_ in days:
        for it in wk.items[d_]:
            if it.kind != "Ngủ":
                by_kind[it.kind] = by_kind.get(it.kind, 0) + it.minutes
    if by_kind:
        st.html('<div class="so-muted" style="margin:8px 0 4px">Tổng theo loại: ' + " · ".join(
            f'<span style="color:{ui.KIND_COLOR.get(k)}">{ui.KIND_ICON.get(k, "")} {ui.KIND_LABEL.get(k, k)} {S.fmt_dur(m)}</span>'
            for k, m in sorted(by_kind.items(), key=lambda x: -x[1])) + "</div>")
    st.markdown("**Chi tiết từng ngày**")
    for p in pdays:
        d = p["date"]
        is_today = d == now.date()
        label = f"{'● ' if is_today else ''}{S.vn_date(d)} · trống {S.fmt_dur(p['free'])} · PT {S.fmt_dur(p['pt'])}"
        with st.expander(label, expanded=is_today):
            st.html(ui.timeline_html(wk.items[d], p["slots"], now.hour * 60 + now.minute if is_today else None))

# ------------------------------------------------------------- Đề xuất
def _accept(p: dict):
    gcal_id = ""
    if wk.settings.get("write_gcal") and not db.is_local():
        try:
            gcal_id = db.store().calendar_create(
                {"date": p["date"], "start": p["start_s"], "end": p["end_s"], "title": f"[Self OS] {p['title']}",
                 "color": S.CATEGORIES.get(p["kind"], S.CATEGORIES["Khác"])[3]}
            )
        except Exception as e:  # vẫn lưu vào web dù không ghi được lên lịch
            st.session_state["_flash_err"] = f"Không ghi được lên Google Calendar: {e}"
    db.put(
        "blocks",
        [{"date": p["date"], "start": p["start_s"], "end": p["end_s"], "title": p["title"], "kind": p["kind"],
          "task_key": p["task_key"], "gcal_id": gcal_id}],
    )
    task = next((t for t in wk.tasks if t["key"] == p["task_key"]), None)
    if task:
        db.put("tasks", [{**task, "status": "Đã xếp"}])


def _proposals_key():
    return f"props:{days[0].isoformat()}"


with tab_prop:
    err = st.session_state.pop("_flash_err", None)
    if err:
        st.error(err)
    pending = [t for t in wk.tasks if t.get("status", "Chờ xếp") == "Chờ xếp"]
    st.markdown(
        f"<div class='so-muted'>Việc khó & học → giờ tỉnh táo ({wk.settings['peak_start']}–{wk.settings['peak_end']}); "
        f"việc nhẹ → giờ hay mệt ({wk.settings['low_start']}–{wk.settings['low_end']}); "
        f"đệm {wk.settings['buffer_min']} phút giữa các khối. Đang chờ xếp: <b>{len(pending)}</b> việc.</div>",
        unsafe_allow_html=True,
    )
    with_skills = st.toggle("Tự chèn giờ học kỹ năng còn thiếu trong tuần", value=True)
    sk_tasks = skill_tasks(db.skills(), wk.blocks, db.table("learn_log"), days) if with_skills else []
    rt_tasks = routine_tasks(db.routines(), wk.blocks, days)
    if rt_tasks:
        st.caption("Việc lặp hằng tuần còn thiếu: " + ", ".join(sorted({f"{ui.KIND_ICON.get(t['kind'], '')} {t['title']}" for t in rt_tasks})))
    if sk_tasks:
        st.caption(f"Giờ học còn thiếu tuần này: {len(sk_tasks)} buổi · {S.fmt_dur(sum(t['minutes'] for t in sk_tasks))}")
    if st.button("✦ Tạo đề xuất cho tuần", type="primary", disabled=not (pending or sk_tasks or rt_tasks)):
        props, unplaced = S.propose(days, wk.items, pending + rt_tasks + sk_tasks, wk.settings, now=now)
        st.session_state[_proposals_key()] = {"props": [p.to_dict() for p in props], "unplaced": unplaced}
        st.rerun()
    if not pending and not sk_tasks and not rt_tasks:
        st.info("Chưa có việc nào chờ xếp. Anh thêm việc ở tab **Việc cần xếp** hoặc đặt giờ học ở trang **Kỹ năng**.")

    data = st.session_state.get(_proposals_key())
    if data:
        props = data["props"]
        if props:
            if st.button(f"Nhận tất cả ({len(props)})"):
                for p in props:
                    _accept(p)
                data["props"] = []
                st.session_state["_flash"] = "Đã nhận tất cả đề xuất."
                st.rerun()
        for i, p in enumerate(list(props)):
            d = to_date(p["date"])
            with st.container(border=True):
                st.markdown(
                    f"**{p['title']}**  \n{S.vn_date(d)} · {p['start_s']}–{p['end_s']} · "
                    f"{ui.ENERGY_ICON[p['energy']]} {p['energy']} · {ui.KIND_ICON.get(p['kind'], '')} _{ui.KIND_LABEL.get(p['kind'], p['kind'])}_"
                    + (f"  \n:orange[{p['note']}]" if p["note"] else "")
                )
                row = st.container(horizontal=True, wrap=False)
                if row.button("Nhận", key=f"acc{i}{p['pid']}", type="primary", width="stretch"):
                    _accept(p)
                    props.pop(i)
                    st.rerun()
                with row.popover("Đổi", width="stretch"):
                    nd = st.date_input("Ngày", d, min_value=days[0], max_value=days[-1], key=f"nd{p['pid']}", format="DD/MM/YYYY")
                    nt = st.time_input("Bắt đầu", to_time(p["start_s"]), step=900, key=f"nt{p['pid']}")
                    if st.button("Lưu giờ mới", key=f"sv{p['pid']}"):
                        dur = S.to_min(p["end_s"]) - S.to_min(p["start_s"])
                        s = nt.hour * 60 + nt.minute
                        e = min(S.DAY, s + dur)
                        busy = [(it.start, it.end) for it in wk.items[nd]]
                        clash = any(s < be and e > bs for bs, be in busy)
                        p.update(date=nd.isoformat(), start=s, end=e, start_s=S.fmt(s), end_s=S.fmt(e),
                                 energy=S.energy_label(s, e, wk.settings),
                                 note="Trùng với lịch đã có — kiểm tra lại" if clash else "")
                        st.rerun()
                if row.button("Bỏ", key=f"drop{i}{p['pid']}", width="stretch"):
                    props.pop(i)
                    st.rerun()
        for u in data["unplaced"]:
            st.warning(f"Chưa xếp được **{u.get('title')}**: {u['reason']}")

    st.markdown("##### Khối đã nhận tuần này")
    mine = sorted(
        [b for b in wk.blocks if days[0].isoformat() <= b.get("date", "") <= days[-1].isoformat()],
        key=lambda b: (b["date"], b["start"]),
    )
    if not mine:
        st.markdown("<div class='so-muted'>Chưa có.</div>", unsafe_allow_html=True)
    for b in mine:
        a, z = st.columns([5, 1])
        a.markdown(f"{S.vn_date(to_date(b['date']))} · **{b['start']}–{b['end']}** · {b['title']} · _{b['kind']}_"
                   + (" · 📅" if b.get("gcal_id") else ""))
        if z.button("Huỷ", key=f"unb{b['key']}", width="stretch"):
            if b.get("gcal_id") and not db.is_local():
                try:
                    db.store().calendar_delete(b["gcal_id"])
                except Exception as e:
                    st.session_state["_flash_err"] = f"Không xoá được trên Google Calendar: {e}"
            db.delete("blocks", [b["key"]])
            task = next((t for t in wk.tasks if t["key"] == b.get("task_key")), None)
            if task:
                db.put("tasks", [{**task, "status": "Chờ xếp"}])
            st.rerun()

# ------------------------------------------------------------- Việc cần xếp
with tab_tasks:
    st.markdown(
        "<div class='so-muted'>Mỗi dòng là 1 việc cần thời gian. Loại: "
        + " · ".join(f"<b>{k}</b> = {v}" for k, v in S.TASK_KIND_HELP.items())
        + ". Để trống <i>Ngày</i> nếu ngày nào trong tuần cũng được.</div>",
        unsafe_allow_html=True,
    )
    ident = lambda v: v  # noqa: E731
    edit_table(
        "tasks",
        wk.tasks,
        {
            "title": (cc.TextColumn("Việc", required=True, width="large"), ident, lambda v: (str(v).strip() or None) if v is not None else None),
            "kind": (cc.SelectboxColumn("Loại", options=S.TASK_KINDS, required=True, format_func=lambda k: f"{ui.KIND_ICON[k]} {ui.KIND_LABEL[k]}"), ident, ident),
            "minutes": (cc.NumberColumn("Phút", min_value=15, max_value=480, step=15, required=True), ident,
                        lambda v: int(v) if v is not None and v == v else None),
            "date": (cc.DateColumn("Ngày (tuỳ chọn)", format="DD/MM/YYYY"), to_date, from_date),
            "status": (cc.SelectboxColumn("Trạng thái", options=["Chờ xếp", "Đã xếp", "Xong"]), ident, ident),
        },
        required=["title", "kind", "minutes"],
        widget_key="ed_tasks",
        defaults={"status": "Chờ xếp"},
    )

    st.markdown("##### 🔁 Việc lặp lại mỗi tuần")
    st.caption("Mỗi tuần web tự tạo đủ số buổi để đề xuất xếp giờ. Tắt “Đang dùng” để tạm dừng.")
    edit_table(
        "routines", db.routines(),
        {
            "title": (cc.TextColumn("Việc", required=True, width="large"), ident, lambda v: (str(v).strip() or None) if v is not None else None),
            "kind": (cc.SelectboxColumn("Loại", options=S.TASK_KINDS, required=True, format_func=lambda k: f"{ui.KIND_ICON[k]} {ui.KIND_LABEL[k]}"), ident, ident),
            "minutes": (cc.NumberColumn("Phút/buổi", min_value=15, max_value=480, step=15, required=True), ident,
                        lambda v: int(v) if v is not None and v == v else None),
            "per_week": (cc.NumberColumn("Buổi/tuần", min_value=1, max_value=7, step=1, required=True), ident,
                         lambda v: int(v) if v is not None and v == v else 1),
            "start": (cc.DateColumn("Từ ngày", format="DD/MM/YYYY"), to_date, from_date),
            "end": (cc.DateColumn("Đến ngày", format="DD/MM/YYYY"), to_date, from_date),
            "active": (cc.CheckboxColumn("Đang dùng"), lambda v: v if v is not None else True, lambda v: bool(v)),
        },
        required=["title", "kind", "minutes"], widget_key="ed_routines", defaults={"active": True, "per_week": 1},
    )

# ------------------------------------------------------------- Lịch cố định
with tab_fixed:
    st.markdown(
        "<div class='so-muted'>Những việc lặp lại hằng tuần (ngủ, Burpee...). Ca PT anh nhập trên lịch Google "
        f"<b>“{wk.settings.get('pt_calendar', 'PT')}”</b>, không cần nhập ở đây. Giờ ngủ qua đêm ghi 23:00 → 05:00 là được.</div>",
        unsafe_allow_html=True,
    )
    edit_table(
        "fixed",
        db.fixed_schedule(),
        {
            "days": (cc.SelectboxColumn("Ngày", options=S.DAY_OPTIONS, required=True), lambda v: v, lambda v: v),
            "start": (cc.TimeColumn("Bắt đầu", format="HH:mm", step=300, required=True), to_time, from_time),
            "end": (cc.TimeColumn("Kết thúc", format="HH:mm", step=300, required=True), to_time, from_time),
            "title": (cc.TextColumn("Nội dung"), lambda v: v, lambda v: v if v == v else None),
            "kind": (cc.SelectboxColumn("Loại", options=S.FIXED_KINDS, required=True), lambda v: v, lambda v: v),
        },
        required=["days", "start", "end", "kind"],
        widget_key="ed_fixed",
    )

# ------------------------------------------------------------- Việc phát sinh
with tab_events:
    st.markdown(
        "<div class='so-muted'>Việc một lần (họp, khám, đi đám cưới...). Cũng có thể nhập thẳng trên Google Calendar "
        "lịch PT nếu anh muốn tính là giờ bận.</div>",
        unsafe_allow_html=True,
    )
    week_events = [e for e in db.table("events") if days[0].isoformat() <= e.get("date", "") <= days[-1].isoformat()]
    show_all = st.toggle("Hiện cả các tuần khác", value=False)
    edit_table(
        "events",
        db.table("events") if show_all else week_events,
        {
            "date": (cc.DateColumn("Ngày", format="DD/MM/YYYY", required=True), to_date, from_date),
            "start": (cc.TimeColumn("Bắt đầu", format="HH:mm", step=300, required=True), to_time, from_time),
            "end": (cc.TimeColumn("Kết thúc", format="HH:mm", step=300, required=True), to_time, from_time),
            "title": (cc.TextColumn("Nội dung", required=True), lambda v: v, lambda v: v if v == v else None),
            "kind": (cc.SelectboxColumn("Loại", options=["Công việc", "Gia đình", "Tập", "Khác"]), lambda v: v, lambda v: v),
        },
        required=["date", "start", "end", "title"],
        widget_key="ed_events" + ("_all" if show_all else ""),
        defaults={"kind": "Khác"},
    )
