import type { Bracket as BracketData, BracketMatch } from "@/lib/data";
import { formatPct } from "@/lib/data";
import SourceBadge, { SourceLegend } from "./SourceBadge";

function MatchCard({ match }: { match: BracketMatch }) {
  return (
    <div className="card w-56 shrink-0 p-3 text-sm">
      <p className="mb-1 text-xs text-fg2">{match.date ? match.date.slice(0, 10) : ""}</p>
      {match.state === "completed" ? (
        <>
          <p className={match.winner === match.team_a ? "font-bold text-fg" : "text-fg2"}>{match.team_a}</p>
          <p className={match.winner === match.team_b ? "font-bold text-fg" : "text-fg2"}>{match.team_b}</p>
          <p className="my-1 font-mono text-lg font-bold text-green">{match.score}</p>
          <p className="text-xs text-fg2">
            Winner: <span className="font-semibold text-fg">{match.winner}</span>
          </p>
        </>
      ) : match.state === "scheduled_known" ? (
        <>
          <div className="flex items-baseline justify-between">
            <p className="font-semibold">{match.team_a}</p>
            {match.team_a_advance_probability != null && <span className="font-mono text-xs text-cyan">{formatPct(match.team_a_advance_probability, 1)}</span>}
          </div>
          <div className="flex items-baseline justify-between">
            <p className="font-semibold">{match.team_b}</p>
            {match.team_b_advance_probability != null && <span className="font-mono text-xs text-cyan">{formatPct(match.team_b_advance_probability, 1)}</span>}
          </div>
          {match.predicted_favorite && (
            <p className="mt-1 text-xs text-fg2">
              Favorite: <span className="font-semibold text-fg">{match.predicted_favorite}</span>
            </p>
          )}
        </>
      ) : (
        <p className="italic text-fg2">Winners of earlier rounds</p>
      )}
      <div className="mt-2">
        <SourceBadge source={match.source} />
      </div>
    </div>
  );
}

export default function Bracket({ bracket }: { bracket: BracketData }) {
  return (
    <div>
      <div className="mb-4">
        <SourceLegend />
      </div>
      <div className="space-y-6">
        {bracket.rounds.map((round) => (
          <section key={round.stage} aria-label={round.stage}>
            <h3 className="mb-2 text-sm font-bold uppercase tracking-wider text-fg2">{round.stage}</h3>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {round.matches.map((match) => (
                <MatchCard key={match.fixture_id} match={match} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
