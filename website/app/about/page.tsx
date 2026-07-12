import type { Metadata } from "next";
import Link from "next/link";
import { Kicker, Disclaimer } from "@/components/ui";
import { Globe, Network, Lock, Shield, Sim, Trophy, Arrow, Lab } from "@/components/icons";

export const metadata: Metadata = { title: "About — FIFA 2026 Tournament Intelligence" };

const PRINCIPLES = [
  ["Completed real results are locked and never re-simulated.", <Lock key="1" width={16} height={16} />],
  ["Elo fallback probabilities are never labeled as XGBoost predictions.", <Shield key="2" width={16} height={16} />],
  ["Cached or snapshot data is never presented as fresh.", <Globe key="3" width={16} height={16} />],
  ["Placeholder TBD slots are never shown as real teams.", <Trophy key="4" width={16} height={16} />],
  ["Every forecast leaves an auditable manifest and probability-source trail.", <Sim key="5" width={16} height={16} />],
];

export default function AboutPage() {
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
  return (
    <div className="relative">
      <div className="bg-floodlight bg-grid absolute inset-x-0 top-0 h-56 opacity-70" aria-hidden />
      <div className="relative mx-auto max-w-3xl px-4 py-14">
        <Kicker icon={<Globe width={14} height={14} />}>About the project</Kicker>
        <h1 className="display mt-3 text-4xl text-fg">A serious football intelligence platform</h1>
        <p className="mt-4 text-fg2">The Dynamic FIFA 2026 Tournament Outcome Predictor is an end-to-end sports-analytics system built as a portfolio project. It ingests real FIFA World Cup 2026 results from football-data.org, generates leakage-safe machine-learning features, predicts each resolved knockout matchup with a trained XGBoost model, and runs Monte Carlo tournament simulations to estimate finalist and champion probabilities — all refreshed with a single command after every real match.</p>

        <div className="card mt-8 p-6">
          <div className="flex items-center gap-2 text-cyan"><Network width={17} height={17} /><h2 className="font-display font-semibold text-fg">Architecture</h2></div>
          <pre className="mt-3 overflow-x-auto text-sm text-fg2">{`GitHub  ──►  Vercel website (static, rebuilt on push)
        └─►  Streamlit dashboard (interactive analytics)
                     ▲
        public-safe JSON exports
                     ▲
   Python · XGBoost · Monte Carlo backend
   football-data.org · quality gate · validation suite`}</pre>
        </div>

        <div className="card mt-4 p-6">
          <div className="flex items-center gap-2 text-cyan"><Shield width={17} height={17} /><h2 className="font-display font-semibold text-fg">Honesty principles</h2></div>
          <ul className="mt-3 space-y-2">
            {PRINCIPLES.map(([t, ic]) => (
              <li key={t as string} className="flex items-start gap-2.5 text-sm text-fg2"><span className="mt-0.5 text-pitch">{ic as React.ReactNode}</span>{t as string}</li>
            ))}
            <li className="flex items-start gap-2.5 text-sm text-fg3"><span className="mt-0.5">•</span>Player-level statistics are not currently part of the verified data pipeline, so none are shown.</li>
          </ul>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          {dashboard && <a href={dashboard} target="_blank" rel="noreferrer" className="btn btn-primary">Open the Dashboard <Arrow width={16} height={16} /></a>}
          {github && <a href={github} target="_blank" rel="noreferrer" className="btn btn-ghost">View Source Code</a>}
          <Link href="/methodology" className="btn btn-ghost">Analytics Lab <Lab width={16} height={16} /></Link>
        </div>
        <Disclaimer className="mt-8" />
      </div>
    </div>
  );
}
