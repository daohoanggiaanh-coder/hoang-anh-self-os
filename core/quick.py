"""Các khối giao diện dùng chung: ＋ Thêm việc (đơn giản) và Lịch làm tuần."""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from core import db
from core import scheduler as S
from core import ui
from core.editors import from_time, to_time

DURATIONS = [15, 30, 45, 60, 90, 120, 180]
ADD_KINDS = ["Content", "Khó", "Học", "Atlas", "Tập", "Nhẹ"]


def quick_add(key: str, today: date):
    """Thêm việc trong 4 bước: tên → loại → bao lâu → khi nào."""
    with st.form(f"qa_{key}", clear_on_submit=True):
        title = st.text_input("1 · Việc gì?", placeholder="VD: Quay video series 84 ngày – Ngày 1", key=f"qa_t_{key}")
        kind = st.pills("2 · Loại việc", ADD_KINDS, default="Content", key=f"qa_k_{key}",
                        format_func=lambda k: f"{ui.KIND_ICON[k]} {ui.KIND_LABEL[k]}")
        minutes = st.pills("3 · Mất bao lâu?", DURATIONS, default=60, key=f"qa_m_{key}", format_func=S.fmt_dur)
        when = st.radio("4 · Khi nào?", ["Ngày nào trong tuần cũng được", "Chọn ngày", "Lặp lại mỗi tuần"],
                        key=f"qa_w_{key}", horizontal=True)
        c1, c2 = st.columns(2)
        day = c1.date_input("Ngày (nếu chọn ngày)", today, min_value=today, format="DD/MM/YYYY", key=f"qa_d_{key}")
        per_week = c2.number_input("Số buổi / tuần (nếu lặp lại)", 1, 7, 2, key=f"qa_n_{key}")
        until = c1.date_input("Lặp đến ngày (tuỳ chọn)", None, min_value=today, format="DD/MM/YYYY", key=f"qa_u_{key}")
        ok = st.form_submit_button("＋ Thêm việc", type="primary", width="stretch")
    if ok:
        if not title.strip():
            st.error("Anh nhập tên việc giúp em.")
            return
        kind = kind or "Khó"
        minutes = int(minutes or 60)
        if when == "Lặp lại mỗi tuần":
            db.put("routines", [{"title": title.strip(), "kind": kind, "minutes": minutes, "per_week": int(per_week),
                                 "start": today.isoformat(), "end": until.isoformat() if until else None, "active": True}])
            msg = f"Đã thêm việc lặp: {title.strip()} · {int(per_week)} buổi/tuần × {S.fmt_dur(minutes)}."
        else:
            db.put("tasks", [{"title": title.strip(), "kind": kind, "minutes": minutes, "status": "Chờ xếp",
                              "date": day.isoformat() if when == "Chọn ngày" else None}])
            msg = f"Đã thêm: {title.strip()} · {S.fmt_dur(minutes)}."
        st.session_state["_flash"] = msg + " Vào Lịch → Đề xuất xếp lịch → bấm “Tạo đề xuất” để web tìm giờ."
        st.rerun()


def work_week_editor(days: list[date]):
    """Lịch làm tuần: bấm chọn ngày nghỉ; giờ làm thường lệ sửa ở phần dưới."""
    tpl = db.work_template()
    weeks = db.work_weeks()
    wk_key = days[0].isoformat()
    rec = weeks.get(wk_key)
    cur_off = [int(x) for x in (rec or tpl).get("off", [])]
    shifts = tpl.get("shifts") or S.DEFAULT_WORK["shifts"]
    st.markdown(
        f"<div class='so-muted'>Giờ làm thường lệ: <b>{' · '.join(f'{a}–{b}' for a, b in shifts)}</b>. "
        "Có ca khách sớm hơn thì web tự lấy từ Google Calendar và tính đi sớm hơn — anh không cần sửa ở đây."
        + ("" if rec else " <i>(Tuần này chưa lưu riêng — đang dùng mặc định.)</i>") + "</div>",
        unsafe_allow_html=True,
    )
    off = st.pills("Ngày nghỉ tuần này (bấm để chọn)", list(range(7)), selection_mode="multi", default=cur_off,
                   format_func=lambda i: S.WEEKDAY_NAMES[i], key=f"off_{wk_key}")
    c1, c2 = st.columns(2)
    if c1.button("💾 Lưu lịch tuần này", type="primary", width="stretch", key=f"sv_{wk_key}"):
        db.put("work_week", [{**(rec or {}), "key": wk_key, "off": sorted(off)}])
        st.session_state["_flash"] = f"Đã lưu lịch làm tuần {days[0].strftime('%d/%m')}–{days[-1].strftime('%d/%m')}." + (
            " Nghỉ: " + ", ".join(S.WEEKDAY_NAMES[i] for i in sorted(off)) + "." if off else " Không nghỉ ngày nào.")
        st.rerun()
    if c2.button("Dùng làm mặc định mọi tuần", width="stretch", key=f"df_{wk_key}"):
        db.save_work_template({**tpl, "off": sorted(off)})
        db.put("work_week", [{**(rec or {}), "key": wk_key, "off": sorted(off)}])
        st.session_state["_flash"] = "Đã lưu ngày nghỉ này làm mặc định cho các tuần sau."
        st.rerun()

    st.html("<div style='display:flex;flex-wrap:wrap;gap:6px;margin:8px 0'>" + "".join(
        f"<span class='so-chip' style='padding:4px 10px;{'opacity:.45' if d.weekday() in off else ''}'>"
        f"{S.WEEKDAY_NAMES[d.weekday()]} {d.strftime('%d/%m')} · "
        f"{'Nghỉ' if d.weekday() in off else ' · '.join(f'{S.fmt(a)}–{S.fmt(b)}' for a, b in S.work_plan_for(d, {**tpl, 'off': off}, None))}</span>"
        for d in days) + "</div>")

    with st.expander("Đổi giờ làm thường lệ"):
        with st.form("work_tpl"):
            a, b = st.columns(2)
            m1 = a.time_input("Ca sáng từ", to_time(shifts[0][0]) if shifts else None, step=900)
            m2 = b.time_input("đến", to_time(shifts[0][1]) if shifts else None, step=900)
            e1 = a.time_input("Ca chiều từ", to_time(shifts[1][0]) if len(shifts) > 1 else None, step=900)
            e2 = b.time_input("đến ", to_time(shifts[1][1]) if len(shifts) > 1 else None, step=900)
            if st.form_submit_button("Lưu giờ làm", type="primary"):
                new = [[from_time(m1), from_time(m2)]] + ([[from_time(e1), from_time(e2)]] if e1 and e2 else [])
                db.save_work_template({**tpl, "shifts": new})
                st.session_state["_flash"] = "Đã lưu giờ làm thường lệ."
                st.rerun()


def week_days_from(ref: date) -> list[date]:
    s = ref - timedelta(days=ref.weekday())
    return [s + timedelta(days=i) for i in range(7)]
