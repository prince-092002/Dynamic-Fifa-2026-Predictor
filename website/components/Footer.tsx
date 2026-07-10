import Link from "next/link";

export default function Footer() {
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  return (
    <footer className="mt-16 border-t border-line bg-bg2">
      <div className="mx-auto max-w-6xl px-4 py-8 text-sm text-fg2">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <p className="font-semibold text-fg">Built by Abel · Dynamic FIFA 2026 Tournament Outcome Predictor</p>
          <ul className="flex flex-wrap gap-4">
            {github && (
              <li>
                <a className="hover:text-cyan" href={github} target="_blank" rel="noreferrer">GitHub</a>
              </li>
            )}
            {dashboard && (
              <li>
                <a className="hover:text-cyan" href={dashboard} target="_blank" rel="noreferrer">Interactive Dashboard</a>
              </li>
            )}
            <li>
              <Link className="hover:text-cyan" href="/methodology">Methodology</Link>
            </li>
          </ul>
        </div>
        <p className="mt-4">
          Independent analytics project. Not affiliated with or endorsed by FIFA. Predictions are probabilistic estimates, not guarantees.
        </p>
      </div>
    </footer>
  );
}
