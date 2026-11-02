from datetime import timedelta

import streamlit as st

from core import db
from core import scheduler as S
from core import ui
from core.editors import edit_table

cc = st.column_config
now = ui.now_vn()
today = now.date()

ui.nav_row()
ui.header("Mục tiêu", "Năm → Quý → Tuần", "Kiểu OKR: mục tiêu (O) + kết quả then chốt đo được (KR). Mỗi sáng chọn Top 3 phục vụ mục tiêu tuần.")
ui.flash()

goals = db.table("goals")
y = today.year
q = (today.month - 1) // 3 + 1
iso = today.isocalendar()
default_period = {"Năm": str(y + 1 if today.month >= 11 else y), "Quý": f"Q{q}/{y}", "Tuần": f"T{iso.week}/{iso.year}"}
parent_of = {"Quý": "Năm", "Tuần": "Quý"}

tabs = st.tabs(["Tổng quan", "Năm", "Quý", "Tuần", "Lịch sử Top 3"])

with tabs[0]:
    if not goals:
        st.info("Chưa có mục tiêu. Bắt đầu ở tab **Năm**: 3–5 mục tiêu lớn (VD: khai trương studio, kỷ luật thói quen, hình ảnh chuyên nghiệp).")
    for g in sorted([g for g in goals if g.get("level") == "Năm"], key=lambda g: g.get("title", "")):
        with st.container(border=True):
            st.markdown(f"**{g.get('title')}** · _{g.get('period', '')}_")
            st.html(ui.bar_html((g.get("progress") or 0) / 100, f"Tiến độ {int(g.get('progress') or 0)}% · {g.get('status', '')}"))
            if g.get("kr"):
                st.caption(g["kr"])
            for c in [x for x in goals if x.get("parent") == g.get("title") and x.get("level") == "Quý"]:
                st.markdown(f"&nbsp;&nbsp;↳ **{c.get('title')}** ({c.get('period', '')}) — {int(c.get('progress') or 0)}%")
                for w in [x for x in goals if x.get("parent") == c.get("title") and x.get("level") == "Tuần"]:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;↳ {w.get('title')} ({w.get('period', '')}) — {int(w.get('progress') or 0)}%")

for tab, level in zip(tabs[1:4], ["Năm", "Quý", "Tuần"]):
    with tab:
        recs = [g for g in goals if g.get("level") == level]
        parents = sorted({g.get("title") for g in goals if g.get("level") == parent_of.get(level)} - {None})
        cols = {
            "period": (cc.TextColumn("Kỳ", help=f"VD {default_period[level]}"), lambda v: v, lambda v: v if v == v else None),
            "title": (cc.TextColumn("Mục tiêu", required=True, width="large"), lambda v: v, lambda v: v if v == v else None),
        }
        if level != "Năm":
            cols["parent"] = (cc.SelectboxColumn(f"Thuộc mục tiêu {parent_of[level]}", options=parents), lambda v: v, lambda v: v)
        cols |= {
            "kr": (cc.TextColumn("Kết quả then chốt (đo được)", width="large"), lambda v: v, lambda v: v if v == v else None),
            "progress": (cc.NumberColumn("%", min_value=0, max_value=100, step=5), lambda v: v,
                         lambda v: int(v) if v is not None and v == v else 0),
            "status": (cc.SelectboxColumn("Trạng thái", options=["Đang làm", "Đạt", "Tạm dừng", "Bỏ"]), lambda v: v, lambda v: v),
        }
        st.caption(f"Kỳ gợi ý: **{default_period[level]}**. KR nên có con số và hạn, VD “Ký hợp đồng mặt bằng trước 31/03”.")
        edit_table("goals", recs, cols, required=["title"], widget_key=f"ed_goals_{level}",
                   defaults={"level": level, "period": default_period[level], "status": "Đang làm", "progress": 0})

with tabs[4]:
    rows = []
    for i in range(14):
        d = today - timedelta(days=i)
        r = db.daily(d.isoformat())
        top = [t for t in r["top3"] if str(t.get("text", "")).strip()]
        rows.append({
            "Ngày": S.vn_date(d),
            "Top 3": " · ".join(("✅ " if t.get("done") else "▫️ ") + t["text"] for t in top) or "—",
            "Xong": f"{sum(1 for t in top if t.get('done'))}/{len(top)}" if top else "",
            "Tổng kết": " / ".join(x for x in (r.get("review") or []) if str(x).strip()),
        })
    st.dataframe(rows, hide_index=True, width="stretch")
