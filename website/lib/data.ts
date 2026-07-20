import fs from "fs";
import path from "path";

// public_data/ lives at the repository root, one level above website/.
// All reads happen at build time (static generation); nothing is fetched client-side.
const PUBLIC_DATA_DIR = path.join(process.cwd(), "..", "public_data");

function readJson<T>(name: string): T | null {
  try {
    const file = path.join(PUBLIC_DATA_DIR, name);
    if (!fs.existsSync(file)) return null;
    return JSON.parse(fs.readFileSync(file, "utf-8")) as T;
  } catch {
    return null;
  }
}

export * from "./types";
import type { Overview, Bracket, ChampionEntry, FinalistEntry, FinalistPairEntry, Team, TeamStats, MatchupPrediction, ModelInsights } from "./types";

export const getOverview = () => readJson<Overview>("latest_overview.json");
export const getBracket = () => readJson<Bracket>("knockout_bracket.json");
export const getChampionForecast = () => readJson<{ entries: ChampionEntry[]; simulations: number | null }>("champion_forecast.json");
export const getFinalistForecast = () => readJson<{ entries: FinalistEntry[]; simulations: number | null }>("finalist_forecast.json");
export const getFinalistPairs = () => readJson<{ entries: FinalistPairEntry[] }>("finalist_pairs.json");
export const getTeams = () => readJson<{ teams: Team[] }>("teams.json");
export const getTeamStats = () => readJson<{ team_stats: Record<string, TeamStats> }>("team_stats.json");
export const getMatchupPredictions = () => readJson<{ matchups: MatchupPrediction[] }>("matchup_predictions.json");
export const getModelInsights = () => readJson<ModelInsights>("model_insights.json");

interface ChampionHistoryPoint {
  run_id: string;
  timestamp: string;
  phase: string;
  team: string;
  champion_probability: number;
}

/**
 * The last champion forecast archived *before* the final was played.
 *
 * Read from the committed forecast history so the pre-match probabilities shown beside the
 * result are the genuine archived numbers — never rewritten after the outcome was known.
 */
export function getPreFinalForecast(): { entries: { team: string; probability: number }[]; timestamp: string | null } | null {
  const history = readJson<{ champion?: ChampionHistoryPoint[] }>("forecast_history.json");
  const points = history?.champion ?? [];
  const preFinal = points.filter((p) => p.phase === "final");
  if (preFinal.length === 0) return null;
  const lastRun = preFinal[preFinal.length - 1].run_id;
  const entries = preFinal
    .filter((p) => p.run_id === lastRun)
    .map((p) => ({ team: p.team, probability: p.champion_probability }))
    .sort((a, b) => b.probability - a.probability);
  return entries.length ? { entries, timestamp: preFinal[preFinal.length - 1].timestamp ?? null } : null;
}

