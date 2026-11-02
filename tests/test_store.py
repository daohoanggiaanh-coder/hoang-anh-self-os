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
