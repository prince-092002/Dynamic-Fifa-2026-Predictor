import type {
  HistoryDateOption,
  HistoryMatchPrediction,
  HistorySelection,
  PredictionHistoryDataset,
  PredictionHistorySnapshot,
  PredictionOutcome,
} from "../types";

type UnknownRecord = Record<string, unknown>;

const record = (value: unknown): UnknownRecord | null =>
  value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as UnknownRecord)
    : null;

const text = (value: unknown, fallback = "") =>
  typeof value === "string" ? value : fallback;

const numberOrNull = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value) ? value : null;

const list = (value: unknown): unknown[] => (Array.isArray(value) ? value : []);

const HISTORY_TIME_ZONE = "America/Chicago";

export function historyDisplayDate(generatedAt: string, fallback = ""): string {
  const date = new Date(generatedAt);
  if (Number.isNaN(date.getTime())) return fallback;

  const parts = new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: HISTORY_TIME_ZONE,
  }).formatToParts(date);
  const value = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return value.year && value.month && value.day
    ? `${value.year}-${value.month}-${value.day}`
    : fallback;
}

function pairKey(teamA: string, teamB: string) {
  return [teamA, teamB].sort((left, right) => left.localeCompare(right)).join("\u0000");
}

function predictionOutcome(predicted: string | null, actual: string | null): PredictionOutcome {
  if (!actual) return "pending";
  return predicted && predicted === actual ? "correct" : "incorrect";
}

function parseProbability(value: unknown) {
  const item = record(value);
  const probability = numberOrNull(item?.probability);
  const team = text(item?.team);
  return item && team && probability !== null
    ? {
        team,
        probability,
        probability_basis: text(item.probability_basis) || null,
        monte_carlo_probability: numberOrNull(item.monte_carlo_probability),
      }
    : null;
}

function parseSnapshot(value: unknown): PredictionHistorySnapshot | null {
  const item = record(value);
  const forecast = record(item?.main_forecast);
  const snapshotId = text(item?.snapshot_id);
  const generatedAt = text(item?.generated_at);
  if (!item || !forecast || !snapshotId || !generatedAt) return null;

  const championProbabilities = list(forecast.champion_probabilities)
    .map(parseProbability)
    .filter((entry): entry is NonNullable<typeof entry> => entry !== null);
  const finalistProbabilities = list(forecast.finalist_probabilities)
    .map(parseProbability)
    .filter((entry): entry is NonNullable<typeof entry> => entry !== null);
  const likelyChampion = parseProbability(forecast.most_likely_champion);
  const secondChampion = parseProbability(forecast.second_most_likely_champion);
  const final = record(forecast.most_likely_final);
  const finalProbability = numberOrNull(final?.probability);
  const finalTeam1 = text(final?.team_1);
  const finalTeam2 = text(final?.team_2);

  const matches = list(item.matchday_predictions).flatMap((raw) => {
    const match = record(raw);
    const teamA = text(match?.team_a);
    const teamB = text(match?.team_b);
    const probabilityA = numberOrNull(match?.team_a_win_probability);
    const probabilityB = numberOrNull(match?.team_b_win_probability);
    if (!match || !teamA || !teamB || probabilityA === null || probabilityB === null) return [];
    const parsed: HistoryMatchPrediction = {
      match_id:
        typeof match.match_id === "number" || typeof match.match_id === "string"
          ? match.match_id
          : `${teamA}-${teamB}`,
      stage: text(match.stage, "Match"),
      scheduled_at: text(match.scheduled_at) || null,
      team_a: teamA,
      team_b: teamB,
      team_a_win_probability: probabilityA,
      team_b_win_probability: probabilityB,
      draw_probability: numberOrNull(match.draw_probability),
      predicted_winner: text(match.predicted_winner) || null,
      prediction_method: text(match.prediction_method, "Model"),
      status_at_snapshot: text(match.status_at_snapshot, "scheduled"),
      actual_winner: null,
      actual_score: null,
      prediction_outcome: "pending",
    };
    return [parsed];
  });

  return {
    schema_version: text(item.schema_version, "1.0"),
    snapshot_id: snapshotId,
    generated_at: generatedAt,
    display_date: historyDisplayDate(
      generatedAt,
      text(item.display_date, generatedAt.slice(0, 10)),
    ),
    timezone: text(item.timezone, "UTC"),
    tournament_phase: text(item.tournament_phase, "unknown"),
    completed_matches: numberOrNull(item.completed_matches),
    remaining_matches: numberOrNull(item.remaining_matches),
    teams_alive: numberOrNull(item.teams_alive),
    teams_eliminated: numberOrNull(item.teams_eliminated),
    provider: text(item.provider) || null,
    forecast_mode: text(item.forecast_mode) || null,
    source_quality_score: numberOrNull(item.source_quality_score),
    simulation_count: numberOrNull(item.simulation_count),
    seed: numberOrNull(item.seed),
    selected_model: text(item.selected_model) || null,
    run_id: text(item.run_id) || null,
    record_class: text(item.record_class, "recovered_from_committed_output"),
    provenance: record(item.provenance) ?? {},
    main_forecast: {
      most_likely_champion: likelyChampion,
      second_most_likely_champion: secondChampion,
      champion_probabilities: championProbabilities,
      champion_probability_basis: text(forecast.champion_probability_basis) || null,
      most_likely_final:
        final && finalTeam1 && finalTeam2 && finalProbability !== null
          ? {
              team_1: finalTeam1,
              team_2: finalTeam2,
              pair_key: text(final.pair_key) || null,
              probability: finalProbability,
            }
          : null,
      finalist_probabilities: finalistProbabilities,
      predicted_final_winner: text(forecast.predicted_final_winner) || null,
    },
    matchday_predictions: matches,
    state_hash: text(item.state_hash),
  };
}

