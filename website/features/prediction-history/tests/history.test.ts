import assert from "node:assert/strict";
import test from "node:test";
import {
  buildPredictionHistoryDataset,
  historyDisplayDate,
  isConfirmedFinalSnapshot,
  selectHistorySnapshot,
} from "../lib/history";

function snapshot(
  id: string,
  generatedAt: string,
  completed: number,
  matches: Array<Record<string, unknown>>,
  championProbability = 0.4,
) {
  return {
    schema_version: "1.0",
    snapshot_id: id,
    generated_at: generatedAt,
    display_date: generatedAt.slice(0, 10),
    timezone: "UTC",
    tournament_phase: completed >= 101 ? "final" : "semifinal",
    completed_matches: completed,
    remaining_matches: 104 - completed,
    teams_alive: 4,
    teams_eliminated: 44,
    provider: "football_data_org",
    forecast_mode: "true_live_forecast",
    source_quality_score: 100,
    simulation_count: 10000,
    seed: 42,
    selected_model: "xgboost",
    run_id: `run-${id}`,
    record_class: "recovered_from_committed_output",
    provenance: { git_commit: id },
    main_forecast: {
      most_likely_champion: { team: "Alpha", probability: championProbability },
      second_most_likely_champion: { team: "Bravo", probability: 0.3 },
      champion_probabilities: [
        { team: "Alpha", probability: championProbability },
        { team: "Bravo", probability: 1 - championProbability },
      ],
      most_likely_final: {
        team_1: "Alpha",
        team_2: "Bravo",
        pair_key: "Alpha vs Bravo",
        probability: 0.55,
      },
      finalist_probabilities: [
        { team: "Alpha", probability: 0.7 },
        { team: "Bravo", probability: 0.6 },
      ],
      predicted_final_winner: null,
    },
    matchday_predictions: matches,
    state_hash: `hash-${id}`,
  };
}

function match(
  id: number,
  teamA: string,
  teamB: string,
  predictedWinner: string,
  probabilityA: number,
) {
  return {
    match_id: id,
    stage: "Semifinal",
    scheduled_at: "2026-07-14T19:00:00Z",
    team_a: teamA,
    team_b: teamB,
    team_a_win_probability: probabilityA,
    team_b_win_probability: 1 - probabilityA,
    predicted_winner: predictedWinner,
    prediction_method: "XGBoost",
    status_at_snapshot: "scheduled",
    actual_winner: null,
    actual_score: null,
    prediction_outcome: "pending",
  };
}

function fixtureData() {
  const files = {
    "snapshots/one.json": snapshot(
      "one",
      "2026-07-12T05:08:43Z",
      99,
      [match(1, "Alpha", "Bravo", "Alpha", 0.61), match(2, "Charlie", "Delta", "Delta", 0.42)],
      0.41,
    ),
    "snapshots/two.json": snapshot(
      "two",
      "2026-07-12T06:35:46Z",
      100,
      [match(1, "Alpha", "Bravo", "Alpha", 0.61), match(3, "Echo", "Foxtrot", "Echo", 0.7)],
      0.44,
    ),
    "snapshots/three.json": snapshot(
      "three",
      "2026-07-14T21:07:09Z",
      101,
      [match(4, "Golf", "Hotel", "Golf", 0.65)],
      0.52,
    ),
  };
  const manifest = {
    schema_version: "1.0",
    snapshots: Object.entries(files).map(([file, value]) => ({
      file,
      snapshot_id: value.snapshot_id,
      generated_at: value.generated_at,
      completed_matches: value.completed_matches,
    })),
  };
  const bracket = {
    rounds: [
      {
        stage: "Semifinal",
        matches: [
          { fixture_id: 1, state: "completed", team_a: "Alpha", team_b: "Bravo", winner: "Alpha", score: "2-1" },
          { fixture_id: 2, state: "completed", team_a: "Charlie", team_b: "Delta", winner: "Charlie", score: "1-0" },
          { fixture_id: 3, state: "scheduled_known", team_a: "Echo", team_b: "Foxtrot" },
          { fixture_id: 4, state: "scheduled_known", team_a: "Golf", team_b: "Hotel" },
        ],
      },
    ],
  };
  const teams = {
    teams: [
      { team: "Alpha", code: "AR", status: "alive" },
      { team: "Bravo", code: "ES", status: "eliminated" },
    ],
  };
  return { files, manifest, bracket, teams };
}

test("loads genuine manifest snapshots in meaningful state order", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(dataset.status, "ready");
  assert.deepEqual(dataset.snapshots.map((entry) => entry.snapshot_id), ["one", "two", "three"]);
});

test("selects the latest genuine snapshot", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(dataset.latestSnapshotId, "three");
  assert.equal(selectHistorySnapshot(dataset, dataset.latestSnapshotId).selected?.completed_matches, 101);
});

test("selects the nearest previous meaningful snapshot", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(selectHistorySnapshot(dataset, "three").previous?.snapshot_id, "two");
});

