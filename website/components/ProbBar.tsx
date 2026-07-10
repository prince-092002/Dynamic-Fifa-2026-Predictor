export default function ProbBar({
  label,
  value,
  flag,
  color = "var(--accent-cyan)",
}: {
  label: string;
  value: number;
  flag?: string | null;
  color?: string;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="flex items-center gap-3" role="group" aria-label={`${label}: ${pct.toFixed(2)} percent`}>
      <span className="w-40 shrink-0 truncate text-sm">
        {flag ? `${flag} ` : ""}
        {label}
      </span>
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-surface2">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="w-16 shrink-0 text-right font-mono text-sm text-fg">{pct.toFixed(2)}%</span>
    </div>
  );
}
