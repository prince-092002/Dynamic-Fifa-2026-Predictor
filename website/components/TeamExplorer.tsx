"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Team } from "@/lib/types";
import { STATUS_LABELS, formatPct } from "@/lib/types";

const SORTS: Record<string, (a: Team, b: Team) => number> = {
  "Championship probability": (a, b) => (b.champion_probability ?? -1) - (a.champion_probability ?? -1),
  "Finalist probability": (a, b) => (b.reach_final_probability ?? -1) - (a.reach_final_probability ?? -1),
  "Goals scored": (a, b) => b.goals_for - a.goals_for,
  "Goal difference": (a, b) => b.goal_difference - a.goal_difference,
  "Matches won": (a, b) => b.wins - a.wins,
  Alphabetical: (a, b) => a.team.localeCompare(b.team),
};

export default function TeamExplorer({ teams }: { teams: Team[] }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [group, setGroup] = useState("All");
  const [sort, setSort] = useState("Championship probability");
  const groups = useMemo(() => Array.from(new Set(teams.map((t) => t.group).filter(Boolean))).sort() as string[], [teams]);

  const filtered = useMemo(() => {
    let list = teams;
    if (query) list = list.filter((t) => t.team.toLowerCase().includes(query.toLowerCase()));
    if (status === "Still alive") list = list.filter((t) => t.status !== "eliminated");
    if (status === "Eliminated") list = list.filter((t) => t.status === "eliminated");
    if (group !== "All") list = list.filter((t) => t.group === group);
    return list.slice().sort(SORTS[sort]);
  }, [teams, query, status, group, sort]);

  return (
    <div className="mt-6">
      <div className="mb-6 grid gap-3 md:grid-cols-4">
        <label className="text-sm text-fg2">
          Search
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Team name…" className="mt-1 w-full rounded border border-line bg-surface px-3 py-2 text-fg" />
        </label>
        <label className="text-sm text-fg2">
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)} className="mt-1 w-full rounded border border-line bg-surface px-3 py-2 text-fg">
            {["All", "Still alive", "Eliminated"].map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        <label className="text-sm text-fg2">
          Group
          <select value={group} onChange={(e) => setGroup(e.target.value)} className="mt-1 w-full rounded border border-line bg-surface px-3 py-2 text-fg">
            <option>All</option>
            {groups.map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
        <label className="text-sm text-fg2">
          Sort by
          <select value={sort} onChange={(e) => setSort(e.target.value)} className="mt-1 w-full rounded border border-line bg-surface px-3 py-2 text-fg">
            {Object.keys(SORTS).map((option) => <option key={option}>{option}</option>)}
          </select>
        </label>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((team) => (
          <Link key={team.slug} href={`/team/${team.slug}`} className="card block p-4 transition-colors hover:border-cyan">
            <div className="flex items-center justify-between">
              <h2 className="font-bold">
                {team.flag ? `${team.flag} ` : ""}
                {team.team}
              </h2>
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${team.status === "eliminated" ? "bg-hot/15 text-hot" : "bg-green/15 text-green"}`}>
                {STATUS_LABELS[team.status]}
              </span>
            </div>
            <p className="mt-1 text-xs text-fg2">Group {team.group ?? "—"} · reached {team.stage_reached}</p>
            <div className="mt-3 grid grid-cols-4 gap-1 text-center text-xs">
              <div><p className="font-mono font-bold">{team.played}</p><p className="text-fg2">P</p></div>
              <div><p className="font-mono font-bold">{team.wins}-{team.draws}-{team.losses}</p><p className="text-fg2">W-D-L</p></div>
              <div><p className="font-mono font-bold">{team.goals_for}:{team.goals_against}</p><p className="text-fg2">Goals</p></div>
              <div><p className="font-mono font-bold">{team.goal_difference > 0 ? "+" : ""}{team.goal_difference}</p><p className="text-fg2">GD</p></div>
            </div>
            {team.status !== "eliminated" && team.champion_probability != null && (
              <p className="mt-3 text-sm">
                Champion: <span className="font-mono font-bold text-cyan">{formatPct(team.champion_probability)}</span>
                {team.next_matchup && <span className="text-fg2"> · next vs {team.next_matchup.opponent}</span>}
              </p>
            )}
            {team.status === "eliminated" && (
              <p className="mt-3 text-sm text-fg2">
                Eliminated in {team.eliminated_in ?? team.stage_reached}
                {team.eliminated_by ? ` by ${team.eliminated_by}` : ""}
              </p>
            )}
          </Link>
        ))}
      </div>
      {!filtered.length && <p className="text-fg2">No teams match the current filters.</p>}
    </div>
  );
}
