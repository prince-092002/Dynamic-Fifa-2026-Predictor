import assert from "node:assert/strict";
import { performance } from "node:perf_hooks";
import test from "node:test";
import { buildScenarioSnapshot } from "../lib/adapter";
import {
  ScenarioValidationError,
  createDefaultScenarioState,
  simulateScenario,
  validateScenarioSnapshot,
} from "../lib/simulation";
import type { ScenarioSettings, ScenarioSnapshot, ScenarioSourcePayload } from "../types";

const active = ["Atlas", "Boreal", "Comet", "Dynamo"];
const eliminated = ["Echo", "Flare", "Globe", "Harbor"];

function sourcePayload(): ScenarioSourcePayload {
  const teams = [...active, ...eliminated].map((team, index) => ({
    team,
    slug: team.toLowerCase(),
    code: ["AR", "ES", "FR", "GB-ENG", "BE", "NO", "CH", "MA"][index],
    status: active.includes(team) ? "alive" : "eliminated",
    played: 6,
    wins: 6 - (index % 3),
    draws: index % 2,
    goal_difference: 12 - index,
  }));

  return {
    overview: {
      current_phase: "semifinal",
      forecast_mode: "true_live_forecast",
      public_label: "Official live forecast",
      provider: "test_provider",
      run_id: "snapshot-test",
      _meta: { generated_at: "2026-07-12T06:35:46Z" },
    },
    bracket: {
      current_phase: "semifinal",
      _meta: { generated_at: "2026-07-12T06:35:46Z", run_id: "snapshot-test" },
      rounds: [
        {
          stage: "Quarterfinal",
          matches: [
            completed(1, "Atlas", "Echo", "Atlas"),
            completed(2, "Boreal", "Flare", "Boreal"),
            completed(3, "Comet", "Globe", "Comet"),
            completed(4, "Dynamo", "Harbor", "Dynamo"),
          ],
        },
        {
          stage: "Semifinal",
          matches: [scheduled(5, "Atlas", "Boreal", 0.6), scheduled(6, "Comet", "Dynamo", 0.55)],
        },
        {
          stage: "Final",
          matches: [tbd(7)],
        },
      ],
    },
    teams,
    matchupPredictions: [
      prediction("Atlas", "Boreal", 0.6),
      prediction("Comet", "Dynamo", 0.55),
    ],
    championForecast: active.map((team) => ({ team, champion_probability: 0.25 })),
    finalistForecast: active.map((team) => ({ team, reach_final_probability: 0.5 })),
    finalPairs: [{ finalist_team_1: "Atlas", finalist_team_2: "Comet", probability: 0.25 }],
  };
}

function completed(fixtureId: number, teamA: string, teamB: string, winner: string) {
  return {
    fixture_id: fixtureId,
    stage: "Quarterfinal",
    date: "2026-07-10T19:00:00Z",
    state: "completed" as const,
    team_a: teamA,
    team_b: teamB,
    winner,
    source_label: "Completed real result",
  };
}

function scheduled(fixtureId: number, teamA: string, teamB: string, probabilityA: number) {
  return {
    fixture_id: fixtureId,
    stage: "Semifinal",
    date: "2026-07-14T19:00:00Z",
    state: "scheduled_known" as const,
    team_a: teamA,
    team_b: teamB,
    team_a_advance_probability: probabilityA,
    team_b_advance_probability: 1 - probabilityA,
    source_label: "Live XGBoost prediction",
  };
}

function tbd(fixtureId: number) {
  return {
    fixture_id: fixtureId,
    stage: "Final",
    date: "2026-07-19T19:00:00Z",
    state: "tbd" as const,
    team_a: null,
    team_b: null,
    source_label: "Unresolved bracket slot",
  };
}

function prediction(teamA: string, teamB: string, probabilityA: number) {
  return {
    stage: "Semifinal",
    team_a: teamA,
    team_b: teamB,
    team_a_advance_probability: probabilityA,
    team_b_advance_probability: 1 - probabilityA,
    source_label: "Live XGBoost prediction",
  };
}

function snapshot(): ScenarioSnapshot {
  return buildScenarioSnapshot(sourcePayload());
}

function settings(overrides: Partial<ScenarioSettings> = {}): ScenarioSettings {
  return {
    simulations: 1000,
    seed: 2026,
    choices: { "fixture-5": "model", "fixture-6": "model" },
    ...overrides,
  };
}

const sum = (values: Array<{ probability: number }>) =>
  values.reduce((total, item) => total + item.probability, 0);

test("loads the current unresolved bracket through the read-only adapter", () => {
  const value = snapshot();
  assert.equal(value.status, "ready");
  assert.deepEqual(value.knownUnresolvedMatchIds, ["fixture-5", "fixture-6"]);
  assert.equal(validateScenarioSnapshot(value).length, 0);
});

test("completed matches remain locked", () => {
  const result = simulateScenario(snapshot(), settings());
  assert.equal(result.completedMatchesLocked, 4);
  assert.equal(result.fixtureAdvancementProbabilities["fixture-1"].Atlas, 1);
  assert.equal(result.fixtureAdvancementProbabilities["fixture-1"].Echo ?? 0, 0);
});

test("model-decides simulation uses published matchup probabilities", () => {
  const result = simulateScenario(snapshot(), settings());
  assert.equal(result.probabilitySourceCounts.published_matchup, 2000);
  assert.equal(result.probabilitySourceCounts.published_tournament_form, 1000);
});