export function isConfirmedFinalSnapshot(snapshot: PredictionHistorySnapshot): boolean {
  const final = snapshot.main_forecast.most_likely_final;
  if (snapshot.tournament_phase.toLowerCase() !== "final" || !final || final.probability < 0.999999) {
    return false;
  }
  const expected = [final.team_1, final.team_2].sort().join("\u0000");
  return snapshot.matchday_predictions.some(
    (match) =>
      match.stage.toLowerCase() === "final" &&
      [match.team_a, match.team_b].sort().join("\u0000") === expected,
  );
}

function completedResults(bracketPayload: unknown) {
  const bracket = record(bracketPayload);
  const byId = new Map<string, { winner: string; score: string | null }>();
  const byPair = new Map<string, { winner: string; score: string | null }>();
  for (const rawRound of list(bracket?.rounds)) {
    const round = record(rawRound);
    for (const rawMatch of list(round?.matches)) {
      const match = record(rawMatch);
      const winner = text(match?.winner);
      const teamA = text(match?.team_a);
      const teamB = text(match?.team_b);
      if (!match || text(match.state) !== "completed" || !winner || !teamA || !teamB) continue;
      const result = { winner, score: text(match.score) || null };
      if (typeof match.fixture_id === "number" || typeof match.fixture_id === "string") {
        byId.set(String(match.fixture_id), result);
      }
      byPair.set(pairKey(teamA, teamB), result);
    }
  }
  return { byId, byPair };
}

function enrichSnapshot(
  snapshot: PredictionHistorySnapshot,
  results: ReturnType<typeof completedResults>,
): PredictionHistorySnapshot {
  return {
    ...snapshot,
    provenance: { ...snapshot.provenance },
    main_forecast: {
      ...snapshot.main_forecast,
      champion_probabilities: snapshot.main_forecast.champion_probabilities.map((entry) => ({ ...entry })),
      finalist_probabilities: snapshot.main_forecast.finalist_probabilities.map((entry) => ({ ...entry })),
      most_likely_champion: snapshot.main_forecast.most_likely_champion
        ? { ...snapshot.main_forecast.most_likely_champion }
        : null,
      second_most_likely_champion: snapshot.main_forecast.second_most_likely_champion
        ? { ...snapshot.main_forecast.second_most_likely_champion }
        : null,
      most_likely_final: snapshot.main_forecast.most_likely_final
        ? { ...snapshot.main_forecast.most_likely_final }
        : null,
    },
    matchday_predictions: snapshot.matchday_predictions.map((match) => {
      const actual =
        results.byId.get(String(match.match_id)) ??
        results.byPair.get(pairKey(match.team_a, match.team_b));
      const actualWinner = actual?.winner ?? null;
      return {
        ...match,
        actual_winner: actualWinner,
        actual_score: actual?.score ?? null,
        prediction_outcome: predictionOutcome(match.predicted_winner, actualWinner),
      };
    }),
  };
}

