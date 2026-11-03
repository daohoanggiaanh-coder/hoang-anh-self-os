from core.store import LocalStore, latest, make_row


def test_latest_by_key_and_delete(tmp_path):
    st = LocalStore(tmp_path)
    st.append("t", [make_row("a", {"v": 1}), make_row("b", {"v": 1})])
    st.append("t", [make_row("a", {"v": 2})])
    st.append("t", [make_row("b", None, deleted=True)])
    recs = latest(st.read("t"))
    assert recs == [{"v": 2, "key": "a"}]


def test_latest_tolerates_bad_rows():
    rows = [{"key": "", "data": "{}"}, {"key": "x", "ts": "1", "data": "not json"}]
    assert latest(rows) == [{"key": "x"}]


def test_deleted_flag_from_sheet_variants():
    rows = [{"key": "x", "ts": "1", "deleted": "1", "data": "{}"}]
    assert latest(rows) == []


def test_edit_table_merge_keeps_hidden_fields(tmp_path, monkeypatch):
    """Sửa 1 dòng trong bảng không được làm mất trường ẩn (VD 'order', 'icon')."""
    import pandas as pd
    import core.editors as E

    saved = {}
    monkeypatch.setattr(E.db, "put", lambda name, recs: saved.setdefault("put", recs))
    monkeypatch.setattr(E.db, "delete", lambda name, keys: saved.setdefault("del", keys))
    monkeypatch.setattr(E.st, "data_editor", lambda df, **kw: df.assign(name=["Mới"]))
    monkeypatch.setattr(E.st, "button", lambda *a, **k: True)
    monkeypatch.setattr(E.st, "rerun", lambda: None)
    monkeypatch.setattr(E.st, "session_state", {})
    recs = [{"key": "a", "name": "Cũ", "icon": "📖", "order": 3}]
    ident = lambda v: v  # noqa: E731
    E.edit_table("habits", recs, {"name": (None, ident, ident)}, ["name"], "w", defaults={"active": True})
    assert saved["put"] == [{"key": "a", "name": "Mới", "icon": "📖", "order": 3}]
    assert "del" not in saved


def test_filter_selfos_blocks():
    from core.db import filter_busy_events

    evs = [{"title": "A Đại (gold gym)"}, {"title": "[Self OS] Học: Tiếng Anh"}, {"title": "x", "fromSelfOS": True}]
    assert [e["title"] for e in filter_busy_events(evs)] == ["A Đại (gold gym)"]


def test_tag_atlas_keeps_only_my_color():
    from core.db import tag_atlas

    evs = [{"title": "H.Anh - Kiệt", "cal": "atlas", "color": "11"}, {"title": "Linh - Vân", "cal": "atlas", "color": ""},
           {"title": "A Đại", "cal": "__primary__", "color": "5"}]
    out = tag_atlas(evs, "atlas", "11")
    assert [e["title"] for e in out] == ["H.Anh - Kiệt", "A Đại"]
    assert out[0]["kind_override"] == "PT_Atlas" and "kind_override" not in out[1]
