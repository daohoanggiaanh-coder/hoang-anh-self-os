import calendar
import html
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import db
from core import progress as P
from core import scheduler as S
from core import ui

today = ui.now_vn().date()

ui.nav_row()
ui.header("Tổng kết", "Nhìn lại & điều chỉnh", "Số liệu từ Top 3, thói quen, giờ học, studio. Nhận xét theo quy tắc rõ ràng — không phải phán đoán mơ hồ.")

data = db.progress_data()
t_week, t_month, t_motiv = st.tabs(["Tuần", "Tháng", "Cấp độ & huy hiệu"])


def render(start: date, end: date, label: str, keypfx: str):
    s = P.period_stats(data, start, end)
    pct = lambda v: f"{v:.0%}" if v is not None else "—"  # noqa: E731
    ui.stats([("Top 3 hoàn thành", pct(s["top3_rate"])), ("Thói quen", pct(s["habit_rate"])),
              ("Giờ học", f"{s['learn_min'] / 60:.1f}/{s['learn_target'] / 60:.1f}g"),
              ("Studio", f"+{s['studio_done']} việc · {pct(s['studio_progress'])}")])
    st.write("")
    c = P.review_comments(s)
    a, b = st.columns(2)
    a.html('<div class="so-card"><h4>Điểm mạnh</h4>' + ("".join(f"<div>✓ {html.escape(x)}</div>" for x in c["strong"])
                                                          or '<div class="so-muted">Chưa đủ dữ liệu.</div>') + "</div>")
    b.html('<div class="so-card"><h4>Cần cải thiện</h4>' + ("".join(f"<div>△ {html.escape(x)}</div>" for x in c["weak"])
                                                             or '<div class="so-muted">Không có điểm đáng lo.</div>') + "</div>")
    ui.card(f"Đề xuất cho {label}", "".join(f"<div>→ {html.escape(x)}</div>" for x in c["tips"]) or '<div class="so-muted">Giữ nhịp như hiện tại.</div>')

    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    hm = P.habit_done_map(data)
    active = [h for h in data.habits if h.get("active", True)]
    rows = []
    for d in days:
        r = db.daily(d.isoformat())
        top = [t for t in r["top3"] if str(t.get("text", "")).strip()]
        rows.append({"Ngày": pd.Timestamp(d),
                     "Top 3 xong": sum(1 for t in top if t.get("done")),
                     "Thói quen": sum(1 for h in active if d in hm.get(h["key"], set())),
                     "Phút học": sum(float(x.get("minutes") or 0) for x in data.learn_log if str(x.get("date", ""))[:10] == d.isoformat())})
    df = pd.DataFrame(rows).set_index("Ngày")
    st.markdown("**Theo ngày**")
    st.bar_chart(df[["Top 3 xong", "Thói quen"]], color=["#C9A45C", "#6E9C7E"], height=220, stack=False)
    if s["per_skill"]:
        st.markdown("**Giờ học theo kỹ năng**")
        st.dataframe([{"Kỹ năng": k, "Đã học": S.fmt_dur(m), "Mục tiêu": S.fmt_dur(t), "%": pct(m / t if t else None)}
                      for k, (m, t) in s["per_skill"].items()], hide_index=True, width="stretch")
    if s["per_habit"]:
        st.markdown("**Thói quen**")
        st.dataframe([{"Thói quen": k, "Đạt": f"{n}/{t:.0f}", "%": pct(n / t if t else None)} for k, (n, t) in s["per_habit"].items()],
                     hide_index=True, width="stretch")
    st.caption("Mục tiêu (OKR) tiến độ trung bình: " + (
        f"{sum(int(g.get('progress') or 0) for g in data.goals) / len(data.goals):.0f}%" if data.goals else "chưa có mục tiêu"))


with t_week:
    # Đầu tuần (T2, T3) mặc định xem tuần trước cho có đủ dữ liệu
    off = st.session_state.setdefault("rv_week_off", -1 if today.weekday() < 2 else 0)
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("‹", key="rvw_prev"):
            st.session_state.rv_week_off = off - 1
            st.rerun()
        ws = S.week_start(today) + timedelta(weeks=off)
        st.markdown(f"<div style='text-align:center;font-weight:600'>{ws.strftime('%d/%m')} – {(ws + timedelta(days=6)).strftime('%d/%m/%Y')}</div>",
                    unsafe_allow_html=True, width="stretch")
        if st.button("›", key="rvw_next", disabled=off >= 0):
            st.session_state.rv_week_off = off + 1
            st.rerun()
    render(ws, min(ws + timedelta(days=6), today) if off == 0 else ws + timedelta(days=6), "tuần sau", "w")

with t_month:
    months = [(today.year, today.month)]
    for _ in range(11):
        y, m = months[-1]
        months.append((y - 1, 12) if m == 1 else (y, m - 1))
    y, m = st.selectbox("Tháng", months, format_func=lambda ym: f"Tháng {ym[1]:02d}/{ym[0]}")
    ms = date(y, m, 1)
    me = date(y, m, calendar.monthrange(y, m)[1])
    render(ms, min(me, today), "tháng sau", "m")

with t_motiv:
    pts = P.total_points(data)
    lv = P.level_of(pts)
    st.html(f'<div class="so-card"><h4>Cấp {lv["level"]} · {html.escape(lv["name"])}</h4>'
            f'<div style="font-size:1.6rem;font-weight:700;color:var(--gold2)">{pts} điểm</div>'
            + ui.bar_html(lv["pct"], f"Còn {lv['next'] - pts} điểm lên cấp {lv['level'] + 1}" if lv["next"] else "Cấp cao nhất") + "</div>")
    st.html("".join(f'<span class="so-badge{"" if b["earned"] else " off"}" title="{html.escape(b["desc"])}">{b["icon"]} {html.escape(b["name"])}</span>'
                    for b in P.badges(data, today)))
    st.markdown("**Cách tính điểm** (chỉ cộng, không bao giờ trừ):")
    st.dataframe([{"Hoạt động": k, "Điểm": v} for k, v in {
        "Chọn Top 3 trong ngày": P.POINTS["top3_set"], "Mỗi việc Top 3 hoàn thành": P.POINTS["top3_done"],
        "Viết tổng kết cuối ngày": P.POINTS["review"], "Mỗi thói quen hoàn thành": P.POINTS["habit"],
        "Mỗi 10 phút học": P.POINTS["learn_10min"], "Cập nhật số đo": P.POINTS["body_log"],
        "Xong checklist vẻ ngoài trong ngày": P.POINTS["look_day"], "Mỗi việc chuẩn bị studio": P.POINTS["studio_task"]}.items()],
        hide_index=True, width="stretch")
