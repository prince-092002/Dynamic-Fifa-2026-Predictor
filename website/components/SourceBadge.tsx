const STYLES: Record<string, { label: string; className: string; symbol: string }> = {
  completed_result: { label: "Completed result", className: "bg-green/15 text-green", symbol: "✓" },
  live_model: { label: "Live XGBoost prediction", className: "bg-cyan/15 text-cyan", symbol: "◆" },
  model_exact: { label: "Pre-tournament model", className: "bg-blue/15 text-blue", symbol: "◇" },
  elo_fallback: { label: "Elo fallback", className: "bg-warn/15 text-warn", symbol: "△" },
  neutral_fallback: { label: "Neutral fallback", className: "bg-hot/15 text-hot", symbol: "○" },
  unresolved_tbd: { label: "Awaiting participants", className: "bg-surface2 text-fg2", symbol: "…" },
};

export default function SourceBadge({ source }: { source: string }) {
  const style = STYLES[source] ?? { label: source, className: "bg-surface2 text-fg2", symbol: "•" };
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ${style.className}`}>
      <span aria-hidden>{style.symbol}</span>
      {style.label}
    </span>
  );
}

export function SourceLegend() {
  return (
    <div className="flex flex-wrap gap-2" aria-label="Probability source legend">
      {Object.keys(STYLES).map((key) => (
        <SourceBadge key={key} source={key} />
      ))}
    </div>
  );
}
