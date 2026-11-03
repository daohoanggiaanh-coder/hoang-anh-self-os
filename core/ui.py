"""Giao diện chung: màu, CSS, thẻ, timeline, cài như app."""
from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from core.scheduler import Item, fmt, fmt_dur

TZ = ZoneInfo("Asia/Ho_Chi_Minh")

from core.scheduler import CATEGORIES  # noqa: E402

KIND_COLOR = {k: v[2] for k, v in CATEGORIES.items()}
KIND_ICON = {k: v[1] for k, v in CATEGORIES.items()}
KIND_LABEL = {k: v[0] for k, v in CATEGORIES.items()}
ENERGY_ICON = {"Tỉnh táo": "⚡", "Bình thường": "◐", "Mệt": "☾"}


def now_vn() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None)


def is_dark() -> bool:
    try:
        return (st.context.theme.type or "dark") == "dark"
    except Exception:
        return True


def inject_css():
    dark = is_dark()
    v = {
        "bg": "#0B0B0C" if dark else "#F7F4EE",
        "card": "#141416" if dark else "#FFFFFF",
        "card2": "#1B1A18" if dark else "#F1ECE2",
        "line": "#2A2620" if dark else "#E2D9C8",
        "text": "#EDE6D6" if dark else "#1A1814",
        "muted": "#9A9284" if dark else "#6B6458",
        "gold": "#C9A45C" if dark else "#9C7631",
        "gold2": "#E3C88A" if dark else "#7A5A22",
        "goldbg": "rgba(201,164,92,.10)" if dark else "rgba(156,118,49,.10)",
    }
    css_vars = ";".join(f"--{k}:{val}" for k, val in v.items())
    st.html(
        f"""<style>
:root {{ {css_vars} }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 4rem; max-width: 980px; }}
h1, h2, h3 {{ letter-spacing: -.01em; }}
.so-eyebrow {{ color: var(--gold); font-size: .72rem; letter-spacing: .22em; text-transform: uppercase; font-weight: 600; }}
.so-title {{ font-size: 1.75rem; font-weight: 700; margin: .1rem 0 .2rem; line-height: 1.2; }}
.so-sub {{ color: var(--muted); font-size: .92rem; margin-bottom: .6rem; }}
.so-rule {{ height: 1px; background: linear-gradient(90deg, var(--gold), transparent); margin: .4rem 0 1rem; opacity: .7; }}
.so-card {{ background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; margin-bottom: 12px; }}
.so-card h4 {{ margin: 0 0 8px; font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; color: var(--gold); font-weight: 600; }}
.so-stat {{ display:flex; gap:10px; flex-wrap:wrap; }}
.so-stat > div {{ flex:1 1 120px; background: var(--card); border:1px solid var(--line); border-radius:12px; padding:10px 12px; }}
.so-stat b {{ display:block; font-size:1.35rem; font-weight:700; color: var(--gold2); }}
.so-stat span {{ font-size:.75rem; color: var(--muted); }}
.so-tl {{ display:flex; flex-direction:column; gap:6px; }}
.so-row {{ display:flex; align-items:center; gap:10px; padding:7px 10px; border-radius:10px; background: var(--card2); border-left: 3px solid var(--c, var(--gold)); }}
.so-row.free {{ background: transparent; border: 1px dashed var(--gold); border-left-width: 1px; }}
.so-row.now {{ outline: 1px solid var(--gold2); }}
.so-time {{ font-variant-numeric: tabular-nums; font-size: .82rem; color: var(--muted); min-width: 92px; }}
.so-name {{ flex:1; font-size: .92rem; }}
.so-chip {{ font-size: .68rem; padding: 2px 8px; border-radius: 999px; background: var(--goldbg); color: var(--gold2); white-space: nowrap; }}
.so-row.free .so-name {{ color: var(--gold2); font-weight: 600; }}
.so-warn {{ border:1px solid rgba(201,164,92,.45); background: var(--goldbg); border-radius: 12px; padding: 10px 14px; margin-bottom: 8px; font-size: .9rem; }}
.so-muted {{ color: var(--muted); font-size: .85rem; }}
.so-soon {{ color: var(--muted); font-size: .85rem; font-style: italic; }}
.st-key-so_nav .stPageLink a {{ justify-content:center; border:1px solid var(--line); border-radius:999px; padding:0 10px; }}
.st-key-so_nav .stPageLink p {{ font-size:.82rem; }}
.so-bar {{ height:8px; border-radius:99px; background: var(--line); overflow:hidden; }}
.so-bar > div {{ height:100%; background: linear-gradient(90deg, var(--gold), var(--gold2)); }}
.so-badge {{ display:inline-flex; gap:6px; align-items:center; padding:6px 10px; border-radius:12px; border:1px solid var(--line); margin:0 6px 6px 0; font-size:.85rem; }}
.so-badge.off {{ opacity:.35; filter: grayscale(1); }}
.st-key-so_ck {{ position:absolute !important; left:-9999px; height:0; overflow:hidden; }}
.so-ver {{ color: var(--muted); font-size: .72rem; letter-spacing: .08em; }}
.stButton > button[kind="primary"] {{ color: #0B0B0C; font-weight: 600; }}
@media (max-width: 640px) {{
  .block-container {{ padding-left: .8rem; padding-right: .8rem; }}
  .so-title {{ font-size: 1.45rem; }}
  .so-time {{ min-width: 84px; font-size: .78rem; }}
}}
</style>"""
    )


