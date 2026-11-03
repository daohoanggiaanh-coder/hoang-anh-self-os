"""Hoàng Anh · Self OS — điểm vào."""
import streamlit as st

from core import auth, ui
from core.version import __version__

st.set_page_config(
    page_title="Hoàng Anh · Self OS",
    page_icon="static/icon-192.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ui.inject_css()
ui.inject_head()


def login_page():
    auth.clear_cookie_if_logged_out()
    auth.restore_from_cookie_js()
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.write("")
        st.image("static/icon-512.png", width=88)
        ui.header("Hoàng Anh · Self OS", "Đăng nhập", "Học · Làm · Theo dõi · Phát triển — mỗi ngày.")
        if not auth._password():
            st.error("Chưa đặt mật khẩu. Thêm APP_PASSWORD vào Secrets (xem README).")
            return
        with st.form("login"):
            pw = st.text_input("Mật khẩu", type="password")
            remember = st.checkbox("Ghi nhớ đăng nhập trên máy này", value=True)
            if st.form_submit_button("Vào", type="primary", width="stretch"):
                if auth.check_password(pw):
                    auth.login(remember)
                    st.rerun()
                else:
                    st.error("Sai mật khẩu.")
        st.markdown(f"<div class='so-ver' style='text-align:center'>phiên bản {__version__}</div>", unsafe_allow_html=True)


if not auth.is_logged_in():
    st.navigation([st.Page(login_page, title="Đăng nhập", icon="🔐")], position="hidden").run()
else:
    auth.apply_pending_cookie()
    pages = [st.Page(path, title=label, icon=icon, default=(i == 0)) for i, (path, label, icon) in enumerate(ui.NAV)]
    st.navigation(pages, position="hidden").run()  # dùng thanh chuyển trang riêng (ui.nav_row)
