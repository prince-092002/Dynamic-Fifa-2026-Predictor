import type { Bracket as BracketData, BracketMatch } from "@/lib/data";
import { formatPct } from "@/lib/data";
import SourceBadge, { SourceLegend } from "./SourceBadge";
import { Lock, Bolt } from "./icons";
import CountryFlag from "./CountryFlag";

function MatchCard({ match, isCurrent, teamCodes }: { match: BracketMatch; isCurrent: boolean; teamCodes: Record<string, string | null> }) {
  const completed = match.state === "completed";
  const known = match.state === "scheduled_known";
  return (
    <div className={`card w-60 shrink-0 p-3.5 text-sm ${isCurrent && !completed ? "border-cyan/50 shadow-[0_0_0_1px_rgba(56,189,248,0.25)]" : ""} ${completed ? "border-pitch/25" : ""}`}>
      <div className="mb-2 flex items-center justify-between text-[0.68rem] text-fg3">
        <span>{match.date ? match.date.slice(0, 10) : ""}</span>
        {completed ? <span className="inline-flex items-center gap-1 text-pitch"><Lock width={11} height={11} /> FINAL</span>
          : known ? <span className="inline-flex items-center gap-1 text-cyan"><Bolt width={11} height={11} /> LIVE FORECAST</span> : null}
      </div>

      {completed ? (
        <>
          <Row name={match.team_a} code={match.team_a ? teamCodes[match.team_a] : null} won={match.winner === match.team_a} />
          <Row name={match.team_b} code={match.team_b ? teamCodes[match.team_b] : null} won={match.winner === match.team_b} />
          <div className="mt-2 rounded-md bg-pitch/10 px-2 py-1 text-center">
            <span className="stat-num text-lg text-pitch">{match.score}</span>
          </div>
        </>
      ) : known ? (
        <>
          <Row name={match.team_a} code={match.team_a ? teamCodes[match.team_a] : null} prob={match.team_a_advance_probability} fav={match.predicted_favorite === match.team_a} />
          <Row name={match.team_b} code={match.team_b ? teamCodes[match.team_b] : null} prob={match.team_b_advance_probability} fav={match.predicted_favorite === match.team_b} />
        </>
      ) : (
        <p className="py-2 text-fg3 italic">Winners of earlier rounds</p>
      )}
      <div className="mt-2.5"><SourceBadge source={match.source} /></div>
    </div>
  );
}

function Row({ name, code, won, prob, fav }: { name: string | null; code?: string | null; won?: boolean; prob?: number | null; fav?: boolean }) {
  return (
    <div className={`flex items-center justify-between rounded-md px-1.5 py-1 ${won ? "bg-pitch/10" : ""}`}>
      <span className={`flex min-w-0 items-center gap-2 ${won || fav ? "font-semibold text-fg" : "text-fg2"}`}>
        {name && <CountryFlag code={code} country={name} size="sm" />}
        <span className="truncate">{name}</span>
      </span>
      {prob != null && <span className={`stat-num shrink-0 text-xs ${fav ? "text-cyan" : "text-fg3"}`}>{formatPct(prob, 0)}</span>}
      {won && <span className="ml-1 shrink-0 text-pitch">•</span>}
    </div>
  );
}

export default function Bracket({ bracket, teamCodes }: { bracket: BracketData; teamCodes: Record<string, string | null> }) {
  return (
    <div>
      <div className="mb-4"><SourceLegend /></div>
      <div className="-mx-4 flex gap-4 overflow-x-auto px-4 pb-3">
        {bracket.rounds.map((round) => {
          const isCurrent = round.stage.toLowerCase() === String(bracket.current_phase).replace(/_/g, " ").toLowerCase();
          return (
            <section key={round.stage} className="shrink-0" aria-label={round.stage}>
              <div className="mb-2 flex items-center gap-2">
                <h3 className={`font-display text-xs font-bold uppercase tracking-[0.15em] ${isCurrent ? "text-cyan" : "text-fg3"}`}>{round.stage}</h3>
                {isCurrent && <span className="chip !py-0.5 !px-2 !text-[0.62rem]">current</span>}
              </div>
              <div className="flex flex-col gap-3">
                {round.matches.map((m) => <MatchCard key={m.fixture_id} match={m} isCurrent={isCurrent} teamCodes={teamCodes} />)}
              </div>
            </section>
          );
        })}
      </div>
    </div>
  );
}
