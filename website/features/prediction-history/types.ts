export type PredictionOutcome = "correct" | "incorrect" | "pending";

export interface HistoryProbability {
  team: string;
  probability: number;
  probability_basis?: string | null;
  monte_carlo_probability?: number | null;
}

export interface HistoryFinalPair {
  team_1: string;
  team_2: string;
  pair_key?: string | null;
  probability: number;
}

export interface HistoryMainForecast {
  most_likely_champion: HistoryProbability | null;
  second_most_likely_champion: HistoryProbability | null;
  champion_probabilities: HistoryProbability[];
  champion_probability_basis?: string | null;
  most_likely_final: HistoryFinalPair | null;
  finalist_probabilities: HistoryProbability[];
  predicted_final_winner: string | null;
}

export interface HistoryMatchPrediction {
  match_id: string | number;
  stage: string;
  scheduled_at: string | null;
  team_a: string;
  team_b: string;
  team_a_win_probability: number;
  team_b_win_probability: number;
  draw_probability?: number | null;
  predicted_winner: string | null;
  prediction_method: string;
  status_at_snapshot?: string;
  actual_winner: string | null;
  actual_score: string | null;
  prediction_outcome: PredictionOutcome;
}

export interface PredictionHistorySnapshot {
  schema_version: string;
  snapshot_id: string;
  generated_at: string;
  display_date: string;
  timezone: string;
  tournament_phase: string;
  completed_matches: number | null;
  remaining_matches: number | null;
  teams_alive: number | null;
  teams_eliminated: number | null;
  provider: string | null;
  forecast_mode: string | null;
  source_quality_score: number | null;
  simulation_count: number | null;
  seed: number | null;
  selected_model: string | null;
  run_id: string | null;
  record_class: "genuine_archived_forecast" | "recovered_from_committed_output" | string;
  provenance: Record<string, unknown>;
  main_forecast: HistoryMainForecast;
  matchday_predictions: HistoryMatchPrediction[];
  state_hash: string;
}

export interface HistoryDateOption {
  displayDate: string;
  snapshotId: string;
}

export interface PredictionHistoryDataset {
  status: "ready" | "empty";
  snapshots: PredictionHistorySnapshot[];
  dateOptions: HistoryDateOption[];
  latestSnapshotId: string | null;
  skippedSnapshots: number;
  teamCodes: Record<string, string | null>;
  currentTeamStatuses: Record<string, string>;
  accuracy: {
    correct: number;
    resolved: number;
    pending: number;
  };
}

export interface HistorySelection {
  selected: PredictionHistorySnapshot | null;
  previous: PredictionHistorySnapshot | null;
  isLatest: boolean;
}
