import type { Metadata } from "next";
import Link from "next/link";
import { Kicker, Disclaimer } from "@/components/ui";
import {
  Globe, Network, Lock, Shield, Sim, Trophy, Arrow, Lab, Database, Chart,
  Gauge, Signal, Route, Bolt, Check,
} from "@/components/icons";

export const metadata: Metadata = {
  title: "About — FIFA 2026 Tournament Intelligence",
  description:
    "What this project is, the data and models behind it, how the forecast updated through the tournament, its limitations, and a plain-language FAQ. The completed archive records Spain as FIFA World Cup 2026 champions. Independent football analytics — not affiliated with FIFA.",
};

const DATA_SOURCES = [
  {
    icon: <Database width={18} height={18} />, accent: "var(--cyan)",
    title: "~50,000 historical matches", role: "Model training",
    body: "International football results spanning 1872–2026, used to train the predictive model. Every feature is built from information available before a match — never the result.",
  },
  {
    icon: <Signal width={18} height={18} />, accent: "var(--pitch)",
    title: "football-data.org", role: "Primary live truth",
    body: "The authoritative source of live tournament state: fixtures, completed results, standings, the knockout bracket, and tournament progression. This is what defines reality in the forecast.",
  },
  {
    icon: <Globe width={18} height={18} />, accent: "var(--gold-c)",
    title: "Zafronix", role: "Secondary enrichment",
    body: "Historical World Cup, squad, and descriptive enrichment (23 tournaments). Evaluated as an experimental challenger — it does not currently power production predictions.",
  },
];

const FEATURES = [
  { icon: <Gauge width={17} height={17} />, t: "Elo-derived strength", d: "Pre-match Elo ratings and expected-score difference — long-run team quality." },
  { icon: <Bolt width={17} height={17} />, t: "Recent form", d: "Win / draw / loss form over the last 5 and 10 matches for each side." },
  { icon: <Chart width={17} height={17} />, t: "Goal-based form", d: "Goals scored & conceded, goal difference, and clean-sheet trends." },
  { icon: <Route width={17} height={17} />, t: "Head-to-head", d: "Recent meeting history between the two teams (last 10)." },
  { icon: <Trophy width={17} height={17} />, t: "Tournament context", d: "Match importance, stage, neutral venue, and competition type." },
];

const STEPS = [
  ["Train on history", "The model learns from ~50,000 historical international matches, using only pre-match information."],
  ["Estimate each match", "The production model outputs win / draw / loss probabilities for a given matchup."],
  ["Lock the real results", "Completed matches from football-data.org are locked as immutable tournament truth."],
  ["Predict what's next", "Newly resolved knockout matchups (both teams known) are predicted with the model."],
  ["Simulate the rest", "The remaining bracket is played out ~10,000 times via Monte Carlo simulation."],
  ["Read the odds", "Finalist and champion probabilities are counted across all those simulations."],
];

const MODELS = [
  {
    icon: <Network width={18} height={18} />, tag: "Production", accent: "var(--gold-c)",
    title: "XGBoost", body: "A gradient-boosted tree model — the current production predictor. Selected because it had the best overall accuracy and probability quality under the project's leakage-safe evaluation.",
    stats: [["Accuracy", "0.6075"], ["Macro F1", "0.4511"], ["Log loss", "0.8607"]],
  },
  {
    icon: <Chart width={18} height={18} />, tag: "Baseline", accent: "var(--cyan)",
    title: "Logistic Regression", body: "A simpler linear baseline kept for comparison. Useful as a sanity check, but weaker on overall accuracy and probability calibration than the production model.",
    stats: [["Accuracy", "0.5752"], ["Macro F1", "0.5273"], ["Role", "Comparison"]],
  },
  {
    icon: <Sim width={18} height={18} />, tag: "Simulation", accent: "var(--pitch)",
    title: "Monte Carlo", body: "Not a predictor in the same sense — a simulation layer that plays the remaining tournament thousands of times using match probabilities to estimate finalist and champion odds.",
    stats: [["Sims / forecast", "10,000"], ["Uses", "Match probs"], ["Output", "Tournament odds"]],
  },
];

