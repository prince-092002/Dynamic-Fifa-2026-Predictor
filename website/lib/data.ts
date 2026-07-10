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
import type { Overview, Bracket, ChampionEntry, FinalistPairEntry, Team, TeamStats, MatchupPrediction, ModelInsights } from "./types";

export const getOverview = () => readJson<Overview>("latest_overview.json");
export const getBracket = () => readJson<Bracket>("knockout_bracket.json");
export const getChampionForecast = () => readJson<{ entries: ChampionEntry[]; simulations: number | null }>("champion_forecast.json");
export const getFinalistPairs = () => readJson<{ entries: FinalistPairEntry[] }>("finalist_pairs.json");
export const getTeams = () => readJson<{ teams: Team[] }>("teams.json");
export const getTeamStats = () => readJson<{ team_stats: Record<string, TeamStats> }>("team_stats.json");
export const getMatchupPredictions = () => readJson<{ matchups: MatchupPrediction[] }>("matchup_predictions.json");
export const getModelInsights = () => readJson<ModelInsights>("model_insights.json");

