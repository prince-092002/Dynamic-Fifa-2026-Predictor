import Link from "next/link";
import { notFound } from "next/navigation";
import ProbBar from "@/components/ProbBar";
import { STATUS_LABELS, formatPct, getTeamStats, getTeams } from "@/lib/data";

export function generateStaticParams() {
  return (getTeams()?.teams ?? []).map((team) => ({ slug: team.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const team = getTeams()?.teams.find((t) => t.slug === slug);
  return { title: team ? `${team.team} — FIFA 2026 Predictor` : "Team — FIFA 2026 Predictor" };
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const team = getTeams()?.teams.find((t) => t.slug === slug);
  if (!team) notFound();
  const stats = getTeamStats()?.team_stats?.[slug];
  const alive = team.status !== "eliminated";

  return (
    <div className="space-y-10 py-10">
      <div>
        <Link href="/teams" className="text-sm text-fg2 hover:text-cyan">← All teams</Link>
        <div className="mt-2 flex flex-wrap items-center gap-4">
          <h1 className="text-4xl font-extrabold">
            {team.flag ? `${team.flag} ` : ""}
            {team.team}
          </h1>
          <span className={`rounded px-3 py-1 text-sm font-semibold ${alive ? "bg-green/15 text-green" : "bg-hot/15 text-hot"}`}>{STATUS_LABELS[team.status]}</span>
        </div>
        <p className="mt-2 text-fg2">
          Group {team.group ?? "—"} {team.code ? `· ${team.code}` : ""} · Stage reached: {team.stage_reached}
          {!alive && team.eliminated_by ? ` · Eliminated in ${team.eliminated_in} by ${team.eliminated_by}` : ""}
        </p>
      </div>

      <section aria-labelledby="record-heading">
        <h2 id="record-heading" className="mb-3 text-xl font-bold">Tournament record</h2>
        <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
          {[
            ["Played", stats?.played ?? team.played],
            ["Wins", stats?.wins ?? team.wins],
            ["Draws", stats?.draws ?? team.draws],
            ["Losses", stats?.losses ?? team.losses],
            ["Goals for", stats?.goals_for ?? team.goals_for],
            ["Goals against", stats?.goals_against ?? team.goals_against],
            ["Goal difference", stats?.goal_difference ?? team.goal_difference],
            ["Clean sheets", stats?.clean_sheets ?? "—"],
            ["Avg scored", stats?.avg_goals_for ?? "—"],
            ["Avg conceded", stats?.avg_goals_against ?? "—"],
          ].map(([label, value]) => (
            <div key={String(label)} className="card p-3 text-center">
              <p className="font-mono text-xl font-bold">{String(value)}</p>
              <p className="text-xs text-fg2">{label}</p>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-fg2">Derived from completed real tournament matches only.</p>
      </section>

      <section aria-labelledby="forecast-heading">
        <h2 id="forecast-heading" className="mb-3 text-xl font-bold">Current forecast</h2>
        {alive ? (
          <div className="card space-y-3 p-5">
            {team.champion_probability != null && <ProbBar label="Champion" value={team.champion_probability} color="var(--accent-magenta)" />}
            {team.reach_final_probability != null && <ProbBar label="Reach final" value={team.reach_final_probability} color="var(--accent-cyan)" />}
            {team.next_matchup && (
              <p className="text-sm">
                Next: <span className="font-semibold">vs {team.next_matchup.opponent}</span> ({team.next_matchup.stage})
                {team.next_matchup.advance_probability != null && (
                  <>
                    {" "}— advance probability <span className="font-mono text-cyan">{formatPct(team.next_matchup.advance_probability)}</span>
                    <span className="text-fg2"> · {team.next_matchup.source_label}</span>
                  </>
                )}
              </p>
            )}
          </div>
        ) : (
          <div className="card p-5 text-fg2">
            Eliminated in {team.eliminated_in ?? team.stage_reached}
            {team.eliminated_by ? ` by ${team.eliminated_by}` : ""}. Final record: {team.wins}W-{team.draws}D-{team.losses}L, goals {team.goals_for}:{team.goals_against}.
          </div>
        )}
      </section>

      <section aria-labelledby="journey-heading">
        <h2 id="journey-heading" className="mb-3 text-xl font-bold">Tournament journey</h2>
        {stats?.matches?.length ? (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-fg2">
                  <th className="p-3">Date</th>
                  <th className="p-3">Stage</th>
                  <th className="p-3">Opponent</th>
                  <th className="p-3">Score</th>
                  <th className="p-3">Result</th>
                </tr>
              </thead>
              <tbody>
                {stats.matches.map((match) => (
                  <tr key={`${match.date}-${match.opponent}`} className="border-b border-line/50">
                    <td className="p-3 font-mono text-fg2">{match.date}</td>
                    <td className="p-3">{match.stage}</td>
                    <td className="p-3">{match.opponent}</td>
                    <td className="p-3 font-mono">{match.score}</td>
                    <td className="p-3">
                      <span className={`rounded px-2 py-0.5 text-xs font-bold ${match.result === "W" ? "bg-green/15 text-green" : match.result === "D" ? "bg-warn/15 text-warn" : "bg-hot/15 text-hot"}`}>
                        {match.result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-fg2">No completed matches recorded.</p>
        )}
      </section>
      <p className="text-xs text-fg2">Player-level statistics are not currently part of the verified data pipeline. Forecast history charts are available in the interactive dashboard.</p>
    </div>
  );
}
