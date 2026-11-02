from datetime import timedelta

import pandas as pd
import streamlit as st

from core import db
from core import scheduler as S
from core import ui
from core.editors import edit_table, to_date
from core.images import b64_to_bytes, compress_to_b64

cc = st.column_config
today = ui.now_vn().date()
ds = today.isoformat()

DEFAULT_LOOK = [
    ("Da – sáng", "Rửa mặt"), ("Da – sáng", "Dưỡng ẩm"), ("Da – sáng", "Kem chống nắng"),
    ("Da – tối", "Rửa mặt / làm sạch"), ("Da – tối", "Dưỡng ẩm / sản phẩm đặc trị (nếu có)"),
    ("Tóc", "Tạo kiểu gọn trước khi đi làm"),
    ("Tư thế", "5 phút mở ngực – kéo giãn cơ gập hông"), ("Tư thế", "Tự kiểm tra tư thế khi đứng dạy / ngồi làm việc"),
    ("Trang phục", "Đồ đi làm đã chuẩn bị từ tối hôm trước"),
]

ui.nav_row()
ui.header("Vẻ ngoài", "Hình ảnh chuyên nghiệp", "Checklist hằng ngày · số đo · ảnh tiến độ 4 tuần · tóc · tủ đồ tối giản.")
ui.flash()

if not any(r.get("key") == "seeded_look" for r in db.table("settings")):
    if not db.table("look_items"):
        db.put("look_items", [{"group": g, "item": i, "order": n} for n, (g, i) in enumerate(DEFAULT_LOOK)])
    db.put("settings", [{"key": "seeded_look", "done": True}])
items = sorted(db.table("look_items"), key=lambda r: r.get("order", 99))
look_cfg = next((r for r in db.table("settings") if r["key"] == "looks"), {"key": "looks", "hair_weeks": 3, "last_haircut": None})

t_check, t_body, t_photo, t_hair, t_wardrobe, t_manage = st.tabs(
    ["Hôm nay", "Số đo", "Ảnh tiến độ", "Tóc", "Tủ đồ", "Sửa checklist"])

# ------------------------------------------------------------- checklist
with t_check:
    rec = next((r for r in db.table("look_log") if r["key"] == ds), {"key": ds, "date": ds, "done": []})
    done = set(rec.get("done") or [])

    def _save():
        sel = [it["key"] for it in items if st.session_state.get(f"lk_{it['key']}")]
        db.put("look_log", [{"key": ds, "date": ds, "done": sel, "total": len(items)}])

    for grp in dict.fromkeys(it["group"] for it in items):
        st.markdown(f"**{grp}**")
        for it in [x for x in items if x["group"] == grp]:
            st.checkbox(it["item"], value=it["key"] in done, key=f"lk_{it['key']}", on_change=_save)
    st.html(ui.bar_html(len(done) / len(items) if items else None, f"Hoàn thành {len(done)}/{len(items)}"))

# ------------------------------------------------------------- số đo
with t_body:
    body = sorted(db.table("body"), key=lambda r: r.get("date", ""))
    with st.form("body"):
        c1, c2, c3, c4 = st.columns(4)
        d = c1.date_input("Ngày", today, max_value=today, format="DD/MM/YYYY")
        w = c2.number_input("Cân nặng (kg)", 0.0, 200.0, float(body[-1]["weight"]) if body and body[-1].get("weight") else 0.0, 0.1)
        bf = c3.number_input("% mỡ", 0.0, 60.0, float(body[-1]["bodyfat"]) if body and body[-1].get("bodyfat") else 0.0, 0.1)
        waist = c4.number_input("Vòng eo (cm)", 0.0, 200.0, float(body[-1]["waist"]) if body and body[-1].get("waist") else 0.0, 0.5)
        src = st.selectbox("Đo bằng", ["InBody", "Cân điện tử", "Thước dây", "Khác"])
        if st.form_submit_button("Lưu số đo", type="primary"):
            db.put("body", [{"key": d.isoformat(), "date": d.isoformat(), "weight": w or None, "bodyfat": bf or None,
                             "waist": waist or None, "source": src}])
            st.session_state["_flash"] = "Đã lưu số đo."
            st.rerun()
    if body:
        df = pd.DataFrame(body).set_index("date")[["weight", "bodyfat", "waist"]].apply(pd.to_numeric, errors="coerce")
        first, last = df.iloc[0], df.iloc[-1]
        ui.stats([(lab, f"{last[c]:.1f} ({last[c] - first[c]:+.1f})") for c, lab in
                  [("weight", "Cân (kg)"), ("bodyfat", "% mỡ"), ("waist", "Eo (cm)")] if pd.notna(last[c]) and pd.notna(first[c])])
        st.caption("Trong ngoặc: thay đổi so với lần đo đầu tiên. Nên đo cùng điều kiện (giờ, trước ăn, cùng máy) để so sánh được.")
        for c, lab in [("weight", "Cân nặng (kg)"), ("bodyfat", "% mỡ"), ("waist", "Vòng eo (cm)")]:
            if df[c].notna().sum() >= 2:
                st.markdown(f"**{lab}**")
                st.line_chart(df[c].dropna(), color="#C9A45C", height=180)
    else:
        st.info("Chưa có số đo.")

