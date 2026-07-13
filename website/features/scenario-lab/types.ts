export type ScenarioChoice = "model" | "team_a" | "team_b";

export type ScenarioSnapshotStatus = "ready" | "complete" | "invalid";

export interface ScenarioTeam {
  name: string;
  slug: string;
  code: string | null;
  status: string;
  played: number;
  wins: number;
  draws: number;
  goalDifference: number;
}

export interface ScenarioMatch {
  id: string;
  fixtureId: number;
  stage: string;
  date: string | null;
  state: "completed" | "scheduled_known" | "tbd";
  teamA: string | null;
  teamB: string | null;
  winner: string | null;
  teamAAdvanceProbability: number | null;
  teamBAdvanceProbability: number | null;
  probabilitySource: string | null;
}

export interface ScenarioRound {
  stage: string;
  matches: ScenarioMatch[];
}

export interface PublishedMatchup {
  stage: string;
  teamA: string;
  teamB: string;
  teamAAdvanceProbability: number;
  teamBAdvanceProbability: number;
  sourceLabel: string;
}

export interface OfficialTeamProbability {
  team: string;
  championProbability: number;
  finalistProbability: number;
}

export interface OfficialFinalPair {
  teamA: string;
  teamB: string;
  probability: number;
}

export interface ScenarioSnapshot {
  status: ScenarioSnapshotStatus;
  error: string | null;
  snapshotId: string;
  generatedAt: string | null;
  currentPhase: string;
  forecastMode: string;
  officialLabel: string;
  provider: string;
  rounds: ScenarioRound[];
  teams: Record<string, ScenarioTeam>;
  activeTeams: string[];
  knownUnresolvedMatchIds: string[];
  publishedMatchups: PublishedMatchup[];
  officialProbabilities: OfficialTeamProbability[];
  officialFinalPairs: OfficialFinalPair[];
}

export interface ScenarioSettings {
  simulations: 1000 | 5000 | 10000;
  seed: number;
  choices: Record<string, ScenarioChoice>;
}

export type ProbabilitySource = "published_matchup" | "published_tournament_form";

export interface ProbabilityResolution {
  teamAProbability: number;
  source: ProbabilitySource;
}

export interface TeamProbabilityResult {
  team: string;
  probability: number;
}

export interface FinalPairResult {
  teamA: string;
  teamB: string;
  probability: number;
}

export interface ScenarioSimulationResult {
  simulations: number;
  seed: number;
  forcedOutcomeCount: number;
  championProbabilities: TeamProbabilityResult[];
  finalistProbabilities: TeamProbabilityResult[];
  finalPairProbabilities: FinalPairResult[];
  fixtureAdvancementProbabilities: Record<string, Record<string, number>>;
  probabilitySourceCounts: Record<ProbabilitySource, number>;
  completedMatchesLocked: number;
}

export interface ScenarioUiState {
  settings: ScenarioSettings;
  result: ScenarioSimulationResult | null;
}

export interface ScenarioSourcePayload {
  overview: {
    current_phase: string | null;
    forecast_mode: string | null;
    public_label: string | null;
    provider: string;
    run_id: string | null;
    _meta?: { generated_at?: string };
  } | null;
  bracket: {
    current_phase: string;
    rounds: Array<{
      stage: string;
      matches: Array<{
        fixture_id: number;
        stage: string;
        date: string | null;
        state: "completed" | "scheduled_known" | "tbd";
        team_a: string | null;
        team_b: string | null;
        winner?: string | null;
        team_a_advance_probability?: number | null;
        team_b_advance_probability?: number | null;
        source_label: string;
      }>;
    }>;
    _meta?: { generated_at?: string; run_id?: string };
  } | null;
  teams: Array<{
    team: string;
    slug: string;
    code: string | null;
    status: string;
    played: number;
    wins: number;
    draws: number;
    goal_difference: number;
  }>;
  matchupPredictions: Array<{
    stage: string;
    team_a: string;
    team_b: string;
    team_a_advance_probability: number | null;
    team_b_advance_probability: number | null;
    source_label: string;
  }>;
  championForecast: Array<{ team: string; champion_probability: number }>;
  finalistForecast: Array<{ team: string; reach_final_probability: number }>;
  finalPairs: Array<{
    finalist_team_1: string;
    finalist_team_2: string;
    probability: number;
  }>;
}
