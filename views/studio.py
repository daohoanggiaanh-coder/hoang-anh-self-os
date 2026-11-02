import pandas as pd
import streamlit as st

from core import db
from core import studio as STU
from core import ui
from core.editors import edit_table, from_date, to_date

cc = st.column_config
today = ui.now_vn().date()


def vnd(x) -> str:
    try:
        return f"{float(x):,.0f}đ".replace(",", ".")
    except (TypeError, ValueError):
        return "—"


ui.nav_row()
ui.header("Studio private", "Chuẩn bị khai trương", "Lộ trình theo quý · ngân sách dự kiến & thực chi · điểm hoà vốn · bảng điều hành sau khai trương.")
ui.flash()
st.caption("⚖️ Mọi con số do anh nhập; web chỉ tính toán. Nội dung tài chính/pháp lý mang tính tham khảo — "
           "nên xác nhận với kế toán và cơ quan cấp phép tại Đồng Nai.")

cfg = next((r for r in db.table("settings") if r["key"] == "studio"),
           {"key": "studio", "area": "70–100 m²", "location": "Long Hưng / Aqua City", "budget": 150_000_000,
            "reserve": 50_000_000, "opening": ""})
tasks = db.studio_tasks()

t_road, t_budget, t_fin, t_ops, t_info = st.tabs(["Lộ trình", "Ngân sách", "Hoà vốn", "Điều hành", "Thông tin"])

# ------------------------------------------------------------- lộ trình
with t_road:
    done_n = sum(1 for t in tasks if t.get("done"))
    st.html(ui.bar_html(done_n / len(tasks) if tasks else None, f"Đã xong {done_n}/{len(tasks)} việc"))
    st.caption("Quý tính tương đối: Q1 = quý đầu tiên của lộ trình, Q4 = quý khai trương. "
               + (f"Khai trương dự kiến: **{cfg['opening']}**." if cfg.get("opening") else "Chưa chốt tháng khai trương (tab Thông tin)."))
    areas = {a: [t for t in tasks if t.get("area") == a] for a in STU.STUDIO_AREAS}
    cols = st.columns(2)
    for i, (a, ts) in enumerate(areas.items()):
        if ts:
            cols[i % 2].html(ui.bar_html(sum(1 for t in ts if t.get("done")) / len(ts), f"{a} · {sum(1 for t in ts if t.get('done'))}/{len(ts)}"))

    def _tick(k):
        t = next(x for x in tasks if x["key"] == k)
        val = st.session_state[f"st_{k}"]
        db.put("studio_tasks", [{**t, "done": val, "done_date": today.isoformat() if val else None}])

    for q in ["Q1", "Q2", "Q3", "Q4"]:
        qs = [t for t in tasks if t.get("quarter") == q]
        if not qs:
            continue
        with st.expander(f"{q} · {sum(1 for t in qs if t.get('done'))}/{len(qs)}", expanded=q == min(
                (t.get("quarter") for t in tasks if not t.get("done")), default="Q1")):
            for t in qs:
                st.checkbox(f"{t['task']}  ·  _{t.get('area', '')}_", value=bool(t.get("done")), key=f"st_{t['key']}",
                            on_change=_tick, args=(t["key"],))
    with st.expander("Thêm / sửa / xoá việc"):
        edit_table(
            "studio_tasks", tasks,
            {
                "quarter": (cc.SelectboxColumn("Quý", options=["Q1", "Q2", "Q3", "Q4", "Sau KT"], required=True), lambda v: v, lambda v: v),
                "area": (cc.SelectboxColumn("Hạng mục", options=STU.STUDIO_AREAS, required=True), lambda v: v, lambda v: v),
                "task": (cc.TextColumn("Việc", required=True, width="large"), lambda v: v, lambda v: v if v == v else None),
                "due": (cc.DateColumn("Hạn", format="DD/MM/YYYY"), to_date, from_date),
                "done": (cc.CheckboxColumn("Xong"), lambda v: bool(v), lambda v: bool(v)),
            },
            required=["quarter", "area", "task"], widget_key="ed_studio", defaults={"order": 999},
        )

