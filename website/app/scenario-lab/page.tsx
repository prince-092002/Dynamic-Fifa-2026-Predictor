import type { Metadata } from "next";
import ScenarioLab from "@/features/scenario-lab/components/ScenarioLab";
import { buildScenarioSnapshot } from "@/features/scenario-lab/lib/adapter";
import {
  getBracket,
  getChampionForecast,
  getFinalistForecast,
  getFinalistPairs,
  getMatchupPredictions,
  getOverview,
  getTeams,
} from "@/lib/data";

export const metadata: Metadata = {
  title: "Scenario Lab - FIFA 2026 Predictor",
  description:
    "Create hypothetical match outcomes and run an isolated browser-based simulation of the remaining FIFA 2026 tournament.",
};

export default function ScenarioLabPage() {
  const snapshot = buildScenarioSnapshot({
    overview: getOverview(),
    bracket: getBracket(),
    teams: getTeams()?.teams ?? [],
    matchupPredictions: getMatchupPredictions()?.matchups ?? [],
    championForecast: getChampionForecast()?.entries ?? [],
    finalistForecast: getFinalistForecast()?.entries ?? [],
    finalPairs: getFinalistPairs()?.entries ?? [],
  });

  return <ScenarioLab snapshot={snapshot} />;
}
