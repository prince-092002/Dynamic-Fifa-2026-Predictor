import type { Metadata } from "next";
import TeamExplorer from "@/components/TeamExplorer";
import { Kicker } from "@/components/ui";
import { Team } from "@/components/icons";
import { getTeams } from "@/lib/data";

export const metadata: Metadata = { title: "Team Intelligence — FIFA 2026 Predictor" };

export default function TeamsPage() {
  const payload = getTeams();
  if (!payload?.teams?.length) {
    return <div className="mx-auto max-w-[78rem] px-4 py-16"><div className="card p-6 text-fg2">Team data unavailable. Run the live forecast pipeline and rebuild public exports.</div></div>;
  }
  return (
    <div className="relative">
      <div className="bg-floodlight bg-grid absolute inset-x-0 top-0 h-64 opacity-70" aria-hidden />
      <div className="relative mx-auto max-w-[78rem] px-4 py-14">
        <Kicker icon={<Team width={14} height={14} />}>Team intelligence</Kicker>
        <h1 className="display mt-3 text-4xl text-fg">The contenders</h1>
        <p className="mt-3 max-w-2xl text-fg2">All {payload.teams.length} tournament teams with real completed-match records, live alive/eliminated status, and current champion & finalist odds. Select a team for its full dossier.</p>
        <TeamExplorer teams={payload.teams} />
      </div>
    </div>
  );
}