def inject_head():
    """Thêm manifest + icon vào <head> để 'Thêm vào màn hình chính' hiện icon riêng."""
    st.iframe(
        """<script>
(function(){
  const d = window.parent.document;
  if (d.getElementById('selfos-manifest')) return;
  const add = (tag, attrs) => { const el = d.createElement(tag); Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k, v)); d.head.appendChild(el); };
  add('link', {id:'selfos-manifest', rel:'manifest', href:'./app/static/manifest.json'});
  add('link', {rel:'apple-touch-icon', href:'./app/static/icon-192.png'});
  add('link', {rel:'icon', type:'image/png', href:'./app/static/icon-192.png'});
  add('meta', {name:'theme-color', content:'#0B0B0C'});
  add('meta', {name:'apple-mobile-web-app-capable', content:'yes'});
  add('meta', {name:'mobile-web-app-capable', content:'yes'});
  add('meta', {name:'apple-mobile-web-app-title', content:'Self OS'});
  add('meta', {name:'apple-mobile-web-app-status-bar-style', content:'black-translucent'});
})();
</script>""",
        height=1,
    )


NAV = [
    ("views/today.py", "Hôm nay", ":material/wb_sunny:"),
    ("views/schedule.py", "Lịch", ":material/calendar_month:"),
    ("views/goals.py", "Mục tiêu", ":material/flag:"),
    ("views/habits.py", "Thói quen", ":material/local_fire_department:"),
    ("views/skills.py", "Kỹ năng", ":material/school:"),
    ("views/looks.py", "Vẻ ngoài", ":material/styler:"),
    ("views/studio.py", "Studio", ":material/storefront:"),
    ("views/review.py", "Tổng kết", ":material/insights:"),
    ("views/settings.py", "Cài đặt", ":material/tune:"),
]


def nav_row():
    """Thanh chuyển trang luôn hiện (điện thoại không phải mở menu)."""
    with st.container(horizontal=True, wrap=True, gap="small", key="so_nav"):
        for path, label, icon in NAV:
            st.page_link(path, label=label, icon=icon)


def header(eyebrow: str, title: str, sub: str = ""):
    st.html(
        f'<div class="so-eyebrow">{html.escape(eyebrow)}</div>'
        f'<div class="so-title">{html.escape(title)}</div>'
        + (f'<div class="so-sub">{html.escape(sub)}</div>' if sub else "")
        + '<div class="so-rule"></div>'
    )


def card(title: str, body_html: str):
    st.html(f'<div class="so-card"><h4>{html.escape(title)}</h4>{body_html}</div>')


def stats(pairs: list[tuple[str, str]]):
    st.html('<div class="so-stat">' + "".join(f"<div><b>{html.escape(v)}</b><span>{html.escape(k)}</span></div>" for k, v in pairs) + "</div>")


def warnings(ws: list[str]):
    for w in ws:
        st.html(f'<div class="so-warn">⚠︎ {html.escape(w)}</div>')


def timeline_html(items: list[Item], slots: list[tuple[int, int]], now_min: int | None = None, hide_kinds=("Ngủ",)) -> str:
    rows = []
    for it in items:
        if it.kind in hide_kinds:
            continue
        rows.append((it.start, 0, it))
    for s, e in slots:
        rows.append((s, 1, (s, e)))
    rows.sort(key=lambda r: (r[0], r[1]))
    out = []
    for _, typ, obj in rows:
        if typ == 0:
            it = obj
            c = KIND_COLOR.get(it.kind, "#C9A45C")
            now = " now" if now_min is not None and it.start <= now_min < it.end else ""
            out.append(
                f'<div class="so-row{now}" style="--c:{c}"><span class="so-time">{fmt(it.start)}–{fmt(it.end)}</span>'
                f'<span class="so-name">{KIND_ICON.get(it.kind, "•")} {html.escape(it.title)}</span>'
                f'<span class="so-chip" style="background:{c}26;color:{c};border:1px solid {c}66">{html.escape(KIND_LABEL.get(it.kind, it.kind))}</span></div>'
            )
        else:
            s, e = obj
            now = " now" if now_min is not None and s <= now_min < e else ""
            out.append(
                f'<div class="so-row free{now}"><span class="so-time">{fmt(s)}–{fmt(e)}</span>'
                f'<span class="so-name">Trống · {fmt_dur(e - s)}</span><span class="so-chip">giờ trống</span></div>'
            )
    if not out:
        return '<div class="so-muted">Chưa có gì trong ngày.</div>'
    return '<div class="so-tl">' + "".join(out) + "</div>"