const LIVE_UPDATES = [
  ["Completed matches are locked", "A finished result becomes immutable truth and is never re-simulated.", <Lock key="1" width={16} height={16} />, "var(--pitch)"],
  ["Eliminated teams are removed", "Knocked-out teams can no longer appear in any future simulation.", <Shield key="2" width={16} height={16} />, "var(--crimson)"],
  ["New matchups are predicted", "Each newly resolved knockout tie is scored by the production model.", <Network key="3" width={16} height={16} />, "var(--cyan)"],
  ["The bracket re-simulates", "The tournament is played out again from the actual current state.", <Sim key="4" width={16} height={16} />, "var(--gold-c)"],
];

const FAQS: [string, React.ReactNode][] = [
  ["What does Macro F1 mean, and why is it lower than accuracy?",
    "Accuracy is the share of matches whose most-likely outcome the model gets right (~61%). Macro F1 averages the model's skill on each outcome — win, draw, loss — equally. Draws are the minority result (~23%) and are rarely the single most-likely outcome, so the model seldom labels a match a draw even though it still assigns it a probability. That drags Macro F1 (0.45) below accuracy. The model stays well-calibrated (calibration error ≈ 0.005), and forcing it to call more draws actually lowered accuracy and calibration — so we kept the calibrated version."],
  ["Why does a team sometimes look better after one recent win?",
    "Form features look at the last 5–10 matches, so a recent result does nudge the estimate. But pre-match Elo — long-run team strength — carries far more weight, so a single win moves the needle only slightly rather than swinging the forecast."],
  ["Is recency bias affecting the model?",
    "Recent form is deliberately a short-window signal and is balanced against Elo and head-to-head history. It informs the forecast; it doesn't dominate it."],
  ["Why do finalist and champion probabilities change after each match?",
    "Because this was a live forecast, not a one-time prediction. Every completed result was locked, and the remaining bracket was simulated again from the real current state — so the odds moved as the tournament actually resolved. The archived final version records Spain as champion and preserves the model's 51.9% pre-final probability through Prediction History."],
  ["Why can a team look more likely to reach the final after a different team is eliminated?",
    "A team's path to the final runs through its own half of the bracket. When a strong rival on that side is knocked out, the simulated route gets easier, so that team's finalist probability rises even though it didn't play."],
  ["Does the model use the current team status?",
    "Yes. Completed results, eliminations, standings, and the bracket were sourced from football-data.org and reflected in every new forecast — through to the completed final."],
  ["Does it use player injuries, lineups, or tactics?",
    "No. The production model is team-level — Elo, form, goals, head-to-head, and tournament context. It does not model individual injuries, expected lineups, or tactical style. That's a stated limitation, not a hidden one."],
  ["What is Monte Carlo simulation?",
    "It's playing out the rest of the tournament many thousands of times using the match probabilities. A team's champion probability is simply how often it wins across all those simulated tournaments."],
  ["Why aren't the probabilities the same as guaranteed outcomes?",
    "They're forecasts of likelihood, not certainties. A 30% favourite is expected to lose about 70% of the time — an upset isn't the model being wrong, it's the 70% happening."],
  ["Why did the project keep XGBoost as the production model?",
    "Under a strict, leakage-safe evaluation it had the best combination of accuracy and probability quality. Tuned variants and enrichment-based challengers were tested and did not beat it by a statistically meaningful margin, so it was retained."],
  ["What role does Zafronix play?",
    "Zafronix is a secondary enrichment source (World Cup history and squads). Its features were engineered and tested as a challenger model; the challenger did not materially outperform the production model, so Zafronix does not power production predictions — it remains available for descriptive context."],
  ["Is this an official FIFA product?",
    "No. It's an independent football-analytics portfolio project, not affiliated with or endorsed by FIFA. Team flags are public-domain; all other imagery is original CSS/SVG artwork."],
];

