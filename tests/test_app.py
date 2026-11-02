"""Test giao diện bằng AppTest của Streamlit (chạy app thật, không cần trình duyệt)."""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    # dữ liệu test tách riêng, không đụng data/ thật
    import core.db as db
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db._make_store.clear()
    yield
    db._make_store.clear()


def _app(password="pw"):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    if password:
        at.secrets["APP_PASSWORD"] = password
    return at


def test_login_page_and_wrong_password():
    at = _app().run()
    assert not at.exception
    at.text_input[0].input("sai")
    at.button[0].click().run()
    assert any("Sai mật khẩu" in e.value for e in at.error)


def test_login_then_today_and_schedule():
    at = _app().run()
    at.text_input[0].input("pw")
    at.button[0].click().run()
    assert not at.exception, at.exception
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "Hôm nay của tôi" in html
    assert "Burpee" in html  # lịch cố định mặc định đã được tạo


def test_remember_token_query_param():
    from core.auth import remember_token

    at = _app()
    at.query_params["k"] = remember_token("pw")
    at.run()
    assert not at.exception
    html = " ".join(h.proto.body for h in at.get("html"))
    assert "Hôm nay của tôi" in html


def test_missing_password_message():
    at = _app(password=None)
    os.environ.pop("APP_PASSWORD", None)
    at.run()
    # secrets.toml local có thể tồn tại; chỉ kiểm tra app không lỗi
    assert not at.exception


def test_version_format():
    from core.version import __version__

    parts = __version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


@pytest.mark.parametrize("page", ["views/schedule.py", "views/settings.py"])
def test_other_pages_render(page):
    from core.auth import remember_token

    at = _app()
    at.query_params["k"] = remember_token("pw")
    at.run()
    at.switch_page(page).run()
    assert not at.exception, at.exception


def test_add_task_and_propose(tmp_path):
    """Thêm 1 việc qua lớp dữ liệu rồi bấm Tạo đề xuất trên trang Lịch."""
    from core.auth import remember_token

    from core.store import LocalStore, make_row

    LocalStore(tmp_path).append("tasks", [make_row(
        "t1", {"title": "Lập kế hoạch studio", "kind": "Khó", "minutes": 60, "status": "Chờ xếp"})])
    at = _app()
    at.query_params["k"] = remember_token("pw")
    at.run()
    at.switch_page("views/schedule.py").run()
    btn = next(b for b in at.button if "Tạo đề xuất" in b.label)
    btn.click().run()
    assert not at.exception, at.exception
    labels = [b.label for b in at.button]
    assert "Nhận" in labels or any("Chưa xếp được" in w.value for w in at.warning)
