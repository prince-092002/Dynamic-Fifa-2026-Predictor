"""Prediction History — an automatic forecast audit trail.

Shows what the model predicted before each matchday and how the forecast evolved as real
results arrived. Reads immutable snapshots from data/prediction_history/ and joins the
current completed-match results (knockout_bracket.json) at render time — the originally
predicted probabilities are never altered.
"""

import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))       # dashboard/
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))       # repo root (for src.*)
from data.loaders import load_json, missing  # noqa: E402
from theme import header, flag_html, GOLD, PITCH, CYAN, CRIMSON, AMBER, FG2, FG3, LINE, LINE2  # noqa: E402

try:
    from src.prediction_history.snapshot import load_all_snapshots, enrich_snapshot, completed_results_index
except Exception:  # pragma: no cover - defensive
    load_all_snapshots = enrich_snapshot = completed_results_index = None

header("Prediction History", "Forecast audit trail",
       "What the model predicted before each matchday — and how the forecast changed as real results came in. "
       "Historical probabilities are preserved exactly; actual results are matched in afterwards.",
       icon_name="route")

# ---- page-scoped styles (do not touch other tabs) ----
st.markdown(f"""<style>
.ph-meta {{ display:flex; flex-wrap:wrap; gap:.4rem .6rem; margin:.2rem 0 1rem; }}
.ph-tag {{ font-size:.72rem; font-weight:600; color:{FG2}; border:1px solid {LINE2}; background:rgba(10,17,32,.6);
  padding:.22rem .55rem; border-radius:999px; }}
.ph-tag b {{ color:#eef4fd; }}
.ph-class {{ font-size:.68rem; font-weight:700; letter-spacing:.04em; padding:.22rem .55rem; border-radius:999px; }}
.ph-class.genuine {{ color:{PITCH}; border:1px solid rgba(41,209,127,.4); background:rgba(41,209,127,.08); }}
.ph-class.recovered {{ color:{CYAN}; border:1px solid rgba(56,189,248,.4); background:rgba(56,189,248,.08); }}
.ph-card {{ border:1px solid {LINE}; border-radius:14px; background:linear-gradient(180deg,rgba(20,32,50,.85),rgba(14,22,38,.85));
  padding:1rem 1.15rem; height:100%; }}
.ph-champ {{ display:flex; align-items:center; gap:.7rem; }}
.ph-champ .name {{ font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.5rem; color:#eef4fd; }}
.ph-champ .pct {{ margin-left:auto; font-family:'Space Grotesk',sans-serif; font-weight:800; font-size:1.6rem; color:{GOLD}; }}
.ph-row {{ display:flex; align-items:center; gap:.55rem; margin:.3rem 0; font-size:.9rem; color:{FG2}; }}
.ph-row .t {{ color:#eef4fd; }}
.ph-row .v {{ margin-left:auto; font-family:'Space Grotesk',sans-serif; font-weight:700; color:#eef4fd; }}
.ph-bar {{ flex:1; height:.5rem; border-radius:999px; background:rgba(51,69,106,.35); overflow:hidden; min-width:60px; }}
.ph-bar > span {{ display:block; height:100%; border-radius:999px; }}
.ph-match {{ border:1px solid {LINE}; border-radius:14px; background:rgba(12,19,32,.7); padding:.95rem 1.05rem; margin-bottom:.7rem; }}
.ph-match .head {{ display:flex; align-items:center; gap:.5rem; font-size:.72rem; color:{FG3}; text-transform:uppercase; letter-spacing:.1em; margin-bottom:.5rem; }}
.ph-side {{ display:flex; align-items:center; gap:.5rem; margin:.28rem 0; }}
.ph-side .nm {{ color:#eef4fd; font-weight:600; }}
.ph-side .p {{ margin-left:auto; font-family:'Space Grotesk',sans-serif; font-weight:700; }}
.ph-side.win .nm {{ color:{GOLD}; }}
.ph-foot {{ display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-top:.6rem; padding-top:.55rem; border-top:1px solid {LINE}; font-size:.8rem; color:{FG2}; }}
.ph-out {{ font-size:.72rem; font-weight:700; padding:.2rem .5rem; border-radius:999px; }}
.ph-out.correct {{ color:{PITCH}; background:rgba(41,209,127,.12); border:1px solid rgba(41,209,127,.4); }}
.ph-out.incorrect {{ color:{CRIMSON}; background:rgba(244,81,95,.12); border:1px solid rgba(244,81,95,.4); }}
.ph-out.pending {{ color:{AMBER}; background:rgba(251,191,36,.12); border:1px solid rgba(251,191,36,.4); }}
.ph-method {{ font-size:.72rem; color:{CYAN}; border:1px solid {LINE2}; padding:.16rem .45rem; border-radius:999px; }}
.ph-sec {{ font-family:'Space Grotesk',sans-serif; font-weight:700; color:#eef4fd; font-size:1.05rem; margin:.2rem 0 .1rem; }}
</style>""", unsafe_allow_html=True)

