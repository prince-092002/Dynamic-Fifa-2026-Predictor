import CountryFlag from "./CountryFlag";

export default function ProbBar({
  label,
  value,
  code,
  color = "var(--accent-cyan)",
}: {
  label: string;
  value: number;
  code?: string | null;
  color?: string;
}) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  return (
    <div className="flex items-center gap-3" role="group" aria-label={`${label}: ${pct.toFixed(2)} percent`}>
      <span className="flex w-40 shrink-0 items-center gap-2 truncate text-sm">
        <CountryFlag code={code} country={label} size="sm" />
        <span className="truncate">{label}</span>
      </span>
      <div className="h-3 flex-1 overflow-hidden rounded-full bg-surface2">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="w-16 shrink-0 text-right font-mono text-sm text-fg">{pct.toFixed(2)}%</span>
    </div>
  );
}
