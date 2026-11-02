from datetime import timedelta

import streamlit as st

from core import db
from core import scheduler as S
from core import ui
from core.editors import edit_table

cc = st.column_config
today = ui.now_vn().date()

ui.nav_row()
ui.header("Kỹ năng", "Học mỗi tuần", "Đặt giờ/tuần cho từng kỹ năng → trang Lịch tự chèn giờ học vào giờ trống. Ghi lại điều học được sau mỗi buổi.")
ui.flash()

skills = db.skills()
logs = db.table("learn_log")
ws = today - timedelta(days=today.weekday())
we = ws + timedelta(days=6)
by_key = {s["key"]: s for s in skills}

tab_over, tab_log, tab_hist, tab_manage = st.tabs(["Tuần này", "Ghi nhật ký", "Nhật ký", "Quản lý kỹ năng"])

with tab_over:
    total_t = sum(float(s.get("hours_week") or 0) for s in skills) * 60
    total_m = sum(float(r.get("minutes") or 0) for r in logs if ws.isoformat() <= str(r.get("date", ""))[:10] <= we.isoformat())
    ui.stats([("Đã học tuần này", S.fmt_dur(total_m)), ("Mục tiêu tuần", S.fmt_dur(total_t)),
              ("Tổng giờ đã học", f"{sum(float(r.get('minutes') or 0) for r in logs) / 60:.1f} giờ")])
    st.write("")
    for s in skills:
        t = float(s.get("hours_week") or 0) * 60
        m = sum(float(r.get("minutes") or 0) for r in logs
                if r.get("skill") == s["key"] and ws.isoformat() <= str(r.get("date", ""))[:10] <= we.isoformat())
        with st.container(border=True):
            st.html(f"<b>{s['name']}</b>" + ui.bar_html(m / t if t else None, f"{S.fmt_dur(m)} / {S.fmt_dur(t)} tuần này"))
            if s.get("resources") or s.get("practice"):
                st.caption((f"📎 {s['resources']}  " if s.get("resources") else "") + (f"🛠 Thực hành: {s['practice']}" if s.get("practice") else ""))
    st.caption("Mặc định mỗi kỹ năng 1 giờ/tuần (em đặt tạm vì anh chưa chọn số giờ) — sửa ở tab Quản lý kỹ năng.")

with tab_log:
    with st.form("learn"):
        names = [s["name"] for s in skills]
        sk = st.selectbox("Kỹ năng", names)
        c1, c2 = st.columns(2)
        d = c1.date_input("Ngày", today, max_value=today, format="DD/MM/YYYY")
        minutes = c2.number_input("Số phút", 5, 480, 60, 5)
        note = st.text_area("Điều học được (1–3 ý)", placeholder="VD: Công thức tính CAC; cách đặt ngân sách thử nghiệm quảng cáo…")
        practice = st.text_input("Bài thực hành / áp dụng", placeholder="VD: Viết 1 mẫu quảng cáo cho gói Online 12 tuần")
        if st.form_submit_button("Lưu nhật ký", type="primary"):
            key = next(s["key"] for s in skills if s["name"] == sk)
            db.put("learn_log", [{"date": d.isoformat(), "skill": key, "minutes": int(minutes), "note": note.strip(), "practice": practice.strip()}])
            st.session_state["_flash"] = f"Đã ghi {int(minutes)} phút — {sk}."
            st.rerun()

with tab_hist:
    rows = [{"Ngày": r.get("date"), "Kỹ năng": by_key.get(r.get("skill"), {}).get("name", "(khác)"), "Phút": r.get("minutes"),
             "Học được": r.get("note", ""), "Thực hành": r.get("practice", "")}
            for r in sorted(logs, key=lambda r: r.get("date", ""), reverse=True)]
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("Chưa có nhật ký học.")
    unlabeled = [r for r in logs if not r.get("note") and r.get("block")]
    if unlabeled:
        st.caption(f"{len(unlabeled)} buổi học được đánh dấu từ lịch chưa ghi điều học được.")

with tab_manage:
    st.caption("Tài liệu/khoá học: ghi tên + link (anh tự chọn nguồn; em không gợi ý khoá cụ thể khi chưa kiểm chứng được).")
    edit_table(
        "skills", skills,
        {
            "name": (cc.TextColumn("Kỹ năng", required=True, width="medium"), lambda v: v, lambda v: v if v == v else None),
            "hours_week": (cc.NumberColumn("Giờ/tuần", min_value=0.0, max_value=20.0, step=0.5), lambda v: v,
                           lambda v: float(v) if v is not None and v == v else 0.0),
            "resources": (cc.TextColumn("Tài liệu / khoá học", width="large"), lambda v: v, lambda v: v if v == v else ""),
            "practice": (cc.TextColumn("Bài thực hành", width="large"), lambda v: v, lambda v: v if v == v else ""),
        },
        required=["name"], widget_key="ed_skills", defaults={"hours_week": 1.0, "order": 99},
    )