# ------------------------------------------------------------- ảnh tiến độ
with t_photo:
    photos = sorted(db.table("photos"), key=lambda r: r.get("date", ""))
    last_photo = to_date(photos[-1]["date"]) if photos else None
    next_due = (last_photo + timedelta(weeks=4)) if last_photo else today
    if next_due <= today:
        st.html('<div class="so-warn">📸 Đến kỳ chụp ảnh tiến độ (mỗi 4 tuần). Chụp cùng góc, cùng ánh sáng, cùng giờ.</div>')
    else:
        st.caption(f"Lần chụp tiếp theo: {S.vn_date(next_due, True)}")
    with st.form("photo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        pd_ = c1.date_input("Ngày chụp", today, max_value=today, format="DD/MM/YYYY")
        angle = c2.selectbox("Góc", ["Trước", "Nghiêng", "Sau"])
        up = st.file_uploader("Ảnh", type=["jpg", "jpeg", "png", "webp"])
        if st.form_submit_button("Lưu ảnh", type="primary") and up:
            try:
                b64 = compress_to_b64(up.getvalue())
                db.put("photos", [{"date": pd_.isoformat(), "angle": angle, "img": b64}])
                st.session_state["_flash"] = "Đã lưu ảnh (đã nén để lưu vào Sheet riêng tư của anh)."
                st.rerun()
            except Exception as e:
                st.error(f"Không đọc được ảnh: {e}")
    st.caption("Ảnh được nén nhỏ (~30 KB) và lưu trong Google Sheet riêng của anh, không đăng ở đâu khác.")
    if len(photos) >= 1:
        dates = sorted({p["date"] for p in photos})
        c1, c2, c3 = st.columns(3)
        a = c1.selectbox("Trước", dates, index=0)
        b = c2.selectbox("Sau", dates, index=len(dates) - 1)
        ang = c3.selectbox("Góc ", ["Trước", "Nghiêng", "Sau"])
        x, y = st.columns(2)
        for col, dd in ((x, a), (y, b)):
            p = next((p for p in photos if p["date"] == dd and p.get("angle") == ang), None)
            with col:
                st.markdown(f"**{S.vn_date(to_date(dd), True)}**")
                if p:
                    st.image(b64_to_bytes(p["img"]), width="stretch")
                else:
                    st.caption("Không có ảnh góc này.")

# ------------------------------------------------------------- tóc
with t_hair:
    with st.form("hair"):
        c1, c2 = st.columns(2)
        last = c1.date_input("Lần cắt gần nhất", to_date(look_cfg.get("last_haircut")) or today, max_value=today, format="DD/MM/YYYY")
        weeks = c2.number_input("Cắt mỗi … tuần", 1, 12, int(look_cfg.get("hair_weeks") or 3))
        if st.form_submit_button("Lưu", type="primary"):
            db.put("settings", [{**look_cfg, "last_haircut": last.isoformat(), "hair_weeks": int(weeks)}])
            st.rerun()
    if look_cfg.get("last_haircut"):
        nd = to_date(look_cfg["last_haircut"]) + timedelta(weeks=int(look_cfg.get("hair_weeks") or 3))
        left = (nd - today).days
        st.info(f"Lần cắt tiếp theo: **{S.vn_date(nd, True)}** " + (f"(còn {left} ngày)" if left >= 0 else f"(trễ {-left} ngày)"))
        if 0 <= left <= 3:
            st.caption("Gợi ý: thêm “Cắt tóc (45')” vào Việc cần xếp ở trang Lịch để web tìm giờ.")

# ------------------------------------------------------------- tủ đồ
with t_wardrobe:
    st.caption("Tủ đồ tối giản: liệt kê món đang có và món cần mua; đặt tháng dự kiến mua + ngân sách để không mua bốc đồng.")
    edit_table(
        "wardrobe", db.table("wardrobe"),
        {
            "item": (cc.TextColumn("Món đồ", required=True, width="medium"), lambda v: v, lambda v: v if v == v else None),
            "category": (cc.SelectboxColumn("Loại", options=["Áo đi dạy", "Quần đi dạy", "Áo sơ mi / polo", "Quần âu / chinos",
                                                              "Giày", "Áo khoác", "Phụ kiện", "Khác"]), lambda v: v, lambda v: v),
            "status": (cc.SelectboxColumn("Trạng thái", options=["Đang có", "Cần mua", "Cần thay", "Đã bỏ"]), lambda v: v, lambda v: v),
            "month": (cc.TextColumn("Tháng mua (VD 12/2026)"), lambda v: v, lambda v: v if v == v else ""),
            "budget": (cc.NumberColumn("Ngân sách (đ)", min_value=0, step=50000, format="%d"), lambda v: v,
                       lambda v: int(v) if v is not None and v == v else None),
        },
        required=["item"], widget_key="ed_wardrobe", defaults={"status": "Đang có"},
    )
    wr = db.table("wardrobe")
    need = [r for r in wr if r.get("status") in ("Cần mua", "Cần thay")]
    if need:
        st.markdown(f"**Cần mua:** {len(need)} món · tổng ngân sách {sum(int(r.get('budget') or 0) for r in need):,}đ".replace(",", "."))

# ------------------------------------------------------------- sửa checklist
with t_manage:
    edit_table(
        "look_items", items,
        {
            "group": (cc.SelectboxColumn("Nhóm", options=["Da – sáng", "Da – tối", "Tóc", "Tư thế", "Trang phục", "Khác"], required=True),
                      lambda v: v, lambda v: v),
            "item": (cc.TextColumn("Việc", required=True, width="large"), lambda v: v, lambda v: v if v == v else None),
        },
        required=["group", "item"], widget_key="ed_look", defaults={"order": 99},
    )
