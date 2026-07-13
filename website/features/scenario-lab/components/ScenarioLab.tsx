"use client";

import { useMemo, useState } from "react";
import CountryFlag from "@/components/CountryFlag";
import { Bolt, Calendar, Chart, Check, Lab, Lock, Route, Shield, Sim, Trophy } from "@/components/icons";
import { createDefaultScenarioState, simulateScenario } from "../lib/simulation";
import type {
  ScenarioChoice,
  ScenarioSettings,
  ScenarioSimulationResult,
  ScenarioSnapshot,
  TeamProbabilityResult,
} from "../types";

const SIMULATION_COUNTS = [1000, 5000, 10000] as const;
const pct = (value: number, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const prettyPhase = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const formatDate = (value: string | null) => {
  if (!value) return "Date to be confirmed";
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(value));
};

const formatTimestamp = (value: string | null) => {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
};

export default function ScenarioLab({ snapshot }: { snapshot: ScenarioSnapshot }) {
  const initial = useMemo(() => createDefaultScenarioState(snapshot), [snapshot]);
  const [settings, setSettings] = useState<ScenarioSettings>(initial.settings);
  const [result, setResult] = useState<ScenarioSimulationResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(snapshot.error);
  const [runTimestamp, setRunTimestamp] = useState<string | null>(null);

  const unresolvedMatches = useMemo(
    () => snapshot.rounds
      .flatMap((round) => round.matches)
      .filter((match) => snapshot.knownUnresolvedMatchIds.includes(match.id)),
    [snapshot],
  );
  const codeFor = (team: string) => snapshot.teams[team]?.code ?? null;

  function setChoice(matchId: string, choice: ScenarioChoice) {
    setSettings((current) => ({ ...current, choices: { ...current.choices, [matchId]: choice } }));
  }

  function runSimulation() {
    setRunning(true);
    setError(null);
    window.setTimeout(() => {
      try {
        setResult(simulateScenario(snapshot, settings));
        setRunTimestamp(new Date().toISOString());
      } catch (caught) {
        setResult(null);
        setError(caught instanceof Error ? caught.message : "The scenario could not be simulated.");
      } finally {
        setRunning(false);
      }
    }, 24);
  }

  function resetScenario() {
    const reset = createDefaultScenarioState(snapshot);
    setSettings(reset.settings);
    setResult(null);
    setRunTimestamp(null);
    setError(snapshot.error);
  }

  if (snapshot.status === "invalid") {
    return (
      <PageShell snapshot={snapshot}>
        <div className="card border-crimson/40 p-6" role="alert">
          <h2 className="font-display text-xl font-semibold text-fg">Scenario data unavailable</h2>
          <p className="mt-2 text-sm text-fg2">{snapshot.error}</p>
          <p className="mt-3 text-xs text-fg3">The official website remains available. No fallback results have been invented.</p>
        </div>
      </PageShell>
    );
  }

  if (snapshot.status === "complete") {
    return (
      <PageShell snapshot={snapshot}>
        <div className="card-feature p-7 text-center">
          <Trophy width={34} height={34} className="mx-auto text-gold" />
          <h2 className="display mt-3 text-2xl text-fg">The tournament is complete</h2>
          <p className="mx-auto mt-2 max-w-xl text-sm text-fg2">There are no unresolved matches left to simulate. The official completed-tournament record remains available across the website.</p>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell snapshot={snapshot}>
      <section className="scenario-notice" aria-labelledby="scenario-notice-title">
        <div className="flex items-start gap-3">
          <Shield width={21} height={21} className="mt-0.5 shrink-0 text-gold" />
          <div>
            <h2 id="scenario-notice-title" className="font-display text-sm font-semibold text-fg">Hypothetical and isolated</h2>
            <p className="mt-1 text-sm text-fg2">Scenario Lab results do not modify or replace the official live forecast. Forced outcomes and selected settings exist only in this browser session; nothing is saved or sent back.</p>
          </div>
        </div>
      </section>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,.85fr)]">
        <section aria-labelledby="match-controls-title">
          <SectionHead icon={<Route width={15} height={15} />} kicker="Scenario controls" title="Choose the road forward" id="match-controls-title" />
          <div className="space-y-4">
            {unresolvedMatches.map((match) => {
              const selected = settings.choices[match.id] ?? "model";
              return (
                <fieldset key={match.id} className="card scenario-match p-5" disabled={running}>
                  <legend className="sr-only">{match.teamA} versus {match.teamB}</legend>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <span className="kicker">{match.stage}</span>
                      <div className="mt-2 flex flex-wrap items-center gap-2 font-display text-lg font-semibold text-fg">
                        <TeamName team={match.teamA as string} code={codeFor(match.teamA as string)} />
                        <span className="text-xs font-normal uppercase text-fg3">vs</span>
                        <TeamName team={match.teamB as string} code={codeFor(match.teamB as string)} />
                      </div>
                    </div>
                    <span className="chip"><Calendar width={13} height={13} /> {formatDate(match.date)}</span>
                  </div>

                  {match.teamAAdvanceProbability !== null && match.teamBAdvanceProbability !== null && (
                    <div className="mt-4 grid grid-cols-2 gap-2 rounded-lg border border-line bg-bg/40 p-3 text-sm">
                      <div><span className="text-fg3">{match.teamA}</span><strong className="stat-num ml-2 text-cyan">{pct(match.teamAAdvanceProbability)}</strong></div>
                      <div className="text-right"><span className="text-fg3">{match.teamB}</span><strong className="stat-num ml-2 text-cyan">{pct(match.teamBAdvanceProbability)}</strong></div>
                      <div className="col-span-2 text-xs text-fg3">Published matchup probability: {match.probabilitySource}</div>
                    </div>
                  )}

                  <div className="mt-4 grid gap-2 sm:grid-cols-3" role="radiogroup" aria-label={`Outcome for ${match.teamA} versus ${match.teamB}`}>
                    <ChoiceCard matchId={match.id} value="model" selected={selected} onChange={setChoice} title="Model decides" detail="Sample published odds" />
                    <ChoiceCard matchId={match.id} value="team_a" selected={selected} onChange={setChoice} title={`${match.teamA} advances`} detail="Force this outcome" />
                    <ChoiceCard matchId={match.id} value="team_b" selected={selected} onChange={setChoice} title={`${match.teamB} advances`} detail="Force this outcome" />
                  </div>
                </fieldset>
              );
            })}
          </div>
        </section>

        <aside aria-labelledby="simulation-settings-title">
          <SectionHead icon={<Sim width={15} height={15} />} kicker="Simulation settings" title="Configure the run" id="simulation-settings-title" />
          <div className="card-elev sticky top-24 p-5">
            <fieldset disabled={running}>
              <legend className="text-xs font-semibold uppercase text-fg3">Simulation count</legend>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {SIMULATION_COUNTS.map((count) => (
                  <label key={count} className="scenario-count">
                    <input type="radio" name="simulation-count" value={count} checked={settings.simulations === count} onChange={() => setSettings((current) => ({ ...current, simulations: count }))} />
                    <span>{count.toLocaleString()}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="mt-5 block text-xs font-semibold uppercase text-fg3" htmlFor="scenario-seed">Random seed</label>
            <input id="scenario-seed" className="scenario-input mt-2" type="number" min={1} max={4294967295} step={1} value={settings.seed} disabled={running} onChange={(event) => setSettings((current) => ({ ...current, seed: Number(event.target.value) }))} aria-describedby="seed-help" />
            <p id="seed-help" className="mt-2 text-xs text-fg3">The same snapshot, choices, count, and seed reproduce the same probabilities.</p>

            <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              <button type="button" className="btn btn-gold justify-center" onClick={runSimulation} disabled={running}>
                {running ? <><span className="scenario-spinner" aria-hidden /> Running...</> : <><Bolt width={16} height={16} /> Run simulation</>}
              </button>
              <button type="button" className="btn btn-ghost justify-center" onClick={resetScenario} disabled={running}>Reset scenario</button>
            </div>

            <div className="mt-5 border-t border-line pt-4 text-xs text-fg3">
              <div className="flex justify-between gap-4"><span>Forced outcomes</span><strong className="text-fg">{Object.values(settings.choices).filter((choice) => choice !== "model").length}</strong></div>
              <div className="mt-2 flex justify-between gap-4"><span>Completed matches</span><strong className="text-fg">Locked</strong></div>
              <div className="mt-2 flex justify-between gap-4"><span>Storage</span><strong className="text-fg">Browser session only</strong></div>
            </div>
          </div>
        </aside>
      </div>

      <div aria-live="polite" aria-busy={running}>
        {error && <div className="card mt-8 border-crimson/40 p-5 text-sm text-fg2" role="alert">{error}</div>}
        {running && <div className="card mt-8 p-8 text-center"><span className="scenario-spinner mx-auto" aria-hidden /><p className="mt-3 text-sm text-fg2">Simulating the remaining bracket...</p></div>}
        {!running && result && <ScenarioResults snapshot={snapshot} result={result} runTimestamp={runTimestamp} codeFor={codeFor} />}
        {!running && !result && !error && (
          <div className="card-glass mt-8 p-7 text-center">
            <Lab width={28} height={28} className="mx-auto text-cyan" />
            <h2 className="mt-3 font-display text-lg font-semibold text-fg">Your scenario is ready</h2>
            <p className="mt-1 text-sm text-fg2">Choose any forced outcomes, keep the rest model-decided, and run the browser simulation.</p>
          </div>
        )}
      </div>

      <section className="mt-12" aria-labelledby="methodology-title">
        <SectionHead icon={<Shield width={15} height={15} />} kicker="Methodology" title="What this simulation does" id="methodology-title" />
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {[
            [<Lock key="lock" width={17} height={17} />, "Locks completed matches", "Real completed results are never replayed or changed."],
            [<Bolt key="force" width={17} height={17} />, "Applies your choices", "Forced winners advance only inside this browser scenario."],
            [<Chart key="chart" width={17} height={17} />, "Uses honest probabilities", "Known matchups use published model odds. Hypothetical finals use published tournament-form statistics, clearly labeled."],
            [<Shield key="shield" width={17} height={17} />, "Changes nothing official", "No API calls, writes, retraining, publishing, or permanent storage."],
          ].map(([icon, title, detail]) => (
            <div key={title as string} className="card p-4">
              <span className="text-cyan">{icon}</span>
              <h3 className="mt-2 font-display text-sm font-semibold text-fg">{title as string}</h3>
              <p className="mt-1 text-xs leading-5 text-fg3">{detail as string}</p>
            </div>
          ))}
        </div>
      </section>
    </PageShell>
  );
}

function PageShell({ snapshot, children }: { snapshot: ScenarioSnapshot; children: React.ReactNode }) {
  return (
    <div className="relative">
      <div className="bg-floodlight bg-grid absolute inset-x-0 top-0 h-80 opacity-70" aria-hidden />
      <header className="relative border-b border-line/60">
        <div className="mx-auto max-w-[78rem] px-4 pb-10 pt-14">
          <span className="kicker inline-flex items-center gap-2"><Lab width={14} height={14} className="text-gold" /> Interactive analytics</span>
          <h1 className="display mt-3 text-4xl text-fg md:text-5xl">Scenario Lab</h1>
          <p className="mt-3 max-w-2xl text-fg2">Change match assumptions, simulate the remaining tournament, and see how the road to the championship changes.</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <span className="chip !border-cyan/40 !text-cyan"><Check width={13} height={13} /> Official: {snapshot.officialLabel}</span>
            <span className="chip !border-gold/40 !text-gold">Scenario: browser generated</span>
            <span className="chip">Phase: {prettyPhase(snapshot.currentPhase)}</span>
          </div>
        </div>
      </header>
      <main className="relative mx-auto max-w-[78rem] space-y-10 px-4 py-10">{children}</main>
    </div>
  );
}

function ChoiceCard({ matchId, value, selected, onChange, title, detail }: {
  matchId: string;
  value: ScenarioChoice;
  selected: ScenarioChoice;
  onChange: (matchId: string, value: ScenarioChoice) => void;
  title: string;
  detail: string;
}) {
  return (
    <label className="scenario-choice">
      <input type="radio" name={`choice-${matchId}`} value={value} checked={selected === value} onChange={() => onChange(matchId, value)} />
      <span><strong>{title}</strong><small>{detail}</small></span>
    </label>
  );
}

function TeamName({ team, code }: { team: string; code: string | null }) {
  return <span className="inline-flex items-center gap-2"><CountryFlag code={code} country={team} size="md" />{team}</span>;
}

function SectionHead({ icon, kicker, title, id }: { icon: React.ReactNode; kicker: string; title: string; id: string }) {
  return <div className="mb-5"><span className="kicker inline-flex items-center gap-2"><span className="text-cyan">{icon}</span>{kicker}</span><h2 id={id} className="display mt-2 text-2xl text-fg">{title}</h2></div>;
}

function ScenarioResults({ snapshot, result, runTimestamp, codeFor }: {
  snapshot: ScenarioSnapshot;
  result: ScenarioSimulationResult;
  runTimestamp: string | null;
  codeFor: (team: string) => string | null;
}) {
  const champion = result.championProbabilities[0];
  const finalPair = result.finalPairProbabilities[0];
  const officialMap = new Map(snapshot.officialProbabilities.map((entry) => [entry.team, entry]));
  const championRows = result.championProbabilities.map((entry) => ({ ...entry, official: officialMap.get(entry.team)?.championProbability ?? 0 }));
  const finalistRows = result.finalistProbabilities.map((entry) => ({ ...entry, official: officialMap.get(entry.team)?.finalistProbability ?? 0 }));

  return (
    <section className="mt-12 space-y-10" aria-labelledby="scenario-results-title">
      <div>
        <span className="kicker inline-flex items-center gap-2 text-gold"><Trophy width={15} height={15} /> Scenario result</span>
        <h2 id="scenario-results-title" className="display mt-2 text-3xl text-fg">How your bracket changes</h2>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ResultCard label="Most likely champion" value={<TeamName team={champion.team} code={codeFor(champion.team)} />} hint={pct(champion.probability)} />
        <ResultCard label="Most likely final" value={`${finalPair.teamA} vs ${finalPair.teamB}`} hint={pct(finalPair.probability)} />
        <ResultCard label="Forced outcomes" value={result.forcedOutcomeCount.toString()} hint={`${result.simulations.toLocaleString()} simulations`} />
        <ResultCard label="Random seed" value={result.seed.toString()} hint="Reproducible run" />
      </div>

      <ComparisonSection title="Champion probability comparison" rows={championRows} codeFor={codeFor} />
      <ComparisonSection title="Finalist probability comparison" rows={finalistRows} codeFor={codeFor} />

      <section aria-labelledby="likely-finals-title">
        <SectionHead icon={<Route width={15} height={15} />} kicker="Scenario pairings" title="Most likely finals" id="likely-finals-title" />
        <div className="grid gap-3 md:grid-cols-2">
          {result.finalPairProbabilities.slice(0, 6).map((pair, index) => (
            <div key={`${pair.teamA}-${pair.teamB}`} className="card flex items-center justify-between gap-4 p-4">
              <div className="flex min-w-0 items-center gap-3">
                <span className="stat-num text-sm text-fg3">{String(index + 1).padStart(2, "0")}</span>
                <div className="min-w-0 font-display text-sm font-semibold text-fg">
                  <TeamName team={pair.teamA} code={codeFor(pair.teamA)} />
                  <span className="mx-2 text-xs font-normal text-fg3">vs</span>
                  <TeamName team={pair.teamB} code={codeFor(pair.teamB)} />
                </div>
              </div>
              <strong className="stat-num shrink-0 text-gold">{pct(pair.probability)}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="card-glass grid gap-4 p-5 text-xs text-fg3 sm:grid-cols-2 lg:grid-cols-4">
        <Meta label="Official forecast timestamp" value={formatTimestamp(snapshot.generatedAt)} />
        <Meta label="Scenario run timestamp" value={formatTimestamp(runTimestamp)} />
        <Meta label="Data snapshot" value={snapshot.snapshotId} />
        <Meta label="Probability decisions" value={`${result.probabilitySourceCounts.published_matchup.toLocaleString()} published matchup / ${result.probabilitySourceCounts.published_tournament_form.toLocaleString()} tournament form`} />
      </div>
    </section>
  );
}

function ResultCard({ label, value, hint }: { label: string; value: React.ReactNode; hint: string }) {
  return <div className="card-feature p-4"><span className="text-[0.68rem] uppercase text-fg3">{label}</span><div className="mt-2 font-display text-lg font-semibold text-fg">{value}</div><div className="stat-num mt-1 text-sm text-gold">{hint}</div></div>;
}

function ComparisonSection({ title, rows, codeFor }: {
  title: string;
  rows: Array<TeamProbabilityResult & { official: number }>;
  codeFor: (team: string) => string | null;
}) {
  const id = title.toLowerCase().replace(/\s+/g, "-");
  return (
    <section aria-labelledby={id}>
      <SectionHead icon={<Chart width={15} height={15} />} kicker="Official vs hypothetical" title={title} id={id} />
      <div className="card overflow-hidden">
        {rows.map((row) => {
          const delta = row.probability - row.official;
          return (
            <div key={row.team} className="scenario-comparison-row">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <TeamName team={row.team} code={codeFor(row.team)} />
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-cyan">Official {pct(row.official)}</span>
                  <span className="text-gold">Scenario {pct(row.probability)}</span>
                  <strong className={delta > 0.00005 ? "text-pitch" : delta < -0.00005 ? "text-crimson" : "text-fg3"}>
                    {delta > 0 ? "+" : ""}{(delta * 100).toFixed(1)} pp
                  </strong>
                </div>
              </div>
              <div className="mt-3 space-y-1.5" aria-label={`${row.team}: official ${pct(row.official)}, scenario ${pct(row.probability)}`}>
                <div className="scenario-bar"><span style={{ width: `${row.official * 100}%` }} className="scenario-bar-official" /></div>
                <div className="scenario-bar"><span style={{ width: `${row.probability * 100}%` }} className="scenario-bar-user" /></div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div><div className="uppercase text-fg3">{label}</div><div className="mt-1 break-words font-mono text-fg2">{value}</div></div>;
}
