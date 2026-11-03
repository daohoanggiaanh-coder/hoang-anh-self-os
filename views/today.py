import html
from datetime import timedelta

import streamlit as st

from core import db
from core import progress as P
from core import scheduler as S
from core import ui
from core.week import load_week

now = ui.now_vn()
today = now.date()
ds = today.isoformat()
wk = load_week(today)
items = wk.items[today]
day = next(p for p in wk.analysis["per_day"] if p["date"] == today)
now_min = now.hour * 60 + now.minute
now_q = -(-now_min // 15) * 15

ui.nav_row()
hour = now.hour
greet = "Chào buổi sáng" if hour < 11 else "Chào buổi trưa" if hour < 14 else "Chào buổi chiều" if hour < 18 else "Chào buổi tối"
ui.header("Hôm nay của tôi", f"{greet}, anh Hoàng Anh", S.vn_date(today, with_year=True))
ui.flash()

data = db.progress_data()
lv = P.level_of(P.total_points(data))
rec = db.daily(ds)
habits = [h for h in data.habits if h.get("active", True)]
hmap = P.habit_done_map(data)
done_today = {h["key"] for h in habits if today in hmap.get(h["key"], set())}
any_done = set().union(*hmap.values()) if hmap else set()
learn_today = sum(float(r.get("minutes") or 0) for r in data.learn_log if str(r.get("date", ""))[:10] == ds)
wk_lo, wk_hi = wk.days[0].isoformat(), wk.days[-1].isoformat()
learn_week = sum(float(r.get("minutes") or 0) for r in data.learn_log if wk_lo <= str(r.get("date", ""))[:10] <= wk_hi)
learn_target = sum(float(s.get("hours_week") or 0) for s in data.skills) * 60

remaining = [(max(s, now_q), e) for s, e in day["slots"] if e > now_q and e - max(s, now_q) >= int(wk.settings["min_slot"])]
top_set = [t for t in rec["top3"] if str(t.get("text", "")).strip()]
ui.stats(
    [
        ("Giờ trống còn lại", S.fmt_dur(sum(e - s for s, e in remaining))),
        ("Top 3 xong", f"{sum(1 for t in top_set if t.get('done'))}/{len(top_set) or 3}"),
        ("Thói quen", f"{len(done_today)}/{len(habits)}"),
        ("Học tuần này", f"{learn_week / 60:.1f}/{learn_target / 60:.0f}g"),
    ]
)
st.write("")

# ------------------------------------------------------------- nhắc nhẹ (không phạt)
nudges = []
if not top_set:
    nudges.append("Chưa chọn Top 3 cho hôm nay — chỉ mất 1 phút.")
if habits and len(done_today) < len(habits) and hour >= 19:
    nudges.append(f"Còn {len(habits) - len(done_today)} thói quen, vẫn kịp trước khi ngủ.")
if hour >= 20 and not any(str(x).strip() for x in rec.get("review", [])):
    nudges.append("Cuối ngày rồi: 3 câu tổng kết nhé.")
for n in nudges:
    st.html(f'<div class="so-warn">✦ {html.escape(n)}</div>')
if wk.pt_error:
    st.warning(f"Chưa đọc được lịch PT từ Google Calendar: {wk.pt_error}")

left, right = st.columns([3, 2], gap="medium")

# ------------------------------------------------------------- Top 3
with left:
    with st.container(border=True):
        st.markdown("**🎯 Top 3 hôm nay**")
        with st.form("top3"):
            new_top = []
            for i in range(3):
                t = rec["top3"][i] if i < len(rec["top3"]) else {"text": "", "done": False}
                row = st.container(horizontal=True, vertical_alignment="center", gap="small")
                done = row.checkbox("Xong", value=bool(t.get("done")), key=f"t3d{i}", label_visibility="collapsed")
                text = row.text_input(f"Việc {i + 1}", value=t.get("text", ""), key=f"t3t{i}",
                                     placeholder=["Việc quan trọng nhất", "Việc thứ hai", "Việc thứ ba"][i],
                                     label_visibility="collapsed")
                new_top.append({"text": text.strip(), "done": done and bool(text.strip())})
            if st.form_submit_button("Lưu Top 3", type="primary"):
                db.put("daily", [{**rec, "top3": new_top}])
                st.session_state["_flash"] = "Đã lưu Top 3."
                st.rerun()

    # --------------------------------------------------------- thói quen
    with st.container(border=True):
        st.markdown("**🔥 Thói quen hôm nay**")

        def _toggle(hk):
            val = st.session_state[f"hb_{hk}"]
            db.put("habit_log", [{"key": f"{ds}|{hk}", "date": ds, "habit": hk, "done": val}])

        for h in habits:
            stk = P.streak(hmap.get(h["key"], set()), today)
            st.checkbox(
                f"{h.get('icon', '•')} {h['name']}" + (f"  · 🔥{stk}" if stk else ""),
                value=h["key"] in done_today, key=f"hb_{h['key']}", on_change=_toggle, args=(h["key"],),
            )
        if not habits:
            st.caption("Chưa có thói quen — thêm ở trang Thói quen.")

    ui.card("Lịch hôm nay", ui.legend_html(sorted({it.kind for it in items if it.kind != "Ngủ"}, key=list(ui.KIND_COLOR).index))
            + ui.timeline_html(items, day["slots"], now_min))

# ------------------------------------------------------------- cột phải
with right:
    nxt = next(((s, e) for s, e in remaining), None)
    if nxt:
        s, e = nxt
        en = S.energy_label(s, e, wk.settings)
        body = (f'<div style="font-size:1.25rem;font-weight:700">{S.fmt(s)} – {S.fmt(e)}</div>'
                f'<div class="so-muted">{S.fmt_dur(e - s)} · {ui.ENERGY_ICON[en]} {en}</div>')
    else:
        body = '<div class="so-muted">Hôm nay không còn khoảng trống ≥ 30 phút.</div>'
    ui.card("Khoảng trống kế tiếp", body)

    with st.container(border=True):
        st.markdown("**📚 Giờ học**")
        st.html(ui.bar_html(learn_week / learn_target if learn_target else None,
                            f"Tuần này {learn_week / 60:.1f} / {learn_target / 60:.1f} giờ · hôm nay {int(learn_today)} phút"))
        learn_blocks = [it for it in items if it.source == "block" and it.kind == "Học"]
        blocks_by_key = {b["key"]: b for b in wk.blocks}
        for it in learn_blocks:
            b = blocks_by_key.get(it.ref, {})
            label = f"{S.fmt(it.start)}–{S.fmt(it.end)} · {it.title}"
            if b.get("learned"):
                st.markdown(f"✅ {label}")
            elif st.button(f"Đã học: {label}", key=f"lb{it.ref}", width="stretch"):
                sk_key = str(b.get("task_key", "")).split(":")[1] if str(b.get("task_key", "")).startswith("skill:") else ""
                db.put("learn_log", [{"date": ds, "skill": sk_key, "minutes": it.minutes, "note": "", "block": it.ref}])
                db.put("blocks", [{**b, "learned": True}])
                st.session_state["_flash"] = f"Đã ghi {it.minutes} phút học. Ghi điều học được ở trang Kỹ năng nhé."
                st.rerun()
        if not learn_blocks:
            st.caption("Hôm nay chưa có khối học nào. Trang Lịch → Đề xuất sẽ tự chèn giờ học.")
        st.page_link("views/skills.py", label="Ghi nhật ký học →")

    with st.container(border=True):
        st.markdown("**✦ Động lực**")
        best_now = max((P.streak(v, today) for v in hmap.values()), default=0)
        st.html(
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<div><b style="font-size:1.2rem">Cấp {lv["level"]}</b> · {html.escape(lv["name"])}</div>'
            f'<div class="so-muted">{lv["points"]} điểm</div></div>'
            + ui.bar_html(lv["pct"], f"Còn {lv['next'] - lv['points']} điểm lên cấp" if lv["next"] else "Cấp cao nhất")
            + f'<div class="so-muted" style="margin-top:6px">🔥 Chuỗi thói quen dài nhất đang giữ: <b>{best_now}</b> ngày'
            + f' · Ngày hoạt động liên tiếp: <b>{P.streak(any_done, today)}</b></div>'
        )

    show_review = hour >= 18
    with st.expander("✍️ Tổng kết cuối ngày (3 câu)", expanded=show_review):
        with st.form("review"):
            prompts = ["Hôm nay làm tốt điều gì?", "Điều gì chưa tốt / học được gì?", "Ngày mai làm khác đi điều gì?"]
            rv = rec.get("review") or ["", "", ""]
            vals = [st.text_input(p, value=rv[i] if i < len(rv) else "", key=f"rv{i}") for i, p in enumerate(prompts)]
            if st.form_submit_button("Lưu tổng kết", type="primary"):
                db.put("daily", [{**db.daily(ds), "review": [v.strip() for v in vals]}])
                st.session_state["_flash"] = "Đã lưu tổng kết. Nghỉ ngơi tốt nhé anh."
                st.rerun()

if wk.analysis["warnings"]:
    with st.expander("Nhắc nhẹ về lịch tuần này"):
        ui.warnings(wk.analysis["warnings"])

yest = db.daily((today - timedelta(days=1)).isoformat())
if any(str(x).strip() for x in yest.get("review", [])) and str(yest["review"][2]).strip():
    st.caption(f"Hôm qua anh dặn mình: “{yest['review'][2]}”")