def bar_html(pct: float | None, label: str = "") -> str:
    p = 0 if pct is None else max(0.0, min(1.0, pct))
    lab = f'<div class="so-muted" style="margin-bottom:4px">{html.escape(label)}</div>' if label else ""
    return f'{lab}<div class="so-bar"><div style="width:{p * 100:.0f}%"></div></div>'


def flash():
    msg = st.session_state.pop("_flash", None)
    if msg:
        st.success(msg)


def legend_html(kinds: list[str] | None = None) -> str:
    kinds = kinds or [k for k in CATEGORIES if k not in ("Ngủ",)]
    return '<div style="display:flex;flex-wrap:wrap;gap:6px 12px;margin:4px 0 10px">' + "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;font-size:.78rem">'
        f'<span style="width:10px;height:10px;border-radius:3px;background:{KIND_COLOR[k]}"></span>'
        f'{KIND_ICON[k]} {html.escape(KIND_LABEL[k])}</span>' for k in kinds if k in CATEGORIES) + "</div>"


def week_map_html(days, items_by_day: dict, slots_by_day: dict, start_min: int = 300, end_min: int = 1380,
                  today=None) -> str:
    """Bản đồ màu cả tuần: mỗi cột 1 ngày, khối màu theo loại việc, vạch đứt = giờ trống."""
    from core.scheduler import WEEKDAY_NAMES, fmt

    span = end_min - start_min
    px = 26  # px mỗi giờ
    h = span / 60 * px
    hours = "".join(
        f'<div style="position:absolute;top:{(m - start_min) / 60 * px:.1f}px;left:0;right:0;border-top:1px solid var(--line);'
        f'font-size:.6rem;color:var(--muted);padding-left:2px">{m // 60}h</div>'
        for m in range(start_min, end_min + 1, 120))
    cols = []
    for d in days:
        blocks = []
        for s_, e_ in slots_by_day.get(d, []):
            s2, e2 = max(s_, start_min), min(e_, end_min)
            if e2 > s2:
                blocks.append(f'<div title="Trống {fmt(s_)}–{fmt(e_)}" style="position:absolute;left:2px;right:2px;'
                              f'top:{(s2 - start_min) / 60 * px:.1f}px;height:{(e2 - s2) / 60 * px:.1f}px;'
                              f'border:1px dashed var(--gold);border-radius:4px;opacity:.45"></div>')
        for it in items_by_day.get(d, []):
            if it.kind == "Ngủ":
                continue
            s2, e2 = max(it.start, start_min), min(it.end, end_min)
            if e2 <= s2:
                continue
            c = KIND_COLOR.get(it.kind, "#7A756B")
            hh = (e2 - s2) / 60 * px
            label = KIND_ICON.get(it.kind, "") if hh >= 13 else ""
            blocks.append(f'<div title="{fmt(it.start)}–{fmt(it.end)} · {html.escape(it.title)} ({html.escape(KIND_LABEL.get(it.kind, it.kind))})" '
                          f'style="position:absolute;left:2px;right:2px;top:{(s2 - start_min) / 60 * px:.1f}px;height:{max(hh, 3):.1f}px;'
                          f'background:{c};border-radius:4px;font-size:.62rem;line-height:1;display:flex;align-items:center;'
                          f'justify-content:center;overflow:hidden">{label}</div>')
        is_today = today is not None and d == today
        head = (f'<div style="text-align:center;font-size:.7rem;font-weight:{700 if is_today else 500};'
                f'color:{"var(--gold2)" if is_today else "var(--muted)"};margin-bottom:4px">'
                f'{WEEKDAY_NAMES[d.weekday()].replace("Thứ ", "T").replace("Chủ nhật", "CN")}<br>{d.day:02d}/{d.month:02d}</div>')
        cols.append(f'<div style="flex:1;min-width:0">{head}<div style="position:relative;height:{h:.0f}px;'
                    f'background:var(--card2);border-radius:6px">{"".join(blocks)}</div></div>')
    return (f'<div style="display:flex;gap:4px"><div style="width:22px;position:relative;margin-top:30px;height:{h:.0f}px">{hours}</div>'
            + "".join(cols) + "</div>")
