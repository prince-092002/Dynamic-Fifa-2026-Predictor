import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "About — FIFA 2026 Predictor" };

export default function AboutPage() {
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
  return (
    <div className="max-w-3xl space-y-8 py-10">
      <h1 className="text-3xl font-bold">About this project</h1>
      <p className="text-fg2">
        The Dynamic FIFA 2026 Tournament Outcome Predictor is an end-to-end sports analytics system built as a portfolio project. It ingests real
        FIFA World Cup 2026 results from football-data.org, generates leakage-safe machine-learning features, predicts each resolved knockout
        matchup with a trained XGBoost model, and runs Monte Carlo tournament simulations to estimate finalist and champion probabilities — all
        refreshed with a single command after every real match.
      </p>
      <div className="card p-5">
        <h2 className="font-bold">Architecture</h2>
        <pre className="mt-2 overflow-x-auto text-sm text-fg2">{`GitHub (source + docs + public data)
   ├── Vercel — this website (static, rebuilt on push)
   └── Streamlit — interactive analytics dashboard
             ↑
   Public-safe JSON exports
             ↑
   Python + XGBoost + Monte Carlo backend`}</pre>
      </div>
      <div className="card p-5">
        <h2 className="font-bold">Honesty principles</h2>
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-fg2">
          <li>Completed real results are locked and never re-simulated.</li>
          <li>Elo fallback probabilities are never labeled as XGBoost predictions.</li>
          <li>Cached or snapshot data is never presented as fresh.</li>
          <li>Placeholder TBD slots are never shown as real teams.</li>
          <li>Every forecast run leaves an auditable manifest, validation report, and probability-source trail.</li>
          <li>Player-level statistics are not currently part of the verified data pipeline, so none are shown.</li>
        </ul>
      </div>
      <div className="flex flex-wrap gap-3">
        {github && (
          <a href={github} target="_blank" rel="noreferrer" className="rounded-lg bg-surface2 px-5 py-2.5 font-semibold hover:bg-surface">
            View Source Code ↗
          </a>
        )}
        {dashboard && (
          <a href={dashboard} target="_blank" rel="noreferrer" className="rounded-lg bg-cyan px-5 py-2.5 font-semibold text-bg hover:opacity-90">
            Open the Dashboard ↗
          </a>
        )}
        <Link href="/methodology" className="rounded-lg border border-line px-5 py-2.5 font-semibold hover:bg-surface">
          Read the Methodology
        </Link>
      </div>
      <p className="text-xs text-fg2">Independent analytics project. Not affiliated with or endorsed by FIFA. Predictions are probabilistic estimates, not guarantees.</p>
    </div>
  );
}
