"""Bảng nhập liệu dạng lưới (st.data_editor) + lưu thay đổi theo key."""
from __future__ import annotations

from datetime import date, time

import pandas as pd
import streamlit as st

from core import db


def to_time(s) -> time | None:
    try:
        h, m = str(s).split(":")[:2]
        h, m = int(h), int(m)
        return time(23, 59) if h >= 24 else time(h, m)
    except (ValueError, AttributeError):
        return None


def from_time(t) -> str | None:
    if t is None or (isinstance(t, float) and pd.isna(t)):
        return None
    if isinstance(t, str):
        return t[:5]
    return f"{t.hour:02d}:{t.minute:02d}"


def to_date(s) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def from_date(d) -> str | None:
    if d is None or (isinstance(d, float) and pd.isna(d)) or d is pd.NaT:
        return None
    if isinstance(d, str):
        return d[:10] or None
    try:
        return d.isoformat()[:10]
    except AttributeError:
        return None


def _blank(v) -> bool:
    return v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT or v == ""


def edit_table(
    name: str,
    records: list[dict],
    columns: dict,  # field -> (column_config, to_ui, from_ui)
    required: list[str],
    widget_key: str,
    defaults: dict | None = None,
):
    """Hiển thị lưới, trả về True nếu đã lưu."""
    fields = list(columns)
    rows = [{"key": r.get("key")} | {f: columns[f][1](r.get(f)) for f in fields} for r in records]
    df = pd.DataFrame(rows, columns=["key"] + fields)
    edited = st.data_editor(
        df,
        key=widget_key,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        column_order=fields,
        column_config={f: columns[f][0] for f in fields},
    )
    if st.button("Lưu thay đổi", key=widget_key + "_save", type="primary"):
        orig = {r["key"]: r for r in records}
        upserts, seen, errors = [], set(), 0
        for _, row in edited.iterrows():
            rec = {f: columns[f][2](row.get(f)) for f in fields}
            if any(_blank(rec.get(f)) for f in required):
                if any(not _blank(v) for v in rec.values()):
                    errors += 1
                continue
            for k, v in (defaults or {}).items():
                if _blank(rec.get(k)):
                    rec[k] = v
            k = row.get("key")
            if _blank(k):
                upserts.append(rec)
            else:
                seen.add(k)
                old = {f: orig.get(k, {}).get(f) for f in fields}
                if old != rec:
                    upserts.append({"key": k, **rec})
        removed = [k for k in orig if k not in seen]
        if upserts:
            db.put(name, upserts)
        if removed:
            db.delete(name, removed)
        msg = f"Đã lưu: {len(upserts)} dòng thêm/sửa, {len(removed)} dòng xoá."
        if errors:
            msg += f" Bỏ qua {errors} dòng thiếu thông tin bắt buộc."
        st.session_state["_flash"] = msg
        st.rerun()
    return False