test("previous matchday skips an earlier snapshot from the selected calendar date", () => {
  const value = fixtureData();
  const files = value.files as Record<string, ReturnType<typeof snapshot>>;
  files["snapshots/four.json"] = snapshot(
    "four",
    "2026-07-15T23:15:25Z",
    102,
    [match(5, "Alpha", "Bravo", "Alpha", 0.52)],
    0.52,
  );
  files["snapshots/five.json"] = snapshot(
    "five",
    "2026-07-16T00:15:25Z",
    102,
    [match(5, "Alpha", "Bravo", "Alpha", 0.52)],
    0.52,
  );
  value.manifest.snapshots.push(
    {
      file: "snapshots/four.json",
      snapshot_id: "four",
      generated_at: "2026-07-15T23:15:25Z",
      completed_matches: 102,
    },
    {
      file: "snapshots/five.json",
      snapshot_id: "five",
      generated_at: "2026-07-16T00:15:25Z",
      completed_matches: 102,
    },
  );

  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  const selection = selectHistorySnapshot(dataset, "five");

  assert.equal(selection.selected?.display_date, "2026-07-15");
  assert.equal(selection.previous?.snapshot_id, "three");
  assert.equal(selection.previous?.display_date, "2026-07-14");
});

test("date navigation uses the newest snapshot when a date has multiple updates", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.deepEqual(dataset.dateOptions, [
    { displayDate: "2026-07-14", snapshotId: "three" },
    { displayDate: "2026-07-12", snapshotId: "two" },
  ]);
});

test("uses the Chicago calendar date when a UTC run crosses midnight", () => {
  assert.equal(historyDisplayDate("2026-07-16T00:15:25Z"), "2026-07-15");

  const value = fixtureData();
  value.files["snapshots/three.json"].generated_at = "2026-07-16T00:15:25Z";
  value.files["snapshots/three.json"].display_date = "2026-07-16";
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);

  assert.equal(dataset.snapshots.at(-1)?.display_date, "2026-07-15");
  assert.equal(dataset.dateOptions[0].displayDate, "2026-07-15");
});

test("renders multiple same-day match predictions", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(dataset.snapshots.find((entry) => entry.snapshot_id === "two")?.matchday_predictions.length, 2);
});

test("historical probabilities remain exactly unchanged", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  const loaded = dataset.snapshots.find((entry) => entry.snapshot_id === "one");
  assert.equal(loaded?.main_forecast.most_likely_champion?.probability, 0.41);
  assert.equal(loaded?.matchday_predictions[0].team_a_win_probability, 0.61);
});

test("actual result enrichment marks a correct prediction", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  const prediction = dataset.snapshots[0].matchday_predictions[0];
  assert.equal(prediction.actual_winner, "Alpha");
  assert.equal(prediction.actual_score, "2-1");
  assert.equal(prediction.prediction_outcome, "correct");
});

test("actual result enrichment marks an incorrect prediction", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  const prediction = dataset.snapshots[0].matchday_predictions[1];
  assert.equal(prediction.actual_winner, "Charlie");
  assert.equal(prediction.prediction_outcome, "incorrect");
});

test("unresolved matches remain pending", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  const prediction = dataset.snapshots[1].matchday_predictions[1];
  assert.equal(prediction.actual_winner, null);
  assert.equal(prediction.prediction_outcome, "pending");
});

test("historical accuracy is calculated dynamically", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.deepEqual(dataset.accuracy, { correct: 2, resolved: 3, pending: 2 });
});

test("empty history fails gracefully", () => {
  const dataset = buildPredictionHistoryDataset({ snapshots: [] }, {}, {}, {});
  assert.equal(dataset.status, "empty");
  assert.equal(dataset.latestSnapshotId, null);
});

test("one-snapshot history has no previous update", () => {
  const value = fixtureData();
  const manifest = { snapshots: [value.manifest.snapshots[0]] };
  const dataset = buildPredictionHistoryDataset(manifest, value.files, value.bracket, value.teams);
  assert.equal(selectHistorySnapshot(dataset, dataset.latestSnapshotId).previous, null);
});

test("a malformed snapshot is skipped without crashing", () => {
  const value = fixtureData();
  value.files["snapshots/two.json"] = { malformed: true } as never;
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(dataset.status, "ready");
  assert.equal(dataset.skippedSnapshots, 1);
  assert.equal(dataset.snapshots.length, 2);
});

test("source manifest and snapshot objects are not mutated", () => {
  const value = fixtureData();
  const before = JSON.stringify(value);
  buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(JSON.stringify(value), before);
});

test("team flags and current statuses come from published website data", () => {
  const value = fixtureData();
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(dataset.teamCodes.Alpha, "AR");
  assert.equal(dataset.currentTeamStatuses.Bravo, "eliminated");
});

test("confirmed-final semantics require a final-stage snapshot with the official final matchup", () => {
  const value = fixtureData();
  const raw = value.files["snapshots/three.json"];
  raw.main_forecast.most_likely_final.probability = 1;
  raw.matchday_predictions = [{ ...match(5, "Alpha", "Bravo", "Alpha", 0.52), stage: "Final" }];
  const dataset = buildPredictionHistoryDataset(value.manifest, value.files, value.bracket, value.teams);
  assert.equal(isConfirmedFinalSnapshot(dataset.snapshots.at(-1)!), true);
  assert.equal(isConfirmedFinalSnapshot(dataset.snapshots[0]), false);
});
