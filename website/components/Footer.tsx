import Link from "next/link";
import { Trophy } from "./icons";

export default function Footer() {
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  return (
    <footer className="relative mt-24 border-t border-line/70 bg-bg2">
      <div className="bg-pitch-glow absolute inset-0" aria-hidden />
      <div className="relative mx-auto max-w-[78rem] px-4 py-12">
        <div className="flex flex-wrap items-start justify-between gap-8">
          <div className="max-w-sm">
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-lg border border-line-strong bg-surface text-pitch"><Trophy width={17} height={17} /></span>
              <span className="font-display text-sm font-bold">Dynamic FIFA 2026 · Tournament Intelligence</span>
            </div>
            <p className="mt-3 text-sm text-fg2">Live football forecasting — historical data, Elo, XGBoost matchup probabilities, and Monte Carlo tournament simulation. Built by Abel.</p>
          </div>
          <nav className="grid grid-cols-2 gap-x-12 gap-y-2 text-sm" aria-label="Footer">
            <Link className="text-fg2 hover:text-cyan" href="/">Home</Link>
            <Link className="text-fg2 hover:text-cyan" href="/teams">Teams</Link>
            <Link className="text-fg2 hover:text-cyan" href="/methodology">Analytics Lab</Link>
            <Link className="text-fg2 hover:text-cyan" href="/about">About</Link>
            {github && <a className="text-fg2 hover:text-cyan" href={github} target="_blank" rel="noreferrer">GitHub</a>}
            {dashboard && <a className="text-fg2 hover:text-cyan" href={dashboard} target="_blank" rel="noreferrer">Dashboard</a>}
          </nav>
        </div>
        <div className="hairline my-8" />
        <p className="text-xs text-fg3">Independent football analytics project. Not affiliated with or endorsed by FIFA. Team names and results via football-data.org. Predictions are probabilistic estimates, not guarantees.</p>
      </div>
    </footer>
  );
}