# ------------------------------------------------------------- ngân sách
with t_budget:
    budget = db.table("studio_budget")
    plan = sum(float(r.get("planned") or 0) for r in budget)
    actual = sum(float(r.get("actual") or 0) for r in budget)
    cap = float(cfg.get("budget") or 0)
    reserve = float(cfg.get("reserve") or 0)
    ui.stats([("Ngân sách chính", vnd(cap)), ("Dự phòng", vnd(reserve)), ("Dự kiến (tổng dòng)", vnd(plan)), ("Đã chi", vnd(actual))])
    st.write("")
    if plan > cap:
        st.warning(f"Tổng dự kiến vượt ngân sách chính {vnd(plan - cap)} — sẽ phải dùng quỹ dự phòng.")
    if actual > cap + reserve:
        st.error("Thực chi đã vượt cả ngân sách chính + dự phòng.")
    st.caption("Em không điền sẵn số tiền cho từng hạng mục vì chưa có báo giá thật — anh nhập theo báo giá.")
    edit_table(
        "studio_budget", budget,
        {
            "category": (cc.SelectboxColumn("Hạng mục", options=STU.BUDGET_CATEGORIES, required=True), lambda v: v, lambda v: v),
            "item": (cc.TextColumn("Chi tiết", required=True, width="large"), lambda v: v, lambda v: v if v == v else None),
            "planned": (cc.NumberColumn("Dự kiến (đ)", min_value=0, step=500000, format="%d"), lambda v: v,
                        lambda v: float(v) if v is not None and v == v else None),
            "actual": (cc.NumberColumn("Thực chi (đ)", min_value=0, step=500000, format="%d"), lambda v: v,
                       lambda v: float(v) if v is not None and v == v else None),
            "note": (cc.TextColumn("Ghi chú / nguồn báo giá"), lambda v: v, lambda v: v if v == v else ""),
        },
        required=["category", "item"], widget_key="ed_budget",
    )
    if budget:
        df = pd.DataFrame(budget).groupby("category")[["planned", "actual"]].sum(numeric_only=True)
        df.columns = ["Dự kiến", "Thực chi"]
        st.bar_chart(df, color=["#8C877C", "#C9A45C"], height=240, stack=False)

# ------------------------------------------------------------- hoà vốn
with t_fin:
    fin = next((r for r in db.table("settings") if r["key"] == "studio_fin"), {"key": "studio_fin"})
    with st.form("fin"):
        st.markdown("**Chi phí cố định mỗi tháng**")
        c1, c2, c3 = st.columns(3)
        rent = c1.number_input("Tiền thuê (đ)", 0, None, int(fin.get("rent") or 0), 500000,
                               help="Đây là con số quan trọng nhất còn chưa xác nhận — nhập giá thuê thật khi khảo sát.")
        staff = c2.number_input("Lương cố định (đ)", 0, None, int(fin.get("staff") or 0), 500000)
        util = c3.number_input("Điện nước, internet (đ)", 0, None, int(fin.get("util") or 0), 100000)
        c1, c2, c3 = st.columns(3)
        soft = c1.number_input("Phần mềm, khác (đ)", 0, None, int(fin.get("soft") or 0), 100000)
        mkt = c2.number_input("Marketing cố định (đ)", 0, None, int(fin.get("mkt") or 0), 100000)
        depr = c3.number_input("Khấu hao thiết bị/tháng (đ)", 0, None, int(fin.get("depr") or 0), 100000,
                               help="VD: tổng tiền thiết bị ÷ số tháng dự kiến dùng")
        st.markdown("**Mỗi khách / tháng**")
        c1, c2 = st.columns(2)
        price = c1.number_input("Doanh thu TB/khách/tháng (đ)", 0, None, int(fin.get("price") or 0), 100000)
        var = c2.number_input("Chi phí biến đổi/khách/tháng (đ)", 0, None, int(fin.get("var") or 0), 50000,
                              help="VD hoa hồng HLV, khăn, nước, đồ tiêu hao")
        if st.form_submit_button("Tính & lưu", type="primary"):
            db.put("settings", [{"key": "studio_fin", "rent": rent, "staff": staff, "util": util, "soft": soft, "mkt": mkt,
                                 "depr": depr, "price": price, "var": var}])
            st.rerun()
    fixed = sum(int(fin.get(k) or 0) for k in ("rent", "staff", "util", "soft", "mkt", "depr"))
    be = STU.breakeven(fixed, float(fin.get("price") or 0), float(fin.get("var") or 0))
    if fixed and be:
        ui.stats([("Chi phí cố định/tháng", vnd(fixed)), ("Lãi gộp/khách", vnd(float(fin['price']) - float(fin['var']))),
                  ("Hoà vốn", f"{be:.1f} khách/tháng")])
        startup = float(cfg.get("budget") or 0)
        st.caption(f"Công thức: chi phí cố định ÷ (doanh thu − chi phí biến đổi mỗi khách). "
                   f"Muốn thu hồi vốn {vnd(startup)} trong 12 tháng cần thêm khoảng "
                   f"{startup / 12 / (float(fin['price']) - float(fin['var'])):.1f} khách/tháng trên mức hoà vốn (chưa tính thuế).")
    elif fixed and not be:
        st.error("Doanh thu mỗi khách đang ≤ chi phí biến đổi — mô hình lỗ trên từng khách.")
    else:
        st.info("Nhập số liệu để tính điểm hoà vốn.")