function Plus() {
  return <svg className="q-ico" width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>;
}

function SecHead({ icon, kicker, title, sub }: { icon: React.ReactNode; kicker: string; title: string; sub?: string }) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-3">
        <span className="sec-ico text-cyan">{icon}</span>
        <span className="kicker">{kicker}</span>
      </div>
      <h2 className="display mt-3 text-2xl text-fg md:text-3xl">{title}</h2>
      {sub && <p className="mt-2 max-w-2xl text-fg2">{sub}</p>}
    </div>
  );
}

export default function AboutPage() {
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";

  return (
    <div className="mx-auto max-w-4xl px-4 pb-20">
      {/* ---------- HERO ---------- */}
      <header className="about-hero py-14 text-center md:py-20">
        <Kicker icon={<Globe width={14} height={14} />}>About the project</Kicker>
        <h1 className="display mx-auto mt-4 max-w-3xl text-4xl text-fg md:text-6xl">
          A live <span className="text-gold-grad">football intelligence</span> platform
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-fg2">
          An independent analytics project that forecast the likely finalists and champion of the FIFA World Cup 2026,
          updating as real matches were played. Not a one-time prediction: a live decision system.
        </p>
        <p className="mx-auto mt-5 max-w-2xl text-sm text-fg2">
          <span className="champion-chip"><Trophy width={13} height={13} aria-hidden /> Tournament complete</span>
          <span className="mt-2 block">
            The archived final version records <span className="text-fg">Spain</span> as FIFA World Cup 2026 champions
            and preserves the model&apos;s 51.9% pre-final probability through Prediction History.
          </span>
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          {["Live forecasting", "Machine learning", "Bracket-aware simulation", "Auditable & honest"].map((c) => (
            <span key={c} className="chip"><Check width={13} height={13} /> {c}</span>
          ))}
        </div>
      </header>

      {/* ---------- A · OVERVIEW ---------- */}
      <section className="mt-6">
        <SecHead icon={<Trophy width={18} height={18} />} kicker="Project overview" title="What this project is"
          sub="An end-to-end sports-analytics system: it ingested real results, engineered leakage-safe machine-learning features, predicted each resolved knockout matchup, and simulated the remaining tournament to estimate finalist and champion probabilities. The tournament is now complete — Spain are champions — and this archived version preserves the final state and the full prediction history." />
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            ["Live, not static", "Through the tournament, forecasts refreshed the moment a real match ended — the bracket rewrote itself and the odds moved with it."],
            ["Machine learning", "A trained XGBoost model estimates win / draw / loss probabilities for each matchup."],
            ["Bracket-aware simulation", "Monte Carlo plays out the rest of the tournament thousands of times to turn match odds into title odds."],
            ["Product thinking", "Data engineering, modeling, simulation, honest UX, and deployment — built as a portfolio-grade system."],
          ].map(([t, d]) => (
            <div key={t} className="card p-5">
              <div className="font-display font-semibold text-fg">{t}</div>
              <p className="mt-1.5 text-sm text-fg2">{d}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- B · WHY ---------- */}
      <section className="mt-12">
        <SecHead icon={<Bolt width={18} height={18} />} kicker="Why it was built" title="The question behind it" />
        <div className="card-elev p-6 md:p-7">
          <p className="text-fg2">
            It started from a simple question: <span className="text-fg">given where a tournament actually stands right now, can you estimate who is most likely to reach the final and lift the trophy?</span> The
            interesting part isn&apos;t a single pre-tournament guess — it&apos;s building a system that keeps answering that question honestly as reality unfolds, combining data analysis,
            modeling, simulation, and product engineering into one live decision tool.
          </p>
        </div>
      </section>

      {/* ---------- C · DATA SOURCES ---------- */}
      <section className="mt-12">
        <SecHead icon={<Database width={18} height={18} />} kicker="Data sources" title="Where the data comes from"
          sub="Three sources, each with a clear and separate job. Keeping them separate is deliberate: only one is allowed to define live tournament reality." />
        <div className="grid gap-3 md:grid-cols-3">
          {DATA_SOURCES.map((s) => (
            <div key={s.title} className="card card-hover p-5">
              <div className="flex items-center justify-between">
                <span className="sec-ico" style={{ color: s.accent }}>{s.icon}</span>
                <span className="chip" style={{ borderColor: s.accent, color: s.accent }}>{s.role}</span>
              </div>
              <div className="mt-3 font-display font-semibold text-fg">{s.title}</div>
              <p className="mt-1.5 text-sm text-fg2">{s.body}</p>
            </div>
          ))}
        </div>
        <div className="card rail mt-3 p-4" style={{ ["--accent" as string]: "var(--pitch)" }}>
          <div className="flex items-center gap-2 pl-2 text-pitch"><Lock width={16} height={16} /><span className="font-display text-sm font-semibold text-fg">What &ldquo;live tournament truth&rdquo; means</span></div>
          <p className="mt-1 pl-2 text-sm text-fg2">One provider — football-data.org — is the single source of what has actually happened. Enrichment sources can add historical context, but they can never overwrite a real result, a completed match, or the current bracket. That separation is what keeps the forecast trustworthy.</p>
        </div>
      </section>

      {/* ---------- D · FEATURES ---------- */}
      <section className="mt-12">
        <SecHead icon={<Gauge width={18} height={18} />} kicker="Model inputs" title="What the model looks at"
          sub="The production model uses a validated set of 25 team-level, pre-match features, grouped into five families. Only information available before kickoff is ever used." />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.t} className="card p-5">
              <span className="sec-ico text-cyan">{f.icon}</span>
              <div className="mt-3 font-display text-sm font-semibold text-fg">{f.t}</div>
              <p className="mt-1 text-sm text-fg2">{f.d}</p>
            </div>
          ))}
          <div className="card rail flex items-center p-5" style={{ ["--accent" as string]: "var(--gold-c)" }}>
            <p className="pl-2 text-sm text-fg2"><span className="font-display font-semibold text-fg">25 features · leakage-safe.</span> Rolling stats are shifted before each match so a result can never leak into its own prediction.</p>
          </div>
        </div>
      </section>

      {/* ---------- E · HOW IT WORKS ---------- */}
      <section className="mt-12">
        <SecHead icon={<Network width={18} height={18} />} kicker="How the model works" title="From history to a live forecast" />
        <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          <ol className="space-y-4">
            {STEPS.map(([t, d], i) => (
              <li key={t} className="step" data-n={i + 1}>
                <div className="font-display font-semibold text-fg">{t}</div>
                <p className="mt-0.5 text-sm text-fg2">{d}</p>
              </li>
            ))}
          </ol>
          <div className="card-feature h-fit p-6">
            <span className="kicker inline-flex items-center gap-2 text-gold"><Sim width={14} height={14} /> Monte Carlo, simply</span>
            <p className="mt-3 text-sm text-fg2">
              Imagine replaying the rest of the tournament <span className="text-fg">10,000 times</span>. In each replay, every remaining
              match is decided by its win / draw / loss probability, round after round, until someone lifts the trophy.
            </p>
            <p className="mt-3 text-sm text-fg2">
              A team&apos;s <span className="text-fg">champion probability</span> is just the share of those 10,000 replays it wins.
              Reach-the-final odds work the same way. More simulations means steadier, more reliable numbers.
            </p>
          </div>
        </div>
      </section>

      {/* ---------- F · MODELS ---------- */}
      <section className="mt-12">
        <SecHead icon={<Lab width={18} height={18} />} kicker="The models" title="What each model means"
          sub="Two predictive models and one simulation layer. Test metrics are from a chronological, leakage-safe hold-out set." />
        <div className="grid gap-3 md:grid-cols-3">
          {MODELS.map((m) => (
            <div key={m.title} className={`${m.tag === "Production" ? "card-feature" : "card"} p-5`}>
              <div className="flex items-center justify-between">
                <span className="sec-ico" style={{ color: m.accent }}>{m.icon}</span>
                <span className="chip" style={{ borderColor: m.accent, color: m.accent }}>{m.tag}</span>
              </div>
              <div className="mt-3 font-display text-lg font-semibold text-fg">{m.title}</div>
              <p className="mt-1.5 text-sm text-fg2">{m.body}</p>
              <div className="mt-4 space-y-1.5 border-t border-line pt-3">
                {m.stats.map(([k, v]) => (
                  <div key={k} className="flex justify-between text-sm"><span className="text-fg3">{k}</span><span className="stat-num text-fg">{v}</span></div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="card rail mt-3 p-4" style={{ ["--accent" as string]: "var(--cyan)" }}>
          <div className="flex items-center gap-2 pl-2 text-cyan"><Globe width={16} height={16} /><span className="font-display text-sm font-semibold text-fg">On the Zafronix challenger</span></div>
          <p className="mt-1 pl-2 text-sm text-fg2">World Cup pedigree and squad features from Zafronix were engineered and tested as a challenger. Its accuracy gain over the production model was not statistically meaningful (95% confidence interval on the difference spanned zero), so the production XGBoost was kept unchanged. Honest result: the challenger was evaluated and rejected, not quietly shipped.</p>
        </div>
      </section>

      {/* ---------- G · LIVE UPDATES ---------- */}
      <section className="mt-12">
        <SecHead icon={<Signal width={18} height={18} />} kicker="Live behaviour" title="How the forecast stays live"
          sub="This is the part that makes it a system rather than a spreadsheet. After every real match:" />
        <div className="grid gap-3 sm:grid-cols-2">
          {LIVE_UPDATES.map(([t, d, ic, ac]) => (
            <div key={t as string} className="card rail p-4" style={{ ["--accent" as string]: ac as string }}>
              <div className="flex items-center gap-2 pl-2" style={{ color: ac as string }}>{ic as React.ReactNode}<span className="font-display text-sm font-semibold text-fg">{t as string}</span></div>
              <p className="mt-1 pl-2 text-sm text-fg2">{d as string}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ---------- H · LIMITATIONS ---------- */}
      <section className="mt-12">
        <SecHead icon={<Shield width={18} height={18} />} kicker="Limitations" title="What it does not claim to do"
          sub="Stated plainly — because credible forecasting is honest about its edges." />
        <div className="card p-6">
          <ul className="space-y-3">
            {[
              "The production model is team-level, not full player-level tactical intelligence.",
              "It does not model individual injuries, expected lineups, or tactical style.",
              "Probabilities are forecasts, not guarantees — favourites lose all the time.",
              "The numbers move as new real results arrive; today's odds are not a fixed prediction.",
            ].map((t) => (
              <li key={t} className="flex items-start gap-2.5 text-sm text-fg2"><span className="mt-0.5 text-amber"><Shield width={15} height={15} /></span>{t}</li>
            ))}
          </ul>
        </div>
      </section>

      {/* ---------- I · FAQ ---------- */}
      <section className="mt-12">
        <SecHead icon={<Chart width={18} height={18} />} kicker="FAQ" title="Questions, answered plainly" />
        <div>
          {FAQS.map(([q, a]) => (
            <details className="faq" key={q}>
              <summary>{q}<Plus /></summary>
              <div className="faq-a">{a}</div>
            </details>
          ))}
        </div>
      </section>

      {/* ---------- CTA ---------- */}
      <section className="mt-12 flex flex-wrap gap-3">
        {dashboard && <a href={dashboard} target="_blank" rel="noreferrer" className="btn btn-primary">Open the Dashboard <Arrow width={16} height={16} /></a>}
        <Link href="/methodology" className="btn btn-ghost">Analytics Lab <Lab width={16} height={16} /></Link>
        {github && <a href={github} target="_blank" rel="noreferrer" className="btn btn-ghost">View Source Code</a>}
      </section>
      <Disclaimer className="mt-8" />
    </div>
  );
}