if load_all_snapshots is None:
    missing("Prediction history module is unavailable.")
    st.stop()

try:
    snapshots = load_all_snapshots()
except Exception:
    snapshots = []

if not snapshots:
    missing("No prediction history yet. Snapshots are archived automatically on each production forecast refresh; "
            "run `python main.py backfill-prediction-history` to recover past forecasts from committed outputs.")
    st.stop()

teams = load_json("teams.json").get("teams", [])
team_code = {t["team"]: t.get("code") for t in teams}
try:
    results = completed_results_index()
except Exception:
    results = {}


def fmt_date(iso_date: str) -> str:
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return iso_date or "—"


def fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%b %d, %Y · %H:%M UTC")
    except Exception:
        return str(iso)


def pctf(v, d=1):
    return f"{float(v) * 100:.{d}f}%" if v is not None else "—"


def flag(team, w=24):
    return flag_html(team_code.get(team), team or "", w) or ""


# newest meaningful production snapshot per calendar date
by_date = {}
for s in snapshots:
    by_date[s.get("display_date")] = s   # snapshots sorted ascending -> last write per date wins (latest)
dates = sorted(by_date.keys(), reverse=True)

sel_date = st.pills("Prediction date", [fmt_date(d) for d in dates],
                    default=fmt_date(dates[0]), key="ph_date", label_visibility="collapsed")
sel_iso = next((d for d in dates if fmt_date(d) == sel_date), dates[0])
selected = by_date[sel_iso]

# index for "previous meaningful" relative to the selected snapshot
order = snapshots  # ascending by (completed, generated_at)
sel_idx = max(i for i, s in enumerate(order) if s.get("snapshot_id") == selected.get("snapshot_id"))
previous = order[sel_idx - 1] if sel_idx > 0 else None
is_latest = sel_idx == len(order) - 1


def champ_prob_map(snap):
    return {c["team"]: c.get("probability") for c in (snap.get("main_forecast", {}).get("champion_probabilities") or [])}


def render_meta(snap, title):
    mf = snap.get("main_forecast", {})
    cls = snap.get("record_class", "")
    cls_kind = "genuine" if cls == "genuine_archived_forecast" else "recovered"
    cls_label = "Genuine archived forecast" if cls_kind == "genuine" else "Recovered from committed output"
    st.markdown(f'<div class="ph-sec">{title}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="ph-meta">'
        f'<span class="ph-tag">Generated <b>{fmt_dt(snap.get("generated_at"))}</b></span>'
        f'<span class="ph-tag">Phase <b>{str(snap.get("tournament_phase","")).title()}</b></span>'
        f'<span class="ph-tag">Completed <b>{snap.get("completed_matches")}</b></span>'
        f'<span class="ph-tag">Sims <b>{(snap.get("simulation_count") or 0):,}</b></span>'
        f'<span class="ph-tag">Source quality <b>{snap.get("source_quality_score")}</b></span>'
        f'<span class="ph-class {cls_kind}">{cls_label}</span>'
        f'</div>', unsafe_allow_html=True)


