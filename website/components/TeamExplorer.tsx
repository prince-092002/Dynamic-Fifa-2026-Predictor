"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Team } from "@/lib/types";
import { STATUS_LABELS, formatPct } from "@/lib/types";
import { Meter } from "./ui";
import { Team as TeamIcon, Arrow } from "./icons";
import CountryFlag from "./CountryFlag";

const SORTS: Record<string, (a: Team, b: Team) => number> = {
  "Champion odds": (a, b) => (b.champion_probability ?? -1) - (a.champion_probability ?? -1),
  "Finalist odds": (a, b) => (b.reach_final_probability ?? -1) - (a.reach_final_probability ?? -1),
  "Goals scored": (a, b) => b.goals_for - a.goals_for,
  "Goal difference": (a, b) => b.goal_difference - a.goal_difference,
  Wins: (a, b) => b.wins - a.wins,
  "A–Z": (a, b) => a.team.localeCompare(b.team),
};
const STATUS = ["All", "Still alive", "Eliminated"];

export default function TeamExplorer({ teams, finalStage = false }: { teams: Team[]; finalStage?: boolean }) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All");
  const [group, setGroup] = useState("All");
  const [sort, setSort] = useState("Champion odds");
  const groups = useMemo(() => Array.from(new Set(teams.map((t) => t.group).filter(Boolean))).sort() as string[], [teams]);
  const sortLabels = finalStage ? Object.keys(SORTS).filter((label) => label !== "Finalist odds") : Object.keys(SORTS);

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
      {/* controls */}
      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-2">
          {STATUS.map((s) => (
            <button key={s} onClick={() => setStatus(s)} className={`chip chip-btn ${status === s ? "chip-active" : ""}`}>{s}</button>
          ))}
          <span className="mx-1 h-5 w-px bg-line-strong" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search team…" aria-label="Search team"
            className="w-40 rounded-lg border border-line-strong bg-surface px-3 py-1.5 text-sm text-fg placeholder:text-fg3" />
          <select value={group} onChange={(e) => setGroup(e.target.value)} aria-label="Group" className="rounded-lg border border-line-strong bg-surface px-3 py-1.5 text-sm text-fg">
            <option value="All">All groups</option>
            {groups.map((g) => <option key={g} value={g}>Group {g}</option>)}
          </select>
          <span className="ml-auto flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-fg3">Sort</span>
            {sortLabels.map((s) => (
              <button key={s} onClick={() => setSort(s)} className={`chip chip-btn !py-1 !px-2.5 !text-xs ${sort === s ? "chip-active" : ""}`}>{s}</button>
            ))}
          </span>
        </div>
      </div>

      {/* grid */}
      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((t) => {
          const alive = t.status !== "eliminated";
          return (
            <Link key={t.slug} href={`/team/${t.slug}`} className="card card-hover group block p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2.5">
                  <CountryFlag code={t.code} country={t.team} size="lg" />
                  <div>
                    <div className="font-display font-semibold text-fg">{t.team}</div>
                    <div className="text-xs text-fg3">Group {t.group ?? "—"} · {t.stage_reached}</div>
                  </div>
                </div>
                <span className={`chip !py-0.5 !px-2 !text-[0.66rem] ${alive ? "!border-pitch/40 !text-pitch" : "!border-crimson/40 !text-crimson"}`}>{STATUS_LABELS[t.status]}</span>
              </div>

              <div className="mt-3 grid grid-cols-4 gap-1 text-center">
                <Stat v={t.played} l="P" /><Stat v={`${t.wins}-${t.draws}-${t.losses}`} l="W-D-L" />
                <Stat v={`${t.goals_for}:${t.goals_against}`} l="GF:GA" /><Stat v={`${t.goal_difference > 0 ? "+" : ""}${t.goal_difference}`} l="GD" />
              </div>

              {alive && t.champion_probability != null ? (
                <div className="mt-3.5">
                  <div className="mb-1 flex items-center justify-between text-xs"><span className="text-fg2">Champion odds</span><span className="stat-num text-cyan">{formatPct(t.champion_probability)}</span></div>
                  <Meter value={t.champion_probability} color="var(--cyan)" />
                  {t.next_matchup && <div className="mt-2 flex items-center gap-1 text-xs text-fg3 transition-colors group-hover:text-fg2"><Arrow width={13} height={13} /> Next vs {t.next_matchup.opponent}</div>}
                </div>
              ) : (
                <div className="mt-3.5 text-xs text-fg3">Eliminated in {t.eliminated_in ?? t.stage_reached}{t.eliminated_by ? ` by ${t.eliminated_by}` : ""}</div>
              )}
            </Link>
          );
        })}
      </div>
      {!filtered.length && <div className="card mt-4 p-6 text-fg2"><TeamIcon width={18} height={18} /> No teams match these filters.</div>}
    </div>
  );
}

function Stat({ v, l }: { v: React.ReactNode; l: string }) {
  return <div><div className="stat-num text-sm text-fg">{v}</div><div className="text-[0.62rem] uppercase tracking-wide text-fg3">{l}</div></div>;
}