# ------------------------------------------------------------- điều hành
with t_ops:
    st.caption("Dùng sau khai trương: nhập số liệu mỗi tháng, web tự tính lợi nhuận, tỉ lệ gia hạn, chi phí/khách, CAC.")
    months = db.table("studio_monthly")
    edit_table(
        "studio_monthly", months,
        {
            "month": (cc.TextColumn("Tháng (MM/YYYY)", required=True), lambda v: v, lambda v: v if v == v else None),
            "revenue": (cc.NumberColumn("Doanh thu", min_value=0, format="%d"), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
            "cost": (cc.NumberColumn("Tổng chi phí", min_value=0, format="%d"), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
            "clients": (cc.NumberColumn("Số khách đang tập", min_value=0), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
            "new_clients": (cc.NumberColumn("Khách mới", min_value=0), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
            "due_renew": (cc.NumberColumn("Đến hạn gia hạn", min_value=0), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
            "renewed": (cc.NumberColumn("Đã gia hạn", min_value=0), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
            "marketing": (cc.NumberColumn("Chi marketing", min_value=0, format="%d"), lambda v: v, lambda v: float(v) if v == v and v is not None else None),
        },
        required=["month"], widget_key="ed_monthly",
    )
    if months:
        rows = []
        for m in sorted(months, key=lambda r: (str(r.get("month", ""))[-4:], str(r.get("month", ""))[:2])):
            k = STU.monthly_kpis(m)
            pct = lambda v: f"{v:.0%}" if v is not None else "—"  # noqa: E731
            rows.append({"Tháng": m["month"], "Doanh thu": vnd(m.get("revenue")), "Lợi nhuận": vnd(k["profit"]),
                         "Biên LN": pct(k["margin"]), "Gia hạn": pct(k["renew_rate"]), "Chi phí/khách": vnd(k["cost_per_client"]),
                         "CAC": vnd(k["cac"]) if k["cac"] is not None else "—", "DT/khách": vnd(k["rev_per_client"])})
        st.dataframe(rows, hide_index=True, width="stretch")

# ------------------------------------------------------------- thông tin
with t_info:
    with st.form("studio_info"):
        c1, c2 = st.columns(2)
        area = c1.text_input("Diện tích", cfg.get("area", ""))
        loc = c2.text_input("Khu vực", cfg.get("location", ""))
        b = c1.number_input("Ngân sách chính (đ)", 0, None, int(cfg.get("budget") or 0), 1_000_000)
        r = c2.number_input("Dự phòng (đ)", 0, None, int(cfg.get("reserve") or 0), 1_000_000)
        op = st.text_input("Tháng khai trương dự kiến (MM/YYYY)", cfg.get("opening", ""))
        if st.form_submit_button("Lưu", type="primary"):
            db.put("settings", [{"key": "studio", "area": area, "location": loc, "budget": b, "reserve": r, "opening": op}])
            st.rerun()
