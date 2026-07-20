export interface FinalResult {
  champion: string;
  runner_up: string | null;
  champion_goals: number | null;
  runner_up_goals: number | null;
  score: string | null;
  score_duration: string | null;
  decided_label: string;
  went_to_extra_time: boolean;
  match_date: string | null;
  published_at: string;
  published_label: string;
}

export interface Overview {
  current_phase: string | null;
  tournament_complete?: boolean;
  final_result?: FinalResult | null;
  completed_matches: number | null;
  teams_total: number;
  teams_alive: number;
  teams_eliminated: number;
  known_unresolved_matchups: number;
  top_champion: string | null;
  top_champion_probability: number | null;
  champion_probability_basis?: string | null;
  monte_carlo_top_champion?: string | null;
  monte_carlo_top_champion_probability?: number | null;
  top_finalist_pair: string | null;
  top_finalist_pair_probability: number | null;
  forecast_mode: string | null;
  public_label: string | null;
  provider: string;
  data_source_mode: string;
  data_age_minutes: number | null;
  source_quality_score: number | null;
  simulations: number | null;
  selected_model: string | null;
  live_forecast_validation: string | null;
  broader_refresh_validation: string | null;
  run_id: string | null;
  _meta?: { generated_at: string };
}

export interface BracketMatch {
  fixture_id: number;
  stage: string;
  date: string | null;
  state: "completed" | "scheduled_known" | "tbd";
  team_a: string | null;
  team_b: string | null;
  score?: string | null;
  score_duration?: string | null;
  winner?: string | null;
  team_a_advance_probability?: number | null;
  team_b_advance_probability?: number | null;
  predicted_favorite?: string;
  source: string;
  source_label: string;
  model?: string;
  placeholder?: string;
}

export interface Bracket {
  rounds: { stage: string; matches: BracketMatch[] }[];
  source_legend: Record<string, string>;
  current_phase: string;
  _meta?: { generated_at: string };
}

export interface ChampionEntry {
  team: string;
  slug: string;
  champion_probability: number;
  monte_carlo_champion_probability?: number | null;
  probability_basis?: string | null;
  source_match_id?: string | number | null;
  model_name?: string | null;
  probability_source?: string | null;
  prediction_generated_at?: string | null;
}

export interface FinalistEntry {
  team: string;
  slug: string;
  reach_final_probability: number;
}

export interface FinalistPairEntry {
  finalist_team_1: string;
  finalist_team_2: string;
  finalist_pair_key: string;
  probability: number;
}

export interface NextMatchup {
  opponent: string;
  stage: string;
  date?: string;
  advance_probability?: number | null;
  source_label?: string;
}

export interface Team {
  team: string;
  slug: string;
  code: string | null;
  flag: string | null;
  group: string | null;
  status: "alive" | "eliminated" | "champion" | "runner_up" | "third_place";
  stage_reached: string;
  eliminated_by: string | null;
  eliminated_in: string | null;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  champion_probability: number | null;
  reach_final_probability: number | null;
  next_matchup: NextMatchup | null;
  latest_result: TeamMatch | null;
}

export interface TeamMatch {
  date: string;
  stage: string;
  opponent: string;
  goals_for: number;
  goals_against: number;
  result: "W" | "D" | "L";
  score: string;
}

export interface TeamStats {
  team: string;
  slug: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for: number;
  goals_against: number;
  goal_difference: number;
  clean_sheets: number;
  avg_goals_for: number | null;
  avg_goals_against: number | null;
  matches: TeamMatch[];
}

export interface MatchupPrediction {
  stage: string;
  team_a: string;
  team_b: string;
  team_a_advance_probability: number | null;
  team_b_advance_probability: number | null;
  favorite: string | null;
  model: string | null;
  prediction_status: string;
  source_label: string;
}

export interface ModelInsights {
  models: {
    model: string;
    selected: boolean;
    test_accuracy: number | null;
    test_log_loss: number | null;
    test_brier_score: number | null;
    test_macro_f1: number | null;
    train_rows: number | null;
    test_rows: number | null;
  }[];
  selected_feature_columns: string[];
  global_feature_importance: { feature: string; importance: number }[] | null;
  importance_note: string;
  diagnostics?: {
    evaluation: string;
    per_class: Record<string, { precision: number | null; recall: number | null; f1: number | null }>;
    actual_distribution: Record<string, number>;
    predicted_distribution: Record<string, number>;
    calibration_ece: number | null;
    macro_f1_note: string;
  } | null;
}

export const formatPct = (value: number | null | undefined, digits = 2) =>
  value === null || value === undefined ? "—" : `${(value * 100).toFixed(digits)}%`;

const PHASE_LABELS: Record<string, string> = { complete: "Tournament complete" };

export const formatPhase = (phase: string | null | undefined) =>
  phase
    ? PHASE_LABELS[phase] ?? phase.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "—";

export const STATUS_LABELS: Record<Team["status"], string> = {
  alive: "Still alive",
  eliminated: "Eliminated",
  champion: "Champion",
  runner_up: "Runner-up",
  third_place: "Third place",
};
