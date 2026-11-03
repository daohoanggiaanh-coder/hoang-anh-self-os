"""Đăng nhập 1 tài khoản. Mật khẩu nằm trong Secrets (APP_PASSWORD).

Ghi nhớ đăng nhập (2 lớp):
1. Cookie `selfos_k` lưu 180 ngày trên trình duyệt / app đã cài.
2. Dự phòng: địa chỉ có ?k=<mã>. Nếu trình duyệt chặn cookie, anh lưu/cài app
   từ địa chỉ có ?k= là lần sau vào thẳng.
Mã được tạo từ mật khẩu (HMAC), không chứa mật khẩu. Đổi mật khẩu → mã cũ hết hiệu lực.
"""
from __future__ import annotations

import hashlib
import hmac

import streamlit as st

from core.db import _secret

COOKIE = "selfos_k"
MAX_AGE = 180 * 24 * 3600


def _password() -> str | None:
    return _secret("APP_PASSWORD")


def remember_token(password: str) -> str:
    return hmac.new(password.encode(), b"selfos-remember-v1", hashlib.sha256).hexdigest()[:32]


def check_password(entered: str) -> bool:
    pw = _password()
    return bool(pw) and hmac.compare_digest(entered.encode(), pw.encode())


def _cookie_value() -> str | None:
    try:
        return st.context.cookies.get(COOKIE)
    except Exception:
        return None


def is_logged_in() -> bool:
    if st.session_state.get("auth"):
        return True
    pw = _password()
    if not pw or st.session_state.get("_logged_out"):
        return False
    tok = remember_token(pw)
    for cand in (st.query_params.get("k"), _cookie_value()):
        if cand and hmac.compare_digest(str(cand), tok):
            st.session_state["auth"] = True
            return True
    return False


def _set_cookie_js(value: str, max_age: int):
    st.iframe(
        f"""<script>
        try {{ window.parent.document.cookie = "{COOKIE}={value}; max-age={max_age}; path=/; SameSite=Lax; Secure"; }}
        catch (e) {{ document.cookie = "{COOKIE}={value}; max-age={max_age}; path=/; SameSite=Lax"; }}
        </script>""",
        height=1,
    )


def login(remember: bool):
    st.session_state.pop("_logged_out", None)
    st.session_state.pop("_cookie_cleared", None)
    st.session_state["auth"] = True
    if remember:
        tok = remember_token(_password())
        st.session_state["_set_cookie"] = tok
        st.query_params["k"] = tok


def apply_pending_cookie():
    """Gọi sau khi đã render trang (cookie phải ghi bằng JS ở lượt chạy kế tiếp)."""
    tok = st.session_state.pop("_set_cookie", None)
    if tok:
        _set_cookie_js(tok, MAX_AGE)


def logout():
    """Đăng xuất: xoá phiên + query; cookie được xoá khi trang đăng nhập hiện ra."""
    st.session_state.pop("auth", None)
    st.session_state["_logged_out"] = True
    st.query_params.clear()


def clear_cookie_if_logged_out():
    if st.session_state.get("_logged_out") and not st.session_state.get("_cookie_cleared"):
        _set_cookie_js("", 0)
        st.session_state["_cookie_cleared"] = True


def restore_from_cookie():
    """Streamlit Cloud không chuyển cookie vào st.context, và iframe bị chặn chuyển trang.
    Cách làm: JS đọc cookie rồi điền vào 1 ô nhập ẩn → Python nhận mã → so khớp → đăng nhập."""
    if st.session_state.get("_logged_out"):
        return
    pw = _password()
    with st.container(key="so_ck"):
        val = st.text_input("ck", key="_ck", label_visibility="collapsed")
    if val and pw and hmac.compare_digest(str(val), remember_token(pw)):
        st.session_state["auth"] = True
        st.query_params["k"] = val
        st.rerun()
    if st.session_state.get("_ck_tries", 0) >= 3:
        return
    st.session_state["_ck_tries"] = st.session_state.get("_ck_tries", 0) + 1
    st.iframe(
        f"""<script>
        (function fill(n) {{
          try {{
            const d = window.parent.document;
            const m = d.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('{COOKIE}='));
            const v = m ? m.split('=')[1] : '';
            if (!v || v.length < 16) return;
            const el = d.querySelector('.st-key-so_ck input');
            if (!el) {{ if (n < 20) setTimeout(() => fill(n + 1), 150); return; }}
            const set = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
            set.call(el, v);
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Enter', code: 'Enter', keyCode: 13, bubbles: true }}));
            el.blur();
          }} catch (e) {{}}
        }})(0);
        </script>""",
        height=1,
    )