def render_forecast(snap):
    # Build the whole card as ONE html string — Streamlit sanitises each st.markdown call
    # independently, so a wrapper element must open and close within a single call.
    mf = snap.get("main_forecast", {})
    champ = mf.get("most_likely_champion") or {}
    final = mf.get("most_likely_final") or {}
    html = ['<div class="ph-card">']
    html.append(
        f'<div class="ph-champ">{flag(champ.get("team"), 34)}'
        f'<span class="name">{champ.get("team","—")}</span>'
        f'<span class="pct">{pctf(champ.get("probability"))}</span></div>'
        f'<div class="ph-row" style="color:{FG3}">Most likely champion at this point</div>')
    if final.get("team_1"):
        html.append(
            f'<div class="ph-row" style="margin-top:.6rem"><span class="t">Projected final</span>'
            f'<span class="v">{final.get("team_1")} vs {final.get("team_2")} · {pctf(final.get("probability"))}</span></div>')
    html.append(f'<div class="ph-row" style="margin-top:.7rem;color:{FG3}">Champion probabilities</div>')
    top = (mf.get("champion_probabilities") or [])[:6]
    mx = max([c.get("probability") or 0 for c in top], default=1) or 1
    for i, c in enumerate(top):
        p = c.get("probability") or 0
        col = GOLD if i == 0 else CYAN
        html.append(
            f'<div class="ph-row">{flag(c.get("team"),20)}<span class="t" style="min-width:90px">{c.get("team")}</span>'
            f'<span class="ph-bar"><span style="width:{p/mx*100:.0f}%;background:{col}"></span></span>'
            f'<span class="v">{pctf(p)}</span></div>')
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def render_matches(snap):
    e = enrich_snapshot(snap, results) if enrich_snapshot else snap
    preds = e.get("matchday_predictions", [])
    if not preds:
        st.caption("No upcoming-match predictions were pending in this snapshot.")
        return
    for m in preds:
        a, b = m.get("team_a"), m.get("team_b")
        pa, pb = m.get("team_a_win_probability") or 0, m.get("team_b_win_probability") or 0
        winner = m.get("predicted_winner")
        outcome = m.get("prediction_outcome", "pending")
        a_win = winner == a
        actual = m.get("actual_winner")
        foot = f'<span class="ph-method">{m.get("prediction_method","model")}</span>'
        if actual:
            foot += (f'<span>Actual: <b style="color:#eef4fd">{actual}</b>'
                     f'{" (" + m.get("actual_score") + ")" if m.get("actual_score") else ""}</span>'
                     f'<span class="ph-out {outcome}">{outcome.upper()}</span>')
        else:
            foot += '<span class="ph-out pending">PENDING</span>'
        kickoff = (m.get("scheduled_at") or "")[:10]
        st.markdown(
            f'<div class="ph-match"><div class="head">{m.get("stage","")} · {kickoff}'
            f' &nbsp;•&nbsp; predicted winner: <b style="color:{GOLD}">{winner}</b></div>'
            f'<div class="ph-side {"win" if a_win else ""}">{flag(a,22)}<span class="nm">{a}</span>'
            f'<span class="p" style="color:{GOLD if a_win else FG2}">{pctf(pa)}</span></div>'
            f'<div class="ph-side {"win" if not a_win else ""}">{flag(b,22)}<span class="nm">{b}</span>'
            f'<span class="p" style="color:{GOLD if not a_win else FG2}">{pctf(pb)}</span></div>'
            f'<div class="ph-foot">{foot}</div></div>', unsafe_allow_html=True)


def render_movement(cur, prev):
    if not prev:
        return
    cur_m, prev_m = champ_prob_map(cur), champ_prob_map(prev)
    teams_all = list(dict.fromkeys(list(prev_m.keys()) + list(cur_m.keys())))
    rows = []
    for t in teams_all:
        before, after = prev_m.get(t), cur_m.get(t)
        if after is None:
            rows.append((t, before, None, "Eliminated"))
        elif before is None:
            rows.append((t, None, after, "New"))
        else:
            rows.append((t, before, after, f"{(after-before)*100:+.1f} pts"))
    rows.sort(key=lambda r: -(r[2] or 0))
    st.markdown(f'<div class="ph-row" style="color:{FG3};margin-top:.2rem">Champion-probability movement vs previous update</div>', unsafe_allow_html=True)
    for t, before, after, delta in rows[:6]:
        color = CRIMSON if delta == "Eliminated" else (PITCH if (after or 0) >= (before or 0) else AMBER)
        b_txt = pctf(before) if before is not None else "—"
        a_txt = pctf(after) if after is not None else "Eliminated"
        st.markdown(
            f'<div class="ph-row">{flag(t,20)}<span class="t" style="min-width:90px">{t}</span>'
            f'<span style="color:{FG2}">{b_txt} → </span><span class="v" style="color:{color}">{a_txt}</span>'
            f'<span style="margin-left:.5rem;color:{color};font-size:.8rem">{delta}</span></div>', unsafe_allow_html=True)


# ================= layout =================
st.info("**Confirmed** results come from football-data.org. **Historical predictions** are the model's odds *before* "
        "each match — preserved exactly. **Current prediction** is the latest live forecast. Historical predictions are "
        "never presented as results.", icon="ℹ️")

col1, col2 = st.columns(2, gap="large")
with col1:
    render_meta(selected, "Current Update" if is_latest else f"Selected Forecast · {fmt_date(sel_iso)}")
    render_forecast(selected)
    if previous:
        st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
        render_movement(selected, previous)
with col2:
    st.markdown('<div class="ph-sec">Matchday Predictions</div>', unsafe_allow_html=True)
    st.caption("What the model predicted for the matches that were upcoming when this forecast was made.")
    render_matches(selected)

if previous:
    st.divider()
    st.markdown('<div class="ph-sec" style="font-size:1.15rem">Previous Matchday Update</div>', unsafe_allow_html=True)
    pcol1, pcol2 = st.columns(2, gap="large")
    with pcol1:
        render_meta(previous, "")
        render_forecast(previous)
    with pcol2:
        st.markdown('<div class="ph-sec">Matchday Predictions</div>', unsafe_allow_html=True)
        render_matches(previous)
