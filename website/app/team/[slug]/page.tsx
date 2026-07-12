import Link from "next/link";
import { notFound } from "next/navigation";
import { ProbRing, Meter } from "@/components/ui";
import { Arrow, Shield, Bolt, Trophy, Route, Calendar } from "@/components/icons";
import CountryFlag from "@/components/CountryFlag";
import { STATUS_LABELS, formatPct, getTeamStats, getTeams } from "@/lib/data";

export function generateStaticParams() {
  return (getTeams()?.teams ?? []).map((team) => ({ slug: team.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const team = getTeams()?.teams.find((t) => t.slug === slug);
  return { title: team ? `${team.team} — Team Intelligence` : "Team — FIFA 2026 Predictor" };
}

export default async function TeamPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const team = getTeams()?.teams.find((t) => t.slug === slug);
  if (!team) notFound();
  const stats = getTeamStats()?.team_stats?.[slug];
  const alive = team.status !== "eliminated";
  const matches = stats?.matches ?? [];
  const form = matches.slice(-6);
  const played = stats?.played ?? team.played;

  const strength: [string, number][] = [
    ["Win rate", played ? (stats?.wins ?? team.wins) / played : 0],
    ["Attack (goals/match)", Math.min(1, (stats?.avg_goals_for ?? 0) / 3)],
    ["Defense (clean sheets)", played ? (stats?.clean_sheets ?? 0) / played : 0],
    ["Goal control", Math.max(0, Math.min(1, 0.5 + (stats?.goal_difference ?? team.goal_difference) / (played * 3 || 1)))],
  ];

  return (
    <div className="relative">
      {/* hero */}
      <div className="relative overflow-hidden border-b border-line/60">
        <div className="bg-floodlight bg-grid absolute inset-0 opacity-80" aria-hidden />
        <div className="relative mx-auto max-w-[78rem] px-4 pb-8 pt-10">
          <Link href="/teams" className="inline-flex items-center gap-1.5 text-sm text-fg3 hover:text-cyan"><Arrow width={14} height={14} className="rotate-180" /> All teams</Link>
          <div className="mt-4 flex flex-wrap items-end justify-between gap-6">
            <div>
              <div className="kicker">Team intelligence profile</div>
              <div className="mt-2 flex items-center gap-4">
                <CountryFlag code={team.code} country={team.team} size="xl" className="!h-10 !w-16" />
                <div>
                  <h1 className="display text-4xl md:text-5xl text-fg">{team.team}</h1>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`chip !py-0.5 ${alive ? "!border-pitch/40 !text-pitch" : "!border-crimson/40 !text-crimson"}`}>{STATUS_LABELS[team.status]}</span>
                    <span className="chip !py-0.5">Group {team.group ?? "—"}</span>
                    <span className="chip !py-0.5">Reached {team.stage_reached}</span>
                  </div>
                </div>
              </div>
            </div>
            {alive && team.champion_probability != null && (
              <div className="flex items-center gap-5">
                <div className="text-center"><ProbRing value={team.champion_probability} size={92} stroke={9} color="var(--gold-c)" label="champion" /></div>
                {team.reach_final_probability != null && <div className="text-center"><ProbRing value={team.reach_final_probability} size={92} stroke={9} color="var(--cyan)" label="final" /></div>}
              </div>
            )}
          </div>
          {/* form strip */}
          {form.length > 0 && (
            <div className="mt-6 flex items-center gap-2">
              <span className="kicker mr-1">Recent form</span>
              {form.map((m, i) => <span key={i} className={`res res-${m.result.toLowerCase()}`} title={`${m.opponent} ${m.score} (${m.stage})`}>{m.result}</span>)}
            </div>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-[78rem] px-4 py-10">
        {/* record */}
        <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
          {[["Played", played], ["Wins", stats?.wins ?? team.wins], ["Draws", stats?.draws ?? team.draws], ["Losses", stats?.losses ?? team.losses], ["Goals for", stats?.goals_for ?? team.goals_for], ["Goals against", stats?.goals_against ?? team.goals_against]].map(([l, v]) => (
            <div key={l as string} className="card p-3 text-center"><div className="stat-num text-2xl text-fg">{String(v)}</div><div className="mt-1 text-[0.66rem] uppercase tracking-wide text-fg3">{l as string}</div></div>
          ))}
        </div>

        <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.3fr]">
          {/* strength profile */}
          <div className="card p-6">
            <div className="flex items-center gap-2 text-cyan"><Shield width={17} height={17} /><h2 className="font-display text-lg font-semibold text-fg">Strength profile</h2></div>
            <p className="mt-1 text-xs text-fg3">Derived from completed real tournament matches.</p>
            <div className="mt-4 space-y-3.5">
              {strength.map(([l, v]) => (
                <div key={l}><div className="mb-1 flex justify-between text-sm"><span className="text-fg2">{l}</span><span className="stat-num text-fg">{(v * 100).toFixed(0)}</span></div><Meter value={v} color="var(--pitch)" /></div>
              ))}
            </div>
            <div className="hairline my-5" />
            {alive ? (
              <div className="flex items-center gap-2 text-sm">
                <Bolt width={16} height={16} className="text-gold" />
                {team.next_matchup ? (
                  <span className="text-fg2">Next: <span className="font-semibold text-fg">vs {team.next_matchup.opponent}</span> ({team.next_matchup.stage})
                    {team.next_matchup.advance_probability != null && <> — advance <span className="stat-num text-cyan">{formatPct(team.next_matchup.advance_probability)}</span></>}</span>
                ) : <span className="text-fg2">Awaiting next opponent.</span>}
              </div>
            ) : (
              <div className="text-sm text-fg2">Eliminated in {team.eliminated_in ?? team.stage_reached}{team.eliminated_by ? ` by ${team.eliminated_by}` : ""}.</div>
            )}
          </div>

          {/* journey */}
          <div className="card p-6">
            <div className="flex items-center gap-2 text-cyan"><Route width={17} height={17} /><h2 className="font-display text-lg font-semibold text-fg">Tournament journey</h2></div>
            {matches.length ? (
              <div className="mt-4 space-y-2">
                {matches.map((m) => (
                  <div key={`${m.date}-${m.opponent}`} className="flex items-center gap-3 rounded-lg border border-line bg-surface/40 px-3 py-2">
                    <span className={`res res-${m.result.toLowerCase()} shrink-0`}>{m.result}</span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm text-fg">vs {m.opponent}</div>
                      <div className="flex items-center gap-1.5 text-[0.68rem] text-fg3"><Calendar width={11} height={11} /> {m.date} · {m.stage}</div>
                    </div>
                    <span className="stat-num text-lg text-fg">{m.score}</span>
                  </div>
                ))}
              </div>
            ) : <p className="mt-4 text-fg2">No completed matches recorded.</p>}
          </div>
        </div>

        {/* future module placeholder — no fabricated data */}
        <div className="card mt-4 border-dashed p-5">
          <div className="flex items-center gap-2 text-fg3"><Trophy width={16} height={16} /><span className="font-display text-sm font-semibold text-fg2">Squad & tactical intelligence</span></div>
          <p className="mt-1 text-sm text-fg3">Expected XI, squad depth, and tactical profiles are planned for a future model expansion. Player-level statistics are not currently part of the verified data pipeline, so none are shown.</p>
        </div>
        <p className="mt-4 text-xs text-fg3">Forecast-evolution charts for this team are available in the interactive dashboard.</p>
      </div>
    </div>
  );
}
