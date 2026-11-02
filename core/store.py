"""Lưu trữ kiểu "ghi nối dòng, bản mới nhất theo khoá".

Mỗi bảng (một tab trong Google Sheet) có 4 cột: key | ts | deleted | data(JSON).
- Ghi: luôn nối thêm dòng mới, không sửa dòng cũ.
- Đọc: lấy dòng có ts mới nhất cho mỗi key; bỏ key có deleted = 1.

Có 2 nơi lưu:
- AppsScriptStore: Google Sheets qua Web App Apps Script (dùng thật).
- LocalStore: file JSONL trong thư mục data/ (chạy thử trên máy, test).
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests


def now_ts() -> str:
    # ISO UTC có micro giây -> so sánh chuỗi = so sánh thời gian
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_key() -> str:
    return uuid.uuid4().hex[:12]


def make_row(key: str, data: dict | None, deleted: bool = False) -> dict:
    return {
        "key": key,
        "ts": now_ts(),
        "deleted": bool(deleted),
        "data": json.dumps(data or {}, ensure_ascii=False),
    }


def latest(rows: Iterable[dict]) -> list[dict]:
    """Gộp các dòng thô thành bản ghi mới nhất theo key. Trả về list dict (có trường 'key')."""
    best: dict[str, tuple[str, int, dict]] = {}
    for i, r in enumerate(rows):
        k = str(r.get("key", ""))
        if not k:
            continue
        ts = str(r.get("ts", ""))
        cur = best.get(k)
        if cur is None or (ts, i) >= (cur[0], cur[1]):
            best[k] = (ts, i, r)
    out = []
    for k, (_, _, r) in best.items():
        deleted = r.get("deleted")
        if deleted in (True, 1, "1", "true", "TRUE"):
            continue
        try:
            data = json.loads(r.get("data") or "{}")
        except (TypeError, ValueError):
            data = {}
        data["key"] = k
        out.append(data)
    return out


class StoreError(RuntimeError):
    pass


class LocalStore:
    def __init__(self, folder: str | Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, table: str) -> Path:
        safe = "".join(ch for ch in table if ch.isalnum() or ch == "_")
        return self.folder / f"{safe}.jsonl"

    def read(self, table: str) -> list[dict]:
        p = self._path(table)
        if not p.exists():
            return []
        rows = []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def append(self, table: str, rows: list[dict]) -> None:
        if not rows:
            return
        with self._lock, self._path(table).open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Lịch Google: bản local đọc từ file mẫu calendar_pt.json (nếu có)
    def calendar_events(self, start: str, end: str, calendar: str = "PT") -> list[dict]:
        p = self.folder / "calendar_pt.json"
        if not p.exists():
            return []
        evs = json.loads(p.read_text(encoding="utf-8"))
        return [e for e in evs if start <= e["start"][:10] <= end]

    def calendar_create(self, ev: dict) -> str:
        self.append("_gcal_log", [make_row(new_key(), ev)])
        return "local-" + new_key()

    def calendar_delete(self, event_id: str) -> None:
        self.append("_gcal_log", [make_row(new_key(), {"delete": event_id})])

    label = "Máy (thử nghiệm)"


class AppsScriptStore:
    label = "Google Sheets"

    def __init__(self, url: str, token: str, timeout: int = 25):
        self.url = url
        self.token = token
        self.timeout = timeout

    def _call(self, payload: dict) -> dict:
        payload = {**payload, "token": self.token}
        try:
            resp = requests.post(self.url, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            raise StoreError(f"Không kết nối được Apps Script: {e}") from e
        try:
            out = resp.json()
        except ValueError as e:
            raise StoreError(
                "Apps Script không trả JSON (kiểm tra lại quyền truy cập Web App: "
                "'Bất kỳ ai')."
            ) from e
        if not out.get("ok"):
            raise StoreError(f"Apps Script báo lỗi: {out.get('error')}")
        return out

    def read(self, table: str) -> list[dict]:
        return self._call({"action": "read", "table": table}).get("rows", [])

    def append(self, table: str, rows: list[dict]) -> None:
        if rows:
            self._call({"action": "append", "table": table, "rows": rows})

    def calendar_events(self, start: str, end: str, calendar: str = "PT") -> list[dict]:
        return self._call(
            {"action": "calendar", "calendar": calendar, "start": start, "end": end}
        ).get("events", [])

    def calendar_create(self, ev: dict) -> str:
        return self._call({"action": "calendar_create", "event": ev}).get("id", "")

    def calendar_delete(self, event_id: str) -> None:
        self._call({"action": "calendar_delete", "id": event_id})
