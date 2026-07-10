import type { Metadata } from "next";
import TeamExplorer from "@/components/TeamExplorer";
import { getTeams } from "@/lib/data";

export const metadata: Metadata = { title: "Teams — FIFA 2026 Predictor" };

export default function TeamsPage() {
  const payload = getTeams();
  if (!payload?.teams?.length) {
    return <div className="card mt-10 p-6 text-fg2">Team data unavailable. Run the live forecast pipeline and rebuild public exports.</div>;
  }
  return (
    <div className="py-10">
      <h1 className="text-3xl font-bold">Team Explorer</h1>
      <p className="mt-2 text-fg2">All {payload.teams.length} tournament teams with real completed-match statistics, live status, and current forecasts.</p>
      <TeamExplorer teams={payload.teams} />
    </div>
  );
}