test("forcing Team A advances it in every run", () => {
  const result = simulateScenario(snapshot(), settings({ choices: { "fixture-5": "team_a", "fixture-6": "model" } }));
  assert.equal(result.fixtureAdvancementProbabilities["fixture-5"].Atlas, 1);
  assert.equal(result.fixtureAdvancementProbabilities["fixture-5"].Boreal ?? 0, 0);
});

test("forcing Team B advances it in every run", () => {
  const result = simulateScenario(snapshot(), settings({ choices: { "fixture-5": "team_b", "fixture-6": "model" } }));
  assert.equal(result.fixtureAdvancementProbabilities["fixture-5"].Boreal, 1);
  assert.equal(result.fixtureAdvancementProbabilities["fixture-5"].Atlas ?? 0, 0);
});

test("multiple forced outcomes are applied together", () => {
  const result = simulateScenario(snapshot(), settings({ choices: { "fixture-5": "team_a", "fixture-6": "team_b" } }));
  assert.equal(result.forcedOutcomeCount, 2);
  assert.equal(result.fixtureAdvancementProbabilities["fixture-5"].Atlas, 1);
  assert.equal(result.fixtureAdvancementProbabilities["fixture-6"].Dynamo, 1);
});

test("forced-out active teams remain visible at zero probability", () => {
  const result = simulateScenario(snapshot(), settings({ choices: { "fixture-5": "team_a", "fixture-6": "model" } }));
  assert.equal(result.championProbabilities.find((entry) => entry.team === "Boreal")?.probability, 0);
  assert.equal(result.finalistProbabilities.find((entry) => entry.team === "Boreal")?.probability, 0);
});

test("forced winners occupy the correct downstream final slots", () => {
  const result = simulateScenario(snapshot(), settings({ choices: { "fixture-5": "team_a", "fixture-6": "team_a" } }));
  assert.deepEqual(result.finalPairProbabilities, [{ teamA: "Atlas", teamB: "Comet", probability: 1 }]);
});

test("eliminated teams cannot return", () => {
  const result = simulateScenario(snapshot(), settings());
  for (const team of eliminated) {
    assert.equal(result.championProbabilities.find((entry) => entry.team === team), undefined);
    assert.equal(result.finalistProbabilities.find((entry) => entry.team === team), undefined);
  }
});

test("champion probabilities sum to 100 percent", () => {
  assert.ok(Math.abs(sum(simulateScenario(snapshot(), settings()).championProbabilities) - 1) < 1e-12);
});

test("finalist probabilities sum to 200 percent", () => {
  assert.ok(Math.abs(sum(simulateScenario(snapshot(), settings()).finalistProbabilities) - 2) < 1e-12);
});

test("final-pair probabilities sum to 100 percent", () => {
  assert.ok(Math.abs(sum(simulateScenario(snapshot(), settings()).finalPairProbabilities) - 1) < 1e-12);
});

test("identical seeds and inputs produce identical results", () => {
  assert.deepEqual(simulateScenario(snapshot(), settings()), simulateScenario(snapshot(), settings()));
});

test("different seeds can produce different samples", () => {
  assert.notDeepEqual(
    simulateScenario(snapshot(), settings({ seed: 7 })),
    simulateScenario(snapshot(), settings({ seed: 8 })),
  );
});

test("official snapshot input is never mutated", () => {
  const value = snapshot();
  const before = JSON.stringify(value);
  simulateScenario(value, settings());
  assert.equal(JSON.stringify(value), before);
});

test("reset restores model decisions, default count, and clears results", () => {
  const state = createDefaultScenarioState(snapshot());
  assert.equal(state.settings.simulations, 5000);
  assert.equal(state.settings.seed, 2026);
  assert.deepEqual(state.settings.choices, { "fixture-5": "model", "fixture-6": "model" });
  assert.equal(state.result, null);
});

test("empty or missing data fails safely", () => {
  const invalid = buildScenarioSnapshot({
    overview: null,
    bracket: null,
    teams: [],
    matchupPredictions: [],
    championForecast: [],
    finalistForecast: [],
    finalPairs: [],
  });
  assert.equal(invalid.status, "invalid");
  assert.throws(() => simulateScenario(invalid, settings()), ScenarioValidationError);
});

test("tournament-complete state returns the locked champion", () => {
  const value = snapshot();
  value.status = "complete";
  value.rounds[1].matches[0] = { ...value.rounds[1].matches[0], state: "completed", winner: "Atlas" };
  value.rounds[1].matches[1] = { ...value.rounds[1].matches[1], state: "completed", winner: "Comet" };
  value.rounds[2].matches[0] = {
    ...value.rounds[2].matches[0],
    state: "completed",
    teamA: "Atlas",
    teamB: "Comet",
    winner: "Atlas",
  };
  const result = simulateScenario(value, settings());
  assert.deepEqual(result.championProbabilities, [{ team: "Atlas", probability: 1 }]);
  assert.equal(sum(result.finalistProbabilities), 2);
});

test("10,000 simulations finish within a reasonable local runtime", () => {
  const started = performance.now();
  simulateScenario(snapshot(), settings({ simulations: 10000 }));
  assert.ok(performance.now() - started < 2000);
});

test("all returned probabilities stay within zero and one", () => {
  const result = simulateScenario(snapshot(), settings());
  for (const entry of [
    ...result.championProbabilities,
    ...result.finalistProbabilities,
    ...result.finalPairProbabilities,
  ]) {
    assert.ok(entry.probability >= 0 && entry.probability <= 1);
  }
});

test("the adapter copies published inputs instead of retaining mutable references", () => {
  const payload = sourcePayload();
  const value = buildScenarioSnapshot(payload);
  payload.teams[0].wins = 0;
  assert.notEqual(value.teams.Atlas.wins, 0);
});
