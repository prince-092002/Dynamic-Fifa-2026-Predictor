import Link from "next/link";
import Bracket from "@/components/Bracket";
import ProbBar from "@/components/ProbBar";
import {
  formatPct,
  formatPhase,
  getBracket,
  getChampionForecast,
  getFinalistPairs,
  getMatchupPredictions,
  getOverview,
} from "@/lib/data";

const BADGES = ["Python", "XGBoost", "Monte Carlo", "Streamlit", "Next.js", "Plotly", "football-data.org", "Automated Validation"];

const HIGHLIGHTS = [
  ["Live XGBoost predictions", "Newly resolved knockout matchups automatically get leakage-safe features and fresh model probabilities."],
  ["Completed results locked", "Real results are immutable in simulation — a finished match is never re-simulated."],
  ["Monte Carlo simulation", "Thousands of full-bracket tournament simulations per forecast run, seeded and reproducible."],
  ["19-check integrity validation", "Eliminated-team, source-labeling, probability-sum, and freshness checks run on every forecast."],
  ["Quality-gated forecast mode", "A live quality gate decides whether output may be called a true live forecast — fallback is never mislabeled."],
  ["Verified feature equivalence", "The optimized live feature path was proven identical to the original (112/112 values exact) before becoming default."],
  ["Probability-source audit trail", "Every simulation decision is attributed: real result, live model, pre-tournament model, or Elo fallback."],
  ["Automated matchday workflow", "One command refreshes state, predicts new matchups, re-simulates, validates, and rebuilds these exports."],
];

