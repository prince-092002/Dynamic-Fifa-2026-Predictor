import type { Metadata } from "next";
import { Meter } from "@/components/ui";
import { Lab, Network, Shield, Gauge, Chart, Check, Database, Sim, Trophy } from "@/components/icons";
import { getModelInsights } from "@/lib/data";

export const metadata: Metadata = { title: "Analytics Lab — Inside the Prediction Engine" };

const LADDER = [
  ["Completed real result", "Locked as truth; a finished match is never re-simulated.", "var(--pitch)"],
  ["Live XGBoost prediction", "Resolved real matchups get leakage-safe features and fresh model probabilities.", "var(--cyan)"],
  ["Pre-tournament model prediction", "When a simulated pairing matches the original fixture list.", "var(--blue)"],
  ["Elo fallback", "Hypothetical future branches whose real participants are not yet known.", "var(--amber)"],
  ["Neutral fallback", "Flat prior when no rating exists — always labeled, never hidden.", "var(--crimson)"],
];
const FGROUPS: [string, (f: string) => boolean][] = [
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
  for (const [g, p] of FGROUPS) { grouped[g] = [...remaining].filter(p); grouped[g].forEach((f) => remaining.delete(f)); }
  const maxImp = insights?.global_feature_importance?.[0]?.importance || 1;
  const diag = insights?.diagnostics;

  return (
    <>
      <div className="relative overflow-hidden border-b border-line/60">
        <div className="bg-grid bg-floodlight absolute inset-0 opacity-80" aria-hidden />
        <div className="relative mx-auto max-w-[78rem] px-4 pb-10 pt-14">
          <span className="kicker inline-flex items-center gap-2"><Lab width={14} height={14} className="text-cyan" /> Analytics Lab</span>
          <h1 className="display mt-3 text-4xl md:text-5xl text-fg">Inside the prediction engine</h1>
          <p className="mt-3 max-w-2xl text-fg2">How ~50,000 historical matches become a live, leakage-safe tournament forecast — the model, its diagnostics, the features that matter, and the validation that keeps it honest.</p>
        </div>
      </div>

      <div className="mx-auto max-w-[78rem] space-y-14 px-4 py-12">
        {/* architecture */}
        <section>
          <Head icon={<Network width={14} height={14} />} kicker="System architecture" title="From raw history to live forecast" />
          <ol className="grid gap-2 md:grid-cols-3 lg:grid-cols-6">
            {[["Historical data", <Database key="a" width={16} height={16} />], ["Leakage-safe features", <Shield key="b" width={16} height={16} />], ["XGBoost model", <Network key="c" width={16} height={16} />], ["Match probabilities", <Chart key="d" width={16} height={16} />], ["Monte Carlo", <Sim key="e" width={16} height={16} />], ["Live forecast", <Trophy key="f" width={16} height={16} />]].map(([t, ic], i) => (
              <li key={t as string} className="card p-3.5"><span className="text-cyan">{ic as React.ReactNode}</span><div className="mt-2 text-xs text-fg3">Stage {i + 1}</div><div className="font-display text-sm font-semibold text-fg">{t as string}</div></li>
            ))}
          </ol>
        </section>

        {/* model comparison */}
        {insights?.models?.length ? (
          <section>
            <Head icon={<Gauge width={14} height={14} />} kicker="Model performance" title="Model comparison" sub="Chronological 70/15/15 split · frozen test set of 7,439 matches. Selected by validation log loss (probability quality) — the metric the Monte Carlo simulator depends on." />
            <div className="grid gap-3 md:grid-cols-2">
              {insights.models.map((m) => (
                <div key={m.model} className={`p-5 ${m.selected ? "card-feature" : "card"}`}>
                  <div className="flex items-center justify-between">
                    <span className="font-display text-lg font-semibold text-fg">{m.model === "xgboost" ? "XGBoost" : "Logistic Regression"}</span>
                    {m.selected && <span className="chip !border-gold/40 !text-gold"><Check width={13} height={13} /> Production</span>}
                  </div>
                  <div className="mt-4 grid grid-cols-4 gap-2 text-center">
                    {[["Acc", m.test_accuracy], ["Log loss", m.test_log_loss], ["Brier", m.test_brier_score], ["Macro F1", m.test_macro_f1]].map(([l, v]) => (
                      <div key={l as string}><div className="stat-num text-lg text-fg">{v ?? "—"}</div><div className="text-[0.62rem] uppercase tracking-wide text-fg3">{l as string}</div></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {/* diagnostics — why macro F1 is lower */}
        {diag && (
          <section>
            <Head icon={<Chart width={14} height={14} />} kicker="Model diagnostics · Phase 5G" title="Why macro-F1 is lower — and why it doesn't matter here" sub={diag.evaluation} />
            <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-line text-left text-fg3"><th className="p-3">Outcome (test)</th><th className="p-3">Precision</th><th className="p-3">Recall</th><th className="p-3">F1</th><th className="p-3">Actual</th><th className="p-3">Predicted</th></tr></thead>
                  <tbody>
                    {Object.entries(diag.per_class).map(([cls, m]) => (
                      <tr key={cls} className="border-b border-line/50">
                        <td className="p-3 font-semibold text-fg">{cls.replace(/_/g, " ")}</td>
                        <td className="stat-num p-3 text-fg2">{m.precision ?? "—"}</td><td className="stat-num p-3 text-fg2">{m.recall ?? "—"}</td><td className="stat-num p-3 text-fg2">{m.f1 ?? "—"}</td>
                        <td className="stat-num p-3 text-fg2">{diag.actual_distribution[cls] ?? "—"}</td><td className="stat-num p-3 text-fg2">{diag.predicted_distribution[cls] ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="card rail p-5" style={{ ["--accent" as string]: "var(--cyan)" }}>
                <div className="flex items-center gap-2 pl-2 text-cyan"><Gauge width={16} height={16} /><span className="font-display text-sm font-semibold text-fg">Calibration first</span></div>
                <div className="stat-num mt-2 pl-2 text-3xl text-cyan">{diag.calibration_ece ?? "—"}</div>
                <div className="pl-2 text-xs text-fg3">Expected Calibration Error — near-perfect.</div>
                <p className="mt-3 pl-2 text-sm text-fg2">{diag.macro_f1_note}</p>
              </div>
            </div>
          </section>
        )}

        {/* feature importance */}
        {insights?.global_feature_importance && (
          <section>
            <Head icon={<Chart width={14} height={14} />} kicker="What drives predictions" title="Global feature importance" sub={insights.importance_note} />
            <div className="card space-y-2.5 p-6">
              {insights.global_feature_importance.slice(0, 10).map((e) => (
                <div key={e.feature} className="flex items-center gap-3">
                  <span className="w-64 shrink-0 truncate font-mono text-xs text-fg2">{e.feature}</span>
                  <div className="flex-1"><Meter value={e.importance / maxImp} color="var(--pitch)" /></div>
                  <span className="stat-num w-14 shrink-0 text-right text-xs text-fg3">{(e.importance * 100).toFixed(1)}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* feature families */}
        <section>
          <Head icon={<Database width={14} height={14} />} kicker="Feature foundation" title={`${insights?.selected_feature_columns?.length ?? 0} model input features`} />
          <div className="grid gap-3 md:grid-cols-3">
            {Object.entries(grouped).filter(([, f]) => f.length).map(([g, f]) => (
              <div key={g} className="card p-4"><h3 className="font-display text-sm font-semibold text-cyan">{g}</h3><ul className="mt-2 space-y-1">{f.map((x) => <li key={x} className="font-mono text-xs text-fg3">{x}</li>)}</ul></div>
            ))}
          </div>
        </section>

        {/* validation + ladder */}
        <section>
          <Head icon={<Shield width={14} height={14} />} kicker="Kept honest" title="Validation principles" />
          <div className="flex flex-wrap gap-2">
            {["Pre-match features only", "Chronological split", "Shift-before-rolling", "No future results", "Completed matches locked", "Fixed-seed reproducibility", "Feature equivalence proven"].map((p) => (
              <span key={p} className="chip"><Check width={14} height={14} className="text-pitch" /> {p}</span>
            ))}
          </div>
          <h3 className="mt-8 font-display text-lg font-semibold text-fg">Probability source ladder</h3>
          <div className="mt-3 space-y-2">
            {LADDER.map(([t, d, c], i) => (
              <div key={t} className="card rail flex items-start gap-3 p-4" style={{ ["--accent" as string]: c }}>
                <span className="stat-num pl-1 text-sm" style={{ color: c }}>{i + 1}</span>
                <div><div className="font-display text-sm font-semibold text-fg">{t}</div><p className="text-sm text-fg2">{d}</p></div>
              </div>
            ))}
          </div>
          <p className="mt-4 max-w-3xl text-sm text-fg2">Future semifinal/final pairings only exist inside each simulated branch, so they use Elo until the real bracket resolves them — at which point the next matchday update generates XGBoost predictions for the newly known matchups. Every simulation decision is attributed to its source; <span className="text-fg">Elo fallback is never presented as a model prediction</span>.</p>
        </section>
      </div>
    </>
  );
}

function Head({ icon, kicker, title, sub }: { icon: React.ReactNode; kicker: string; title: string; sub?: string }) {
  return (
    <div className="mb-6 max-w-3xl">
      <span className="kicker inline-flex items-center gap-2"><span className="text-cyan">{icon}</span>{kicker}</span>
      <h2 className="display mt-2 text-2xl md:text-3xl text-fg">{title}</h2>
      {sub && <p className="mt-2 text-sm text-fg2">{sub}</p>}
    </div>
  );
}
