import streamlit as st

from core import scheduler as S
from core import ui
from core.week import load_week

now = ui.now_vn()
today = now.date()
wk = load_week(today)
items = wk.items[today]
day = next(p for p in wk.analysis["per_day"] if p["date"] == today)
now_min = now.hour * 60 + now.minute
now_q = -(-now_min // 15) * 15  # làm tròn lên mốc 15'

hour = now.hour
greet = "Chào buổi sáng" if hour < 11 else "Chào buổi trưa" if hour < 14 else "Chào buổi chiều" if hour < 18 else "Chào buổi tối"
ui.nav_row()
ui.header("Hôm nay của tôi", f"{greet}, anh Hoàng Anh", S.vn_date(today, with_year=True))

remaining = [(max(s, now_q), e) for s, e in day["slots"] if e > now_q and e - max(s, now_q) >= int(wk.settings["min_slot"])]
blocks_today = [it for it in items if it.source == "block"]
ui.stats(
    [
        ("Giờ trống còn lại", S.fmt_dur(sum(e - s for s, e in remaining))),
        ("Ca PT hôm nay", str(sum(1 for it in items if it.kind == "PT"))),
        ("Khối đã nhận", str(len(blocks_today))),
        ("Giờ ngủ theo lịch", S.fmt_dur(day["sleep"])),
    ]
)
st.write("")

if wk.pt_error:
    st.warning(f"Chưa đọc được lịch PT từ Google Calendar: {wk.pt_error}")

left, right = st.columns([3, 2], gap="medium")
with left:
    ui.card("Lịch hôm nay", ui.timeline_html(items, day["slots"], now_min))
with right:
    nxt = next(((s, e) for s, e in remaining), None)
    if nxt:
        s, e = nxt
        en = S.energy_label(s, e, wk.settings)
        body = (
            f'<div style="font-size:1.25rem;font-weight:700">{S.fmt(s)} – {S.fmt(e)}</div>'
            f'<div class="so-muted">{S.fmt_dur(e - s)} · {ui.ENERGY_ICON[en]} {en}</div>'
        )
    else:
        body = '<div class="so-muted">Hôm nay không còn khoảng trống ≥ 30 phút.</div>'
    ui.card("Khoảng trống kế tiếp", body)
    ui.card("Top 3 hôm nay", '<div class="so-soon">Có ở phần 2 — Mục tiêu & việc hằng ngày.</div>')
    ui.card("Thói quen", '<div class="so-soon">Có ở phần 3.</div>')
    ui.card("Giờ học", '<div class="so-soon">Có ở phần 4.</div>')

if wk.analysis["warnings"]:
    st.markdown("##### Nhắc nhẹ tuần này")
    ui.warnings(wk.analysis["warnings"])

if st.button("Mở Lịch & giờ trống để xếp việc →", type="primary"):
    st.switch_page("views/schedule.py")
