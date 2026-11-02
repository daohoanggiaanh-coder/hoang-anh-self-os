"""Nén ảnh tiến độ để lưu vừa 1 ô Google Sheets (giới hạn 50.000 ký tự/ô)."""
from __future__ import annotations

import base64
import io

from PIL import Image, ImageOps

MAX_CHARS = 45_000


def compress_to_b64(raw: bytes, max_chars: int = MAX_CHARS) -> str:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    for h in (640, 560, 480, 420, 360, 300, 240):
        im = img.copy()
        im.thumbnail((int(h * 0.8), h))
        for q in (75, 65, 55, 45, 35):
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=q, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode()
            if len(b64) <= max_chars:
                return b64
    raise ValueError("Ảnh quá phức tạp để nén — thử ảnh khác.")


def b64_to_bytes(b64: str) -> bytes:
    return base64.b64decode(b64)
