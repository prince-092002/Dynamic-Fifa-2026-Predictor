import type { ReactNode } from "react";

export function Section({ id, children, className = "" }: { id?: string; children: ReactNode; className?: string }) {
  return (
    <section id={id} className={`scroll-mt-24 py-14 md:py-20 ${className}`}>
      {children}
    </section>
  );
}

export function Kicker({ icon, children }: { icon?: ReactNode; children: ReactNode }) {
  return (
    <span className="kicker inline-flex items-center gap-2">
      {icon && <span className="text-cyan">{icon}</span>}
      {children}
    </span>
  );
}

export function SectionHead({ kicker, title, sub, icon }: { kicker?: string; title: string; sub?: string; icon?: ReactNode }) {
  return (
    <div className="mb-8 max-w-2xl">
      {kicker && <Kicker icon={icon}>{kicker}</Kicker>}
      <h2 className="display mt-3 text-3xl md:text-4xl text-fg">{title}</h2>
      {sub && <p className="mt-3 text-fg2">{sub}</p>}
    </div>
  );
}

/** Probability ring (SVG). value in 0..1. */
export function ProbRing({ value, size = 68, stroke = 7, color = "var(--cyan)", label }: { value: number; size?: number; stroke?: number; color?: string; label?: string }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div className="relative inline-grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(51,69,106,0.4)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - pct)} />
      </svg>
      <div className="absolute text-center">
        <div className="stat-num text-fg" style={{ fontSize: size * 0.24 }}>{(pct * 100).toFixed(1)}</div>
        {label && <div className="text-[0.55rem] uppercase tracking-wider text-fg3">{label}</div>}
      </div>
    </div>
  );
}

/** Semantic meter bar. */
export function Meter({ value, color = "var(--cyan)" }: { value: number; color?: string }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="meter" role="meter" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}>
      <span style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function StatCard({ icon, label, value, hint, accent = "var(--cyan)", className = "" }: { icon?: ReactNode; label: string; value: ReactNode; hint?: string; accent?: string; className?: string }) {
  return (
    <div className={`card card-hover p-4 ${className}`}>
      <div className="flex items-center gap-2 text-fg3">
        {icon && <span style={{ color: accent }}>{icon}</span>}
        <span className="text-[0.7rem] uppercase tracking-wider">{label}</span>
      </div>
      <div className="stat-num mt-2 text-2xl md:text-[1.7rem] text-fg">{value}</div>
      {hint && <div className="mt-1 text-xs text-fg2">{hint}</div>}
    </div>
  );
}

export function Disclaimer({ className = "" }: { className?: string }) {
  return <p className={`text-xs text-fg3 ${className}`}>Independent football analytics project. Not affiliated with or endorsed by FIFA. Predictions are probabilistic estimates, not guarantees.</p>;
}