export default function Home() {
  const overview = getOverview();
  const bracket = getBracket();
  const champion = getChampionForecast();
  const pairs = getFinalistPairs();
  const matchups = getMatchupPredictions();

  return (
    <div className="space-y-16 py-10">
      <section className="text-center">
        <h1 className="mx-auto max-w-3xl bg-gradient-to-r from-cyan via-blue to-magenta bg-clip-text text-4xl font-extrabold tracking-tight text-transparent md:text-5xl">
          Dynamic FIFA 2026 Tournament Outcome Predictor
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-fg2">
          A live machine-learning forecasting system that combines real tournament results, XGBoost matchup probabilities, and Monte Carlo
          simulation to continuously update finalist and champion forecasts.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          {process.env.NEXT_PUBLIC_DASHBOARD_URL && (
            <a href={process.env.NEXT_PUBLIC_DASHBOARD_URL} target="_blank" rel="noreferrer" className="rounded-lg bg-cyan px-5 py-2.5 font-semibold text-bg hover:opacity-90">
              Explore Dashboard
            </a>
          )}
          <a href="#forecast" className="rounded-lg bg-surface2 px-5 py-2.5 font-semibold hover:bg-surface">View Live Forecast</a>
          <Link href="/teams" className="rounded-lg bg-surface2 px-5 py-2.5 font-semibold hover:bg-surface">Explore Teams</Link>
          {process.env.NEXT_PUBLIC_GITHUB_URL && (
            <a href={process.env.NEXT_PUBLIC_GITHUB_URL} target="_blank" rel="noreferrer" className="rounded-lg border border-line px-5 py-2.5 font-semibold hover:bg-surface">
              View Source Code
            </a>
          )}
        </div>
        <ul className="mt-6 flex flex-wrap justify-center gap-2">
          {BADGES.map((badge) => (
            <li key={badge} className="rounded-full border border-line bg-surface px-3 py-1 text-xs text-fg2">{badge}</li>
          ))}
        </ul>
        <p className="mt-4 text-xs text-fg2">Independent analytics project. Not affiliated with or endorsed by FIFA.</p>
      </section>

      {overview ? (
        <section aria-labelledby="snapshot-heading">
          <h2 id="snapshot-heading" className="mb-4 text-2xl font-bold">Current tournament snapshot</h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              ["Current phase", formatPhase(overview.current_phase)],
              ["Completed matches", overview.completed_matches ?? "—"],
              ["Teams still alive", overview.teams_alive],
              ["Teams eliminated", overview.teams_eliminated],
              ["Title favorite", overview.top_champion ?? "—"],
              ["Championship estimate", formatPct(overview.top_champion_probability)],
              ["Top projected final", overview.top_finalist_pair ?? "—"],
              ["Unresolved matchups", overview.known_unresolved_matchups],
              ["Forecast mode", overview.forecast_mode === "true_live_forecast" ? "True live" : formatPhase(overview.forecast_mode)],
              ["Data freshness", overview.data_source_mode === "fresh_api" ? `Fresh (${overview.data_age_minutes ?? 0} min)` : overview.data_source_mode],
              ["Live validation", overview.live_forecast_validation === "pass" ? "Passed" : overview.live_forecast_validation ?? "—"],
              ["Simulations", overview.simulations ? overview.simulations.toLocaleString() : "—"],
            ].map(([label, value]) => (
              <div key={String(label)} className="card p-4">
                <p className="text-xs uppercase tracking-wider text-fg2">{label}</p>
                <p className="mt-1 text-lg font-bold">{value}</p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-fg2">
            {overview.public_label} · generated {overview._meta?.generated_at ?? ""} · run {overview.run_id ?? ""}
          </p>
        </section>
      ) : (
        <section className="card p-6 text-fg2">Current tournament snapshot unavailable. Run the live forecast pipeline and rebuild public exports.</section>
      )}

      <section id="forecast" aria-labelledby="forecast-heading" className="scroll-mt-20">
        <h2 id="forecast-heading" className="mb-4 text-2xl font-bold">Champion forecast</h2>
        {champion?.entries?.length ? (
          <div className="grid gap-8 md:grid-cols-2">
            <div className="card space-y-3 p-5">
              <h3 className="font-semibold text-fg2">Championship probability — current model favorite first</h3>
              {champion.entries
                .slice()
                .sort((a, b) => b.champion_probability - a.champion_probability)
                .map((entry, index) => (
                  <ProbBar key={entry.team} label={entry.team} value={entry.champion_probability} color={index === 0 ? "var(--accent-magenta)" : "var(--accent-cyan)"} />
                ))}
              <p className="pt-1 text-xs text-fg2">{champion.simulations ? `${champion.simulations.toLocaleString()} Monte Carlo simulations` : ""}</p>
            </div>
            <div className="card space-y-3 p-5">
              <h3 className="font-semibold text-fg2">Most likely projected finals</h3>
              {(pairs?.entries ?? [])
                .slice()
                .sort((a, b) => b.probability - a.probability)
                .slice(0, 8)
                .map((pair) => (
                  <ProbBar key={pair.finalist_pair_key} label={pair.finalist_pair_key} value={pair.probability} color="var(--accent-blue)" />
                ))}
              {matchups?.matchups?.length ? (
                <div className="pt-2">
                  <h4 className="mb-2 text-sm font-semibold text-fg2">Next matchup predictions (live XGBoost)</h4>
                  <ul className="space-y-1 text-sm">
                    {matchups.matchups
                      .filter((matchup) => matchup.prediction_status === "predicted")
                      .map((matchup) => (
                        <li key={`${matchup.team_a}-${matchup.team_b}`}>
                          {matchup.team_a} <span className="font-mono text-cyan">{formatPct(matchup.team_a_advance_probability, 1)}</span> vs{" "}
                          {matchup.team_b} <span className="font-mono text-cyan">{formatPct(matchup.team_b_advance_probability, 1)}</span>
                          <span className="text-fg2"> · {matchup.stage}</span>
                        </li>
                      ))}
                  </ul>
                </div>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="card p-6 text-fg2">Current champion forecast unavailable. Run the live forecast pipeline first.</div>
        )}
        <p className="mt-2 text-xs text-fg2">Highest estimated championship probability from the latest live forecast — probabilistic estimates, not guarantees.</p>
      </section>

      <section id="bracket" aria-labelledby="bracket-heading" className="scroll-mt-20">
        <h2 id="bracket-heading" className="mb-4 text-2xl font-bold">Knockout bracket</h2>
        {bracket ? <Bracket bracket={bracket} /> : <div className="card p-6 text-fg2">Bracket data unavailable.</div>}
      </section>

      <section aria-labelledby="engineering-heading">
        <h2 id="engineering-heading" className="mb-4 text-2xl font-bold">Engineering highlights</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {HIGHLIGHTS.map(([title, body]) => (
            <div key={title} className="card p-4">
              <h3 className="font-semibold text-cyan">{title}</h3>
              <p className="mt-1 text-sm text-fg2">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 text-sm text-fg2">
          Full details on the <Link href="/methodology" className="text-cyan underline-offset-2 hover:underline">methodology page</Link>.
        </p>
      </section>
    </div>
  );
}