function teamMetadata(teamsPayload: unknown) {
  const teamsRoot = record(teamsPayload);
  const teamCodes: Record<string, string | null> = {};
  const currentTeamStatuses: Record<string, string> = {};
  for (const rawTeam of list(teamsRoot?.teams)) {
    const team = record(rawTeam);
    const name = text(team?.team);
    if (!team || !name) continue;
    teamCodes[name] = text(team.code) || null;
    currentTeamStatuses[name] = text(team.status, "unknown");
  }
  return { teamCodes, currentTeamStatuses };
}

export function buildPredictionHistoryDataset(
  manifestPayload: unknown,
  snapshotFiles: Record<string, unknown>,
  bracketPayload: unknown,
  teamsPayload: unknown,
): PredictionHistoryDataset {
  const manifest = record(manifestPayload);
  const entries = list(manifest?.snapshots);
  const results = completedResults(bracketPayload);
  const metadata = teamMetadata(teamsPayload);
  let skippedSnapshots = 0;

  const snapshots = entries.flatMap((rawEntry) => {
    const entry = record(rawEntry);
    const file = text(entry?.file);
    const parsed = file ? parseSnapshot(snapshotFiles[file]) : null;
    if (!parsed) {
      skippedSnapshots += 1;
      return [];
    }
    return [enrichSnapshot(parsed, results)];
  });

  snapshots.sort((left, right) => {
    const completed = (left.completed_matches ?? -1) - (right.completed_matches ?? -1);
    return completed || left.generated_at.localeCompare(right.generated_at);
  });

  const newestByDate = new Map<string, string>();
  for (const snapshot of snapshots) newestByDate.set(snapshot.display_date, snapshot.snapshot_id);
  const dateOptions: HistoryDateOption[] = [...newestByDate.entries()]
    .map(([displayDate, snapshotId]) => ({ displayDate, snapshotId }))
    .reverse();

  let correct = 0;
  let resolved = 0;
  let pending = 0;
  for (const snapshot of snapshots) {
    for (const match of snapshot.matchday_predictions) {
      if (match.prediction_outcome === "pending") pending += 1;
      else {
        resolved += 1;
        if (match.prediction_outcome === "correct") correct += 1;
      }
    }
  }

  return {
    status: snapshots.length ? "ready" : "empty",
    snapshots,
    dateOptions,
    latestSnapshotId: snapshots.at(-1)?.snapshot_id ?? null,
    skippedSnapshots,
    teamCodes: metadata.teamCodes,
    currentTeamStatuses: metadata.currentTeamStatuses,
    accuracy: { correct, resolved, pending },
  };
}

export function selectHistorySnapshot(
  dataset: PredictionHistoryDataset,
  snapshotId: string | null,
): HistorySelection {
  const selectedIndex = Math.max(
    0,
    dataset.snapshots.findIndex((snapshot) => snapshot.snapshot_id === snapshotId),
  );
  const selected = dataset.snapshots[selectedIndex] ?? null;
  const previous = selected
    ? dataset.snapshots
        .slice(0, selectedIndex)
        .reverse()
        .find((snapshot) => snapshot.display_date !== selected.display_date) ?? null
    : null;
  return {
    selected,
    previous,
    isLatest: Boolean(selected && selected.snapshot_id === dataset.latestSnapshotId),
  };
}
