import type { Metadata } from "next";
import ProbBar from "@/components/ProbBar";
import { getModelInsights } from "@/lib/data";

export const metadata: Metadata = { title: "Methodology — FIFA 2026 Predictor" };

const LADDER = [
  ["1. Completed real result", "Locked as truth; a finished match is never re-simulated."],
  ["2. Live XGBoost prediction", "Resolved real matchups get leakage-safe features and fresh model probabilities."],
  ["3. Pre-tournament model prediction", "Used when a simulated pairing matches the original fixture list."],
  ["4. Elo fallback", "Hypothetical future branches whose real participants are not yet known."],
  ["5. Neutral fallback", "Flat prior when no rating exists — always labeled, never hidden."],
];

const FEATURE_GROUPS: [string, (f: string) => boolean][] = [
  ["Elo-derived strength", (f) => f.includes("elo")],
  ["Recent form", (f) => f.includes("form") || f.includes("win_rate") || f.includes("loss_rate")],
  ["Goal-based form", (f) => f.includes("goal") || f.includes("clean_sheet")],
  ["Head-to-head", (f) => f.startsWith("h2h")],
  ["Tournament context", (f) => f.startsWith("is_") || f.includes("importance") || f.includes("stage")],
  ["Rest & schedule", (f) => f.includes("days") || f.includes("congestion") || f.includes("rest")],
];

export default function MethodologyPage() {
  const insights = getModelInsights();
  const grouped: Record<string, string[]> = {};
  const remaining = new Set(insights?.selected_feature_columns ?? []);
  for (const [group, predicate] of FEATURE_GROUPS) {
    grouped[group] = [...remaining].filter(predicate);
    grouped[group].forEach((f) => remaining.delete(f));
  }

  return (
    <div className="space-y-12 py-10">
      <div>
        <h1 className="text-3xl font-bold">Methodology</h1>
        <p className="mt-2 max-w-3xl text-fg2">
          How real results, machine learning, and simulation combine into a continuously updated tournament forecast — with validation at every step.
        </p>
      </div>

      <section aria-labelledby="architecture-heading">
        <h2 id="architecture-heading" className="mb-3 text-xl font-bold">System architecture</h2>
        <pre className="card overflow-x-auto p-5 text-sm text-fg2">{`Historical match data (~50,000 international matches)
        ↓  leakage-safe feature engineering (chronological, shift-before-rolling)
Model comparison (baselines, logistic regression, XGBoost)
        ↓  selected XGBoost win/draw/loss classifier
Live knockout feature generation (completed real results as history)
        ↓  current matchup probabilities
Monte Carlo tournament simulation (completed results locked)
        ↓
Champion & finalist forecasts  →  validation + audit manifest  →  this website`}</pre>
      </section>

      <section aria-labelledby="model-heading">
        <h2 id="model-heading" className="mb-3 text-xl font-bold">Model selection (actual test metrics)</h2>
        {insights?.models?.length ? (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-fg2">
                  <th className="p-3">Model</th>
                  <th className="p-3">Accuracy</th>
                  <th className="p-3">Log loss</th>
                  <th className="p-3">Brier</th>
                  <th className="p-3">Macro F1</th>
                  <th className="p-3">Selected</th>
                </tr>
              </thead>
              <tbody>
                {insights.models.map((model) => (
                  <tr key={model.model} className="border-b border-line/50">
                    <td className="p-3 font-semibold">{model.model}</td>
                    <td className="p-3 font-mono">{model.test_accuracy ?? "—"}</td>
                    <td className="p-3 font-mono">{model.test_log_loss ?? "—"}</td>
                    <td className="p-3 font-mono">{model.test_brier_score ?? "—"}</td>
                    <td className="p-3 font-mono">{model.test_macro_f1 ?? "—"}</td>
                    <td className="p-3">{model.selected ? "✅" : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-fg2">Model metrics unavailable.</p>
        )}
      </section>

      <section aria-labelledby="features-heading">
        <h2 id="features-heading" className="mb-3 text-xl font-bold">Model input features ({insights?.selected_feature_columns?.length ?? 0})</h2>
        <div className="grid gap-3 md:grid-cols-3">
          {Object.entries(grouped)
            .filter(([, features]) => features.length)
            .map(([group, features]) => (
              <div key={group} className="card p-4">
                <h3 className="font-semibold text-cyan">{group}</h3>
                <ul className="mt-2 space-y-1 text-xs text-fg2">
                  {features.map((feature) => (
                    <li key={feature} className="font-mono">{feature}</li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      </section>

      {insights?.global_feature_importance && (
        <section aria-labelledby="importance-heading">
          <h2 id="importance-heading" className="mb-3 text-xl font-bold">Top 10 global XGBoost feature importances</h2>
          <div className="card space-y-2 p-5">
            {insights.global_feature_importance.slice(0, 10).map((entry) => (
              <ProbBar key={entry.feature} label={entry.feature} value={entry.importance / (insights.global_feature_importance![0].importance || 1)} color="var(--accent-green)" />
            ))}
            <p className="pt-1 text-xs text-fg2">Bars normalized to the top feature. {insights.importance_note}</p>
          </div>
        </section>
      )}

      <section aria-labelledby="leakage-heading">
        <h2 id="leakage-heading" className="mb-3 text-xl font-bold">Leakage prevention</h2>
        <ul className="card list-inside list-disc space-y-2 p-5 text-sm text-fg2">
          <li>The target match outcome never enters its own features.</li>
          <li>Only completed matches enter history; unplayed placeholder rows with missing goals are excluded.</li>
          <li>Rolling and form features are sorted chronologically and shifted before rolling windows.</li>
          <li>The target matchup never enters its own historical feature calculation.</li>
          <li>The optimized live feature path was equivalence-tested against the original: 112/112 values exactly identical.</li>
        </ul>
      </section>

      <section aria-labelledby="ladder-heading">
        <h2 id="ladder-heading" className="mb-3 text-xl font-bold">Probability source ladder</h2>
        <div className="space-y-2">
          {LADDER.map(([title, body]) => (
            <div key={title} className="card p-4">
              <h3 className="font-semibold">{title}</h3>
              <p className="text-sm text-fg2">{body}</p>
            </div>
          ))}
        </div>
        <p className="mt-3 max-w-3xl text-sm text-fg2">
          Future semifinal/final pairings only exist inside each simulated branch, so they use Elo until the real bracket resolves them — at which
          point the next matchday update automatically generates XGBoost predictions for the newly known matchups. Every simulation decision is
          attributed to its source, and Elo fallback is never presented as a model prediction.
        </p>
      </section>
    </div>
  );
}
