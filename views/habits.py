from datetime import timedelta

import pandas as pd
import streamlit as st

from core import db
from core import progress as P
from core import scheduler as S
from core import ui
from core.editors import edit_table

cc = st.column_config
today = ui.now_vn().date()

ui.nav_row()
ui.header("Thói quen", "Chuỗi ngày & điểm", "Đánh dấu mỗi ngày. Bỏ lỡ 1 ngày không mất điểm — chỉ cần quay lại.")
ui.flash()

data = db.progress_data()
habits = [h for h in data.habits if h.get("active", True)]
hmap = P.habit_done_map(data)

tab_check, tab_stats, tab_manage = st.tabs(["Đánh dấu", "Thống kê", "Quản lý"])

with tab_check:
    d = st.date_input("Ngày", today, max_value=today, format="DD/MM/YYYY")
    ds = d.isoformat()

    def _toggle(hk):
        db.put("habit_log", [{"key": f"{ds}|{hk}", "date": ds, "habit": hk, "done": st.session_state[f"hc_{ds}_{hk}"]}])

    for h in habits:
        stk = P.streak(hmap.get(h["key"], set()), today)
        st.checkbox(f"{h.get('icon', '•')} {h['name']}" + (f" · 🔥{stk}" if stk else ""),
                    value=d in hmap.get(h["key"], set()), key=f"hc_{ds}_{h['key']}", on_change=_toggle, args=(h["key"],))

with tab_stats:
    start = today - timedelta(days=today.weekday())
    rows = []
    for h in habits:
        dd = hmap.get(h["key"], set())
        wk_n = sum(1 for i in range(7) if start + timedelta(days=i) in dd)
        rows.append({"Thói quen": f"{h.get('icon', '')} {h['name']}", "🔥 Chuỗi": P.streak(dd, today),
                     "Kỷ lục": P.best_streak(dd), "Tuần này": f"{wk_n}/{int(h.get('per_week') or 7)}",
                     "Điểm": P.POINTS["habit"] * len(dd)})
    st.dataframe(rows, hide_index=True, width="stretch")

    st.markdown("##### 4 tuần gần đây")
    days = [today - timedelta(days=i) for i in range(27, -1, -1)]
    chart = pd.DataFrame(
        {"Ngày": pd.to_datetime([d.isoformat() for d in days]),
         "Số thói quen hoàn thành": [sum(1 for h in habits if d in hmap.get(h["key"], set())) for d in days]}
    ).set_index("Ngày")
    st.bar_chart(chart, color="#C9A45C", height=220)

    st.markdown("##### Lưới hoàn thành (28 ngày)")
    grid = {f"{h.get('icon', '')} {h['name'][:18]}": ["●" if d in hmap.get(h["key"], set()) else "·" for d in days] for h in habits}
    st.dataframe(pd.DataFrame(grid, index=[S.WEEKDAY_NAMES[d.weekday()][:5] + " " + d.strftime("%d/%m") for d in days]).T,
                 width="stretch")

with tab_manage:
    st.caption("Thêm/sửa/xoá thói quen. “Lần/tuần” = mục tiêu số ngày trong tuần (7 = hằng ngày). Tắt “Đang dùng” để ẩn mà không mất lịch sử.")
    edit_table(
        "habits", data.habits,
        {
            "icon": (cc.TextColumn("Icon", width="small"), lambda v: v, lambda v: v if v == v else "•"),
            "name": (cc.TextColumn("Thói quen", required=True, width="large"), lambda v: v, lambda v: v if v == v else None),
            "per_week": (cc.NumberColumn("Lần/tuần", min_value=1, max_value=7, step=1), lambda v: v,
                         lambda v: int(v) if v is not None and v == v else 7),
            "active": (cc.CheckboxColumn("Đang dùng"), lambda v: v if v is not None else True, lambda v: bool(v)),
        },
        required=["name"], widget_key="ed_habits", defaults={"active": True, "per_week": 7, "order": 99},
    )
