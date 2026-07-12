"""Shared 'Floodlit Night Stadium' theme for the Streamlit dashboard.

The shared app shell calls inject_theme() once to transform the whole app: it
applies the stadium canvas and restyles navigation, metrics, tables, tabs,
buttons, and expanders. Plus HTML render helpers (brand header, page header,
KPI cards) and a dark Plotly template shared with the website's visual language.

Note: the CSS targets Streamlit's data-testid / data-baseweb selectors. These are
reasonably stable but can shift across major Streamlit versions — if a future
upgrade changes them, only the cosmetic layer needs updating (no logic depends on it).
"""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FLAG_DIR = Path(__file__).resolve().parent / "assets" / "flags"
WORLD_CUP_LOGO = PROJECT_ROOT / "website" / "public" / "images" / "fifa-world-cup-26-emblem.png"

# palette (mirrors website/app/globals.css)
BG = "#05080f"
SURFACE = "#131f31"
LINE = "#223049"
LINE2 = "#33456a"
FG = "#eef4fd"
FG2 = "#9db0cc"
FG3 = "#61728e"
PITCH = "#29d17f"
GOLD = "#f5c451"
CYAN = "#38bdf8"
AMBER = "#fbbf24"
CRIMSON = "#f4515f"
BLUE = "#4f8cff"

ACCENTS = {"cyan": CYAN, "pitch": PITCH, "gold": GOLD, "crimson": CRIMSON, "amber": AMBER, "blue": BLUE, "muted": FG2}

_ICONS = {
    "trophy": '<path d="M7 4h10v4a5 5 0 0 1-10 0V4Z"/><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3"/><path d="M10 13v3M14 13v3M8 20h8M9 20a3 3 0 0 1 6 0"/>',
    "pitch": '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M12 5v14M3 9h3v6H3M21 9h-3v6h3"/><circle cx="12" cy="12" r="2.4"/>',
    "chart": '<path d="M4 4v16h16"/><path d="M8 15l3-4 3 2 4-6"/>',
    "bolt": '<path d="M13 3 5 13h5l-1 8 8-11h-5l1-7Z"/>',
    "shield": '<path d="M12 3 5 6v5c0 4.2 3 7.3 7 9 4-1.7 7-4.8 7-9V6l-7-3Z"/><path d="m9.5 12 1.8 1.8L15 10"/>',
    "team": '<circle cx="9" cy="8" r="3"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 6a3 3 0 0 1 0 6"/>',
    "route": '<circle cx="6" cy="18" r="2.2"/><circle cx="18" cy="6" r="2.2"/><path d="M8 18h6a3 3 0 0 0 3-3V9"/>',
    "gauge": '<path d="M4 18a8 8 0 1 1 16 0"/><path d="m12 14 3.5-3.5"/>',
    "lab": '<path d="M9 3h6M10 3v6l-5 8a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-8V3"/><path d="M7.5 15h9"/>',
    "signal": '<path d="M5 20v-4M10 20v-8M15 20v-12M20 20V6"/>',
    "network": '<circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="12" cy="18" r="2.4"/><path d="M7.6 7.6 10.4 16M16.4 7.6 13.6 16M8 6h8"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "sim": '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18M8 8l2 4-2 4M16 8l-2 4 2 4"/>',
}


def icon(name: str, color: str = CYAN, size: int = 18) -> str:
    body = _ICONS.get(name, "")
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


@lru_cache(maxsize=64)
def _asset_data_uri(path_string: str, mime: str) -> str:
    path = Path(path_string)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def flag_html(code: str | None, country: str, width: int = 28) -> str:
    """Return a locally bundled, accessible country flag for custom HTML blocks."""
    if not code:
        return ""
    source = _asset_data_uri(str(FLAG_DIR / f"{str(code).lower()}.svg"), "image/svg+xml")
    if not source:
        return ""
    safe_country = html.escape(str(country), quote=True)
    height = round(width * 0.75)
    return (f'<img class="sk-flag" src="{source}" width="{width}" height="{height}" '
            f'alt="{safe_country} flag" title="{safe_country}">')


