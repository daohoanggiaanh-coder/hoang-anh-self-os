import streamlit as st

from core import auth, db
from core import scheduler as S
from core import ui
from core.editors import from_time, to_time
from core.version import __version__

ui.nav_row()
ui.header("Cài đặt", "Cá nhân hoá", "Giờ năng lượng, đệm, ngưỡng cảnh báo, kết nối Google.")

flash = st.session_state.pop("_flash", None)
if flash:
    st.success(flash)

s = db.settings()
with st.form("settings"):
    st.markdown("##### Năng lượng trong ngày")
    a, b = st.columns(2)
    peak_s = a.time_input("Tỉnh táo nhất — từ", to_time(s["peak_start"]), step=900)
    peak_e = b.time_input("đến", to_time(s["peak_end"]), step=900)
    low_s = a.time_input("Hay mệt — từ", to_time(s["low_start"]), step=900)
    low_e = b.time_input("đến ", to_time(s["low_end"]), step=900)
    day_s = a.time_input("Chỉ xếp việc từ", to_time(s["day_start"]), step=900)
    day_e = b.time_input("đến  ", to_time(s["day_end"]), step=900)

    st.markdown("##### Quy tắc xếp lịch")
    a, b = st.columns(2)
    buffer_min = a.number_input("Đệm giữa các khối (phút)", 0, 60, int(s["buffer_min"]), 5)
    commute = b.number_input("Đi lại trước/sau ca PT (phút)", 0, 90, int(s["commute_min"]), 5)
    min_slot = a.number_input("Khoảng trống tối thiểu (phút)", 15, 120, int(s["min_slot"]), 15)
    max_deep = b.number_input("Tối đa việc khó + học mỗi ngày (phút)", 30, 600, int(s["max_deep_min"]), 15)

    st.markdown("##### Ngưỡng nhắc nhẹ")
    a, b = st.columns(2)
    sleep_t = a.number_input("Ngủ tối thiểu (giờ/đêm)", 5.0, 10.0, int(s["sleep_target_min"]) / 60, 0.5)
    work_lim = b.number_input("Giờ làm việc tối đa / tuần", 20, 100, int(float(s["work_week_limit_h"])), 1)
    st.caption("Ngưỡng do anh tự đặt. 7 giờ ngủ là mức khuyến nghị chung cho người trưởng thành (AASM & SRS, 2015); "
               "55 giờ/tuần là mốc WHO/ILO dùng trong báo cáo 2021 về làm việc kéo dài — chỉ để tham khảo.")

    st.markdown("##### Google Calendar")
    cal = st.text_input("Tên lịch chứa ca PT", s.get("pt_calendar", "PT"))
    read_primary = st.toggle("Đọc cả lịch chính (mọi sự kiện trên lịch chính tính là giờ bận, có cộng giờ đi lại)",
                             bool(s.get("read_primary", True)))
    write_gcal = st.toggle("Khi bấm “Nhận” đề xuất → tạo sự kiện riêng tư trên lịch chính", bool(s.get("write_gcal", True)))

    if st.form_submit_button("Lưu cài đặt", type="primary"):
        db.save_settings(
            {
                "peak_start": from_time(peak_s), "peak_end": from_time(peak_e),
                "low_start": from_time(low_s), "low_end": from_time(low_e),
                "day_start": from_time(day_s), "day_end": from_time(day_e),
                "buffer_min": int(buffer_min), "commute_min": int(commute), "min_slot": int(min_slot),
                "max_deep_min": int(max_deep), "sleep_target_min": int(round(sleep_t * 60)),
                "work_week_limit_h": int(work_lim), "pt_calendar": cal.strip() or "PT", "write_gcal": bool(write_gcal),
                "read_primary": bool(read_primary),
            }
        )
        db.invalidate_calendar()
        st.session_state["_flash"] = "Đã lưu cài đặt."
        st.rerun()

st.markdown("##### Giao diện sáng / tối")
st.markdown(
    "<div class='so-muted'>Mặc định web theo chế độ sáng/tối của điện thoại. Muốn cố định: bấm <b>⋮</b> (góc trên phải) "
    "→ <b>Settings</b> → <b>Choose app theme</b> → Light / Dark. Giao diện hiện tại: "
    f"<b>{'Tối' if ui.is_dark() else 'Sáng'}</b>.</div>",
    unsafe_allow_html=True,
)

st.markdown("##### Kết nối dữ liệu")
if db.is_local():
    st.warning("Đang lưu tạm trên máy chủ (chế độ thử). Trên Streamlit Cloud dữ liệu này có thể mất khi app khởi động lại — "
               "anh làm Bước 2 trong README để nối Google Sheets.")
else:
    st.success("Đang lưu vào Google Sheets qua Apps Script.")
    if st.button("Kiểm tra kết nối"):
        try:
            db.store()._call({"action": "ping"})
            db.invalidate_calendar()
            wd = S.week_days(ui.now_vn().date())
            evs, err = db.pt_events(wd[0].isoformat(), wd[-1].isoformat())
            if err:
                st.error(err)
            else:
                st.success(f"Kết nối tốt. Tuần này đọc được {len(evs)} sự kiện bận từ Google Calendar.")
        except Exception as e:
            st.error(str(e))

st.divider()
c1, c2 = st.columns([3, 1])
c1.markdown(f"<span class='so-ver'>HOÀNG ANH · SELF OS — phiên bản {__version__}</span>", unsafe_allow_html=True)
if c2.button("Đăng xuất", width="stretch"):
    auth.logout()
    st.rerun()
