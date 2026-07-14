"use client";

import { useMemo, useState } from "react";
import CountryFlag from "@/components/CountryFlag";
import { Calendar, Check, Lock, Route, Shield, Signal, Trophy } from "@/components/icons";
import { selectHistorySnapshot } from "../lib/history";
import type {
  HistoryMatchPrediction,
  HistoryProbability,
  PredictionHistoryDataset,
  PredictionHistorySnapshot,
} from "../types";

const pct = (value: number | null | undefined, digits = 1) =>
  value === null || value === undefined ? "Unavailable" : `${(value * 100).toFixed(digits)}%`;

const phaseLabel = (value: string) =>
  value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

const dateLabel = (value: string) =>
  new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(
    new Date(`${value}T12:00:00Z`),
  );

const fullDateLabel = (value: string) =>
  new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(`${value}T12:00:00Z`),
  );

const timestampLabel = (value: string) =>
  new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/Chicago",
    timeZoneName: "short",
  }).format(new Date(value));

const kickoffLabel = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        timeZone: "America/Chicago",
        timeZoneName: "short",
      }).format(new Date(value))
    : "Kickoff unavailable";

export default function PredictionHistory({ data }: { data: PredictionHistoryDataset }) {
  const [selectedId, setSelectedId] = useState(data.latestSnapshotId);
  const selection = useMemo(() => selectHistorySnapshot(data, selectedId), [data, selectedId]);

  if (data.status === "empty" || !selection.selected) {
    return (
      <PageHeader>
        <div className="card p-7" role="status">
          <h2 className="font-display text-xl font-semibold text-fg">Prediction history is not available yet</h2>
          <p className="mt-2 max-w-2xl text-sm text-fg2">The website remains fully available. Forecast snapshots will appear here after a meaningful archived production update exists.</p>
        </div>
      </PageHeader>
    );
  }

  const { selected, previous, isLatest } = selection;

  return (
    <PageHeader>
      <section aria-labelledby="history-dates-title">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <span className="kicker inline-flex items-center gap-2"><Calendar width={14} height={14} className="text-cyan" /> Forecast archive</span>
            <h2 id="history-dates-title" className="display mt-2 text-2xl text-fg">Choose an update</h2>
          </div>
          <span className="chip">{data.snapshots.length} genuine forecast states</span>
        </div>
        <div className="history-date-strip mt-4" role="tablist" aria-label="Prediction history dates">
          {data.dateOptions.map((option) => {
            const active = option.snapshotId === selected.snapshot_id;
            return (
              <button
                key={option.snapshotId}
                type="button"
                role="tab"
                aria-selected={active}
                className={`history-date-btn ${active ? "is-active" : ""}`}
                onClick={() => setSelectedId(option.snapshotId)}
              >
                <span>{dateLabel(option.displayDate)}</span>
                <small>{option.displayDate.slice(0, 4)}</small>
              </button>
            );
          })}
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-3" aria-label="Prediction history summary">
        <SummaryCard
          icon={<Signal width={17} height={17} />}
          label="Historical matchday record"
          value={`${data.accuracy.correct} of ${data.accuracy.resolved}`}
          hint="resolved archived predictions correct"
          accent="var(--pitch)"
        />
        <SummaryCard
          icon={<Trophy width={17} height={17} />}
          label="Latest archived leader"
          value={data.snapshots.at(-1)?.main_forecast.most_likely_champion?.team ?? "Unavailable"}
          hint={pct(data.snapshots.at(-1)?.main_forecast.most_likely_champion?.probability)}
          accent="var(--gold-c)"
        />
        <SummaryCard
          icon={<Lock width={17} height={17} />}
          label="Frozen forecast states"
          value={data.snapshots.length.toString()}
          hint={`${data.accuracy.pending} archived predictions still pending`}
          accent="var(--cyan)"
        />
      </section>

      <section className="history-truth-grid" aria-label="Facts and forecast labels">
        <TruthCard label="Confirmed Result" color="var(--pitch)" detail="A completed score and winner joined from the published bracket." />
        <TruthCard label="Historical Prediction" color="var(--gold-c)" detail="The frozen probability recorded before that match was played." />
        <TruthCard label="Current Prediction" color="var(--cyan)" detail="The newest archived forecast for matches that remain unresolved." />
      </section>

      {data.skippedSnapshots > 0 && (
        <div className="card border-amber/30 p-4 text-sm text-fg2" role="status">
          {data.skippedSnapshots} malformed or unavailable snapshot file{data.skippedSnapshots === 1 ? " was" : "s were"} skipped safely.
        </div>
      )}

      <div className="grid gap-14">
        <UpdatePanel
          title="Current Update"
          snapshot={selected}
          teamCodes={data.teamCodes}
          predictionLabel={isLatest ? "Current Prediction" : "Historical Prediction"}
          prominent
        />
        {previous ? (
          <UpdatePanel
            title="Previous Matchday Update"
            snapshot={previous}
            teamCodes={data.teamCodes}
            predictionLabel="Historical Prediction"
          />
        ) : (
          <section className="card p-6">
            <h2 className="font-display text-xl font-semibold text-fg">Previous Matchday Update</h2>
            <p className="mt-2 text-sm text-fg2">This is the first archived forecast, so no earlier meaningful update is available.</p>
          </section>
        )}
      </div>

      <section aria-labelledby="history-method-title">
        <SectionHeading icon={<Shield width={15} height={15} />} kicker="Provenance and integrity" title="An audit trail, not a reconstruction" id="history-method-title" />
        <div className="grid gap-3 md:grid-cols-3">
          <MethodCard title="Genuine archived values" detail="Every probability comes directly from the immutable snapshot selected above. Old forecasts are never rerun with today's model." />
          <MethodCard title="Results joined separately" detail="Completed scores and winners are matched from the current published bracket without changing any archived probability." />
          <MethodCard title="Automatic matchday flow" detail="Meaningful refreshes archive state changes; committed snapshots are read at the next static website build with no manual page edits." />
        </div>
      </section>
    </PageHeader>
  );
}

function PageHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      <div className="bg-floodlight bg-grid absolute inset-x-0 top-0 h-96 opacity-70" aria-hidden />
      <header className="relative border-b border-line/60">
        <div className="mx-auto max-w-[78rem] px-4 pb-11 pt-14">
          <span className="kicker inline-flex items-center gap-2"><Route width={14} height={14} className="text-gold" /> Forecast accountability</span>
          <h1 className="display mt-3 text-4xl text-fg md:text-5xl">Prediction History</h1>
          <p className="mt-3 max-w-3xl text-fg2">See what the model predicted before each tournament update, which teams it expected to advance, and how the championship forecast changed as confirmed results came in.</p>
          <div className="mt-5 flex flex-wrap gap-2">
            <span className="chip !border-pitch/35 !text-pitch"><Check width={13} height={13} /> Genuine archived forecasts</span>
            <span className="chip">Frozen probabilities</span>
            <span className="chip">No model reruns</span>
          </div>
        </div>
      </header>
      <main className="relative mx-auto max-w-[78rem] space-y-11 px-4 py-10">{children}</main>
    </div>
  );
}

function UpdatePanel({ title, snapshot, teamCodes, predictionLabel, prominent = false }: {
  title: string;
  snapshot: PredictionHistorySnapshot;
  teamCodes: Record<string, string | null>;
  predictionLabel: "Current Prediction" | "Historical Prediction";
  prominent?: boolean;
}) {
  const forecast = snapshot.main_forecast;
  const champion = forecast.most_likely_champion;
  const final = forecast.most_likely_final;
  const provenance = snapshot.record_class === "genuine_archived_forecast"
    ? "Genuine archived forecast"
    : "Recovered from historical committed output";

  return (
    <section className={`history-update ${prominent ? "is-current" : ""}`} aria-labelledby={`${snapshot.snapshot_id}-title`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <span className={`history-update-label ${prominent ? "current" : "previous"}`}>{title}</span>
          <h2 id={`${snapshot.snapshot_id}-title`} className="display mt-2 text-2xl text-fg">{fullDateLabel(snapshot.display_date)}</h2>
          <p className="mt-1 text-sm text-fg2">Generated {timestampLabel(snapshot.generated_at)}</p>
        </div>
        <span className="history-provenance" title={provenance}>{provenance}</span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <span className="chip">Phase: {phaseLabel(snapshot.tournament_phase)}</span>
        <span className="chip">{snapshot.completed_matches ?? "Unknown"} completed</span>
        <span className="chip">{(snapshot.simulation_count ?? 0).toLocaleString()} simulations</span>
        {snapshot.source_quality_score !== null && <span className="chip">Source quality: {snapshot.source_quality_score}</span>}
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="history-headline-card">
          <span>Most likely champion</span>
          <div className="mt-3 flex items-center gap-2">
            {champion?.team && <CountryFlag code={teamCodes[champion.team]} country={champion.team} size="lg" />}
            <strong>{champion?.team ?? "Unavailable"}</strong>
            <b>{pct(champion?.probability)}</b>
          </div>
          {forecast.second_most_likely_champion && (
            <small>Next: {forecast.second_most_likely_champion.team} at {pct(forecast.second_most_likely_champion.probability)}</small>
          )}
        </div>
        <div className="history-headline-card">
          <span>Projected final</span>
          <strong className="mt-3 block !text-lg">{final ? `${final.team_1} vs ${final.team_2}` : "Unavailable"}</strong>
          <b className="mt-1 block">{final ? pct(final.probability) : ""}</b>
          <small>Most likely final pairing at this update</small>
        </div>
      </div>

      <div className="mt-6 grid gap-5 md:grid-cols-2">
        <ProbabilityList title="Champion probabilities" entries={forecast.champion_probabilities} teamCodes={teamCodes} color="var(--gold-c)" />
        <ProbabilityList title="Finalist probabilities" entries={forecast.finalist_probabilities} teamCodes={teamCodes} color="var(--cyan)" />
      </div>

      <div className="mt-7">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-display text-base font-semibold text-fg">Matchday predictions</h3>
          <span className="text-xs text-fg3">{snapshot.matchday_predictions.length} archived</span>
        </div>
        {snapshot.matchday_predictions.length ? (
          <div className="mt-3 grid gap-3">
            {snapshot.matchday_predictions.map((match) => (
              <MatchCard key={`${snapshot.snapshot_id}-${match.match_id}`} match={match} teamCodes={teamCodes} predictionLabel={predictionLabel} />
            ))}
          </div>
        ) : (
          <div className="card mt-3 p-4 text-sm text-fg2">No upcoming-match prediction was pending in this archived state.</div>
        )}
      </div>
    </section>
  );
}

function ProbabilityList({ title, entries, teamCodes, color }: {
  title: string;
  entries: HistoryProbability[];
  teamCodes: Record<string, string | null>;
  color: string;
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase text-fg3">{title}</h3>
      {entries.length ? (
        <div className="mt-3 space-y-3">
          {entries.map((entry) => (
            <div key={entry.team}>
              <div className="flex items-center gap-2 text-sm">
                <CountryFlag code={teamCodes[entry.team]} country={entry.team} size="sm" />
                <span className="font-medium text-fg">{entry.team}</span>
                <strong className="stat-num ml-auto text-fg2">{pct(entry.probability)}</strong>
              </div>
              <div className="history-prob-track mt-1.5" role="meter" aria-label={`${entry.team} ${title.toLowerCase()} ${pct(entry.probability)}`} aria-valuenow={entry.probability * 100} aria-valuemin={0} aria-valuemax={100}>
                <span style={{ width: `${Math.max(0, Math.min(1, entry.probability)) * 100}%`, background: color }} />
              </div>
            </div>
          ))}
        </div>
      ) : <p className="mt-3 text-sm text-fg3">Unavailable in this snapshot.</p>}
    </div>
  );
}

function MatchCard({ match, teamCodes, predictionLabel }: {
  match: HistoryMatchPrediction;
  teamCodes: Record<string, string | null>;
  predictionLabel: "Current Prediction" | "Historical Prediction";
}) {
  const outcome = match.prediction_outcome;
  return (
    <article className="history-match-card">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <span className="kicker">{match.stage}</span>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-fg3"><Calendar width={12} height={12} /> {kickoffLabel(match.scheduled_at)}</p>
        </div>
        <span className={`history-prediction-kind ${predictionLabel === "Current Prediction" ? "current" : "historical"}`}>{predictionLabel}</span>
      </div>

      <div className="mt-4 space-y-3">
        <MatchTeam team={match.team_a} probability={match.team_a_win_probability} winner={match.predicted_winner === match.team_a} code={teamCodes[match.team_a]} />
        <MatchTeam team={match.team_b} probability={match.team_b_win_probability} winner={match.predicted_winner === match.team_b} code={teamCodes[match.team_b]} />
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3 text-xs">
        <span className="text-fg3">Predicted winner</span>
        <strong className="text-gold">{match.predicted_winner ?? "Unavailable"}</strong>
        <span className="history-method">{match.prediction_method}</span>
      </div>

      <div className={`history-result ${outcome}`}>
        {match.actual_winner ? (
          <>
            <span><b>Confirmed Result</b>: {match.actual_winner} won{match.actual_score ? ` ${match.actual_score}` : ""}</span>
            <strong>{outcome === "correct" ? "Correct" : "Incorrect"}</strong>
          </>
        ) : (
          <><span>Confirmed result pending</span><strong>Pending</strong></>
        )}
      </div>
    </article>
  );
}

function MatchTeam({ team, probability, winner, code }: {
  team: string;
  probability: number;
  winner: boolean;
  code: string | null | undefined;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm">
        <CountryFlag code={code} country={team} size="sm" />
        <span className={winner ? "font-semibold text-fg" : "text-fg2"}>{team}</span>
        {winner && <span className="text-[0.62rem] uppercase text-gold">model pick</span>}
        <strong className={`stat-num ml-auto ${winner ? "text-gold" : "text-fg2"}`}>{pct(probability)}</strong>
      </div>
      <div className="history-prob-track mt-1.5"><span style={{ width: `${probability * 100}%`, background: winner ? "var(--gold-c)" : "var(--line-strong)" }} /></div>
    </div>
  );
}

function SummaryCard({ icon, label, value, hint, accent }: { icon: React.ReactNode; label: string; value: string; hint: string; accent: string }) {
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 text-fg3"><span style={{ color: accent }}>{icon}</span><span className="text-[0.68rem] uppercase">{label}</span></div>
      <div className="stat-num mt-2 text-2xl text-fg">{value}</div>
      <p className="mt-1 text-xs text-fg3">{hint}</p>
    </div>
  );
}

function TruthCard({ label, color, detail }: { label: string; color: string; detail: string }) {
  return <div className="history-truth-card" style={{ ["--truth" as string]: color }}><strong>{label}</strong><p>{detail}</p></div>;
}

function SectionHeading({ icon, kicker, title, id }: { icon: React.ReactNode; kicker: string; title: string; id: string }) {
  return <div className="mb-5"><span className="kicker inline-flex items-center gap-2"><span className="text-cyan">{icon}</span>{kicker}</span><h2 id={id} className="display mt-2 text-2xl text-fg">{title}</h2></div>;
}

function MethodCard({ title, detail }: { title: string; detail: string }) {
  return <div className="card p-5"><h3 className="font-display text-sm font-semibold text-fg">{title}</h3><p className="mt-2 text-xs leading-5 text-fg3">{detail}</p></div>;
}