def flag_uri(code: str | None) -> str:
    """Return a data URI suitable for Streamlit ImageColumn and chart helpers."""
    if not code:
        return ""
    return _asset_data_uri(str(FLAG_DIR / f"{str(code).lower()}.svg"), "image/svg+xml")


def brand_header() -> None:
    logo = _asset_data_uri(str(WORLD_CUP_LOGO), "image/png")
    logo_html = (f'<img class="sk-brand-logo" src="{logo}" alt="FIFA World Cup 26 official emblem">'
                 if logo else f'<span class="sk-brand-logo">{icon("trophy", GOLD, 28)}</span>')
    st.markdown(
        f'''<div class="sk-brand">
          <div class="sk-brand-main">
            {logo_html}
            <div>
              <div class="sk-brand-name">FIFA 2026 <span>Intelligence</span></div>
              <div class="sk-brand-sub">Dynamic tournament forecasting · XGBoost · Monte Carlo</div>
            </div>
          </div>
          <div class="sk-brand-status"><span class="sk-dot"></span> Live tournament command center</div>
        </div>''',
        unsafe_allow_html=True,
    )


def inject_theme() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
        :root {{ --pitch:{PITCH}; --gold:{GOLD}; --cyan:{CYAN}; --crimson:{CRIMSON}; --line:{LINE}; --line2:{LINE2}; --fg:{FG}; --fg2:{FG2}; --fg3:{FG3}; }}
        .stApp {{
            background:
              radial-gradient(60% 40% at 15% -6%, rgba(79,140,255,0.14), transparent 60%),
              radial-gradient(52% 38% at 86% -4%, rgba(245,196,81,0.09), transparent 60%),
              radial-gradient(80% 55% at 50% 120%, rgba(41,209,127,0.09), transparent 60%),
              linear-gradient(180deg, #080d18 0%, {BG} 55%);
            color: {FG}; font-family: 'Inter', system-ui, sans-serif;
        }}
        header[data-testid="stHeader"] {{ background: transparent; height: .35rem; }}
        #MainMenu, footer, [data-testid="stDecoration"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stToolbar"], [data-testid="stStatusWidget"] {{ display: none; }}
        h1, h2, h3 {{ font-family: 'Space Grotesk', system-ui, sans-serif !important; letter-spacing: -0.01em; }}
        .block-container {{ padding-top: .55rem; max-width: 78rem; padding-left: 1.25rem; padding-right: 1.25rem; }}

        /* metrics -> premium cards */
        [data-testid="stMetric"] {{
            background: linear-gradient(180deg, rgba(20,32,50,0.9), rgba(14,22,38,0.9));
            border: 1px solid {LINE}; border-radius: 14px; padding: 14px 16px;
            transition: transform .18s ease, border-color .18s ease;
        }}
        [data-testid="stMetric"]:hover {{ transform: translateY(-2px); border-color: {LINE2}; }}
        [data-testid="stMetricValue"] {{ font-family: 'Space Grotesk'; font-weight: 700; color: {FG}; }}
        [data-testid="stMetricLabel"] {{ color: {FG3}; text-transform: uppercase; letter-spacing: .06em; font-size: .72rem; }}

        /* dataframes */
        .stDataFrame {{ border: 1px solid {LINE}; border-radius: 12px; overflow: hidden; }}

        /* liquid-glass interactive system */
        [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid rgba(157,176,204,.18); }}
        [data-baseweb="tab"] {{
            color: {FG2}; border-radius: 10px 10px 0 0;
            background: linear-gradient(135deg, rgba(255,255,255,.06), rgba(255,255,255,.015));
            border: 1px solid rgba(255,255,255,.07); border-bottom: 0;
            backdrop-filter: blur(16px) saturate(145%); transition: all .2s ease;
        }}
        [data-baseweb="tab"]:hover {{ color:{FG}; border-color:rgba(56,189,248,.35); transform:translateY(-1px); }}
        [aria-selected="true"][data-baseweb="tab"] {{ color:{FG}; border-color:rgba(56,189,248,.45); box-shadow:inset 0 1px 0 rgba(255,255,255,.13), 0 10px 28px -20px rgba(56,189,248,.9); }}

        .stButton button, .stDownloadButton button, [data-testid="stPageLink"] a {{
            color:{FG}; border:1px solid rgba(157,176,204,.28); border-radius:12px; font-weight:600;
            background:linear-gradient(135deg, rgba(255,255,255,.09), rgba(255,255,255,.025));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.13), 0 12px 32px -24px rgba(56,189,248,.8);
            backdrop-filter:blur(18px) saturate(150%); transition:transform .2s ease, border-color .2s ease, box-shadow .2s ease, background .2s ease;
        }}
        .stButton button:hover, .stDownloadButton button:hover, [data-testid="stPageLink"] a:hover {{
            color:#fff; border-color:rgba(56,189,248,.62); transform:translateY(-2px);
            background:linear-gradient(135deg, rgba(56,189,248,.16), rgba(41,209,127,.07));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.18), 0 16px 34px -20px rgba(56,189,248,.75);
        }}
        .stButton button:active, .stDownloadButton button:active {{ transform:translateY(0) scale(.985); }}
        [data-testid="stExpander"] {{
            border:1px solid rgba(157,176,204,.2); border-radius:14px;
            background:linear-gradient(135deg, rgba(20,32,50,.7), rgba(14,22,38,.46));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.06); backdrop-filter:blur(16px) saturate(135%);
        }}
        [data-baseweb="select"] > div, .stTextInput input, .stMultiSelect [data-baseweb="select"] > div {{
            color:{FG}; border-color:rgba(157,176,204,.28); border-radius:11px;
            background:linear-gradient(135deg, rgba(20,32,50,.82), rgba(14,22,38,.68));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.07); backdrop-filter:blur(14px) saturate(140%);
        }}
        [data-baseweb="select"] > div:hover, .stTextInput input:hover {{ border-color:rgba(56,189,248,.48); }}
        [data-testid="stPlotlyChart"] {{ border-radius:16px; overflow:hidden; border:1px solid rgba(157,176,204,.12); background:rgba(14,22,38,.28); }}

        /* responsive top navigator */
        .st-key-top_navigation {{ margin:.65rem 0 .15rem; }}
        .st-key-top_navigation [data-testid="stPills"] > div {{ gap:.5rem; flex-wrap:wrap; }}
        .st-key-top_navigation button {{
            min-height:2.55rem; padding:.48rem .86rem; color:{FG2}; font-family:'Space Grotesk'; font-weight:600;
            border:1px solid rgba(157,176,204,.2); border-radius:12px;
            background:linear-gradient(135deg, rgba(255,255,255,.075), rgba(255,255,255,.018));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.1), 0 12px 30px -26px rgba(56,189,248,.85);
            backdrop-filter:blur(20px) saturate(160%); transition:all .2s cubic-bezier(.2,.7,.2,1);
        }}
        .st-key-top_navigation button:hover {{
            color:#fff; transform:translateY(-2px); border-color:rgba(56,189,248,.55);
            background:linear-gradient(135deg, rgba(56,189,248,.17), rgba(41,209,127,.06));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.16), 0 16px 32px -22px rgba(56,189,248,.72);
        }}
        .st-key-top_navigation button[kind="pillsActive"], .st-key-top_navigation button[aria-pressed="true"] {{
            color:#031711; border-color:rgba(74,229,158,.8);
            background:linear-gradient(135deg, #58e6a2, {PITCH});
            box-shadow:inset 0 1px 0 rgba(255,255,255,.45), 0 14px 30px -16px rgba(41,209,127,.9);
        }}

        /* custom components */
        .sk-brand {{ display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.3rem 0 .7rem; }}
        .sk-brand-main {{ display:flex; align-items:center; gap:.85rem; min-width:0; }}
        .sk-brand-logo {{ width:3.25rem; height:3.25rem; flex:0 0 auto; object-fit:cover; border-radius:8px; border:1px solid rgba(245,196,81,.32); box-shadow:0 14px 34px -20px rgba(245,196,81,.7); }}
        .sk-brand-name {{ font-family:'Space Grotesk'; font-size:1.45rem; line-height:1; font-weight:700; color:{FG}; }}
        .sk-brand-name span {{ color:{FG3}; font-weight:600; }}
        .sk-brand-sub {{ margin-top:.35rem; color:{FG2}; font-size:.78rem; }}
        .sk-brand-status {{ display:flex; align-items:center; gap:.45rem; color:#c9ffe4; font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; white-space:nowrap; }}
        .sk-nav-rule {{ height:1px; margin:.5rem 0 1.5rem; background:linear-gradient(90deg, transparent, rgba(56,189,248,.42), rgba(41,209,127,.24), transparent); }}
        .sk-header {{ margin: 0 0 1.2rem; }}
        .sk-kicker {{ font-family:'Space Grotesk'; font-size:.72rem; letter-spacing:.2em; text-transform:uppercase; color:{FG3}; font-weight:600; display:flex; align-items:center; gap:.5rem; }}
        .sk-title {{ font-family:'Space Grotesk'; font-weight:700; font-size:2.1rem; line-height:1.05; margin:.4rem 0 0; color:{FG}; }}
        .sk-sub {{ color:{FG2}; margin-top:.4rem; font-size:.95rem; }}
        .sk-live {{ display:inline-flex; align-items:center; gap:.45rem; padding:.28rem .6rem; border-radius:999px; font-size:.68rem; font-weight:700; letter-spacing:.08em; color:#c9ffe4; background:rgba(41,209,127,0.12); border:1px solid rgba(41,209,127,0.4); }}
        .sk-dot {{ width:.5rem; height:.5rem; border-radius:999px; background:{PITCH}; box-shadow:0 0 0 0 rgba(41,209,127,.6); animation:skpulse 2s infinite; }}
        @keyframes skpulse {{ 0%{{box-shadow:0 0 0 0 rgba(41,209,127,.5)}} 70%{{box-shadow:0 0 0 7px rgba(41,209,127,0)}} 100%{{box-shadow:0 0 0 0 rgba(41,209,127,0)}} }}
        .sk-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(155px,1fr)); gap:12px; margin:.3rem 0 1rem; }}
        .sk-card {{ background:linear-gradient(180deg, rgba(20,32,50,.9), rgba(14,22,38,.9)); border:1px solid {LINE}; border-radius:14px; padding:15px 16px; transition:transform .18s ease, border-color .18s ease; }}
        .sk-card:hover {{ transform:translateY(-2px); border-color:{LINE2}; }}
        .sk-card .l {{ display:flex; align-items:center; gap:.45rem; color:{FG3}; font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; }}
        .sk-card .v {{ font-family:'Space Grotesk'; font-weight:700; font-size:1.7rem; color:{FG}; margin-top:.35rem; line-height:1; }}
        .sk-card .h {{ color:{FG2}; font-size:.76rem; margin-top:.3rem; }}
        .sk-feature {{ border:1px solid rgba(245,196,81,.28); background:linear-gradient(160deg, rgba(33,44,66,.95), rgba(12,19,32,.96)); box-shadow:0 26px 70px -40px rgba(245,196,81,.25); border-radius:18px; padding:22px 24px; }}
        .sk-team-row {{ display:flex; align-items:center; gap:.55rem; min-width:0; color:{FG}; font-weight:650; }}
        .sk-team-row .name {{ overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
        .sk-match-title {{ display:flex; align-items:center; justify-content:space-between; gap:.65rem; padding:.25rem 0 .55rem; }}
        .sk-match-vs {{ color:{FG3}; font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }}
        .sk-team-strip {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr)); gap:.7rem; margin:.4rem 0 1rem; }}
        .sk-team-chip {{ display:flex; align-items:center; gap:.6rem; padding:.7rem .8rem; border:1px solid rgba(157,176,204,.18); border-radius:12px; background:linear-gradient(135deg,rgba(255,255,255,.07),rgba(255,255,255,.018)); box-shadow:inset 0 1px 0 rgba(255,255,255,.08); backdrop-filter:blur(16px); }}
        .sk-team-chip .meta {{ min-width:0; }}
        .sk-team-chip .team {{ color:{FG}; font-weight:650; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
        .sk-team-chip .prob {{ color:{CYAN}; font-family:'Space Grotesk'; font-size:.76rem; font-weight:700; margin-top:.08rem; }}
        .sk-bar {{ height:.5rem; border-radius:999px; background:rgba(51,69,106,.35); overflow:hidden; }}
        .sk-bar > span {{ display:block; height:100%; border-radius:999px; }}
        .sk-flag {{ display:inline-block; object-fit:cover; border-radius:2px; border:1px solid rgba(255,255,255,.18); box-shadow:0 3px 10px rgba(0,0,0,.28); vertical-align:-.16em; flex:0 0 auto; }}
        @media (max-width: 700px) {{
            .block-container {{ padding-left:.8rem; padding-right:.8rem; }}
            .sk-brand {{ align-items:flex-start; }}
            .sk-brand-logo {{ width:2.65rem; height:2.65rem; }}
            .sk-brand-name {{ font-size:1.08rem; }}
            .sk-brand-sub {{ font-size:.68rem; }}
            .sk-brand-status {{ display:none; }}
            .st-key-top_navigation button {{ min-height:2.3rem; padding:.38rem .66rem; font-size:.78rem; }}
            .sk-title {{ font-size:1.7rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def header(title: str, kicker: str = "", sub: str = "", icon_name: str = "trophy", live: bool = False) -> None:
    live_html = '<span class="sk-live"><span class="sk-dot"></span> LIVE FORECAST</span>' if live else ""
    kick = f'<div class="sk-kicker">{icon(icon_name, CYAN, 14)}{kicker} {live_html}</div>' if kicker or live else ""
    sub_html = f'<div class="sk-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="sk-header">{kick}<div class="sk-title">{title}</div>{sub_html}</div>', unsafe_allow_html=True)


def kpi_grid(cards: list[dict]) -> None:
    """cards: list of {label, value, hint?, accent?, icon?}."""
    html = '<div class="sk-grid">'
    for c in cards:
        ac = ACCENTS.get(c.get("accent", "cyan"), CYAN)
        ic = icon(c.get("icon", "chart"), ac, 15)
        hint = f'<div class="h">{c["hint"]}</div>' if c.get("hint") else ""
        html += f'<div class="sk-card"><div class="l">{ic}{c["label"]}</div><div class="v">{c["value"]}</div>{hint}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def bar(value: float, color: str = CYAN) -> str:
    pct = max(0.0, min(1.0, value)) * 100
    return f'<div class="sk-bar"><span style="width:{pct:.1f}%;background:{color}"></span></div>'


def apply_plotly(fig, height: int | None = None):
    """Apply the shared dark stadium template to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color=FG2, size=12),
        title_font=dict(family="Space Grotesk", color=FG, size=15),
        colorway=[CYAN, PITCH, GOLD, BLUE, CRIMSON, AMBER],
        margin=dict(l=10, r=10, t=44, b=10),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor="rgba(51,69,106,0.25)", zerolinecolor="rgba(51,69,106,0.35)"),
        yaxis=dict(gridcolor="rgba(51,69,106,0.25)", zerolinecolor="rgba(51,69,106,0.35)"),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE2, font=dict(color=FG)),
    )
    if height:
        fig.update_layout(height=height)
    return fig
