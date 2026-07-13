import { createSeededRandom, normalizeSeed } from "./prng";
import { resolveAdvanceProbability } from "./probability";
import type {
  FinalPairResult,
  ProbabilitySource,
  ScenarioChoice,
  ScenarioMatch,
  ScenarioSettings,
  ScenarioSimulationResult,
  ScenarioSnapshot,
  ScenarioUiState,
  TeamProbabilityResult,
} from "../types";

const SIMULATION_OPTIONS = new Set([1000, 5000, 10000]);

export class ScenarioValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ScenarioValidationError";
  }
}

export function createDefaultScenarioState(snapshot: ScenarioSnapshot): ScenarioUiState {
  return {
    settings: {
      simulations: 5000,
      seed: 2026,
      choices: Object.fromEntries(
        snapshot.knownUnresolvedMatchIds.map((matchId) => [matchId, "model" as ScenarioChoice]),
      ),
    },
    result: null,
  };
}

export function validateScenarioSnapshot(snapshot: ScenarioSnapshot): string[] {
  const errors: string[] = [];
  if (snapshot.status === "invalid") errors.push(snapshot.error ?? "Scenario snapshot is invalid.");
  if (!snapshot.rounds.length) errors.push("Tournament bracket is empty.");
  if (!Object.keys(snapshot.teams).length) errors.push("Published team inputs are empty.");

  for (const round of snapshot.rounds) {
    for (const match of round.matches) {
      if (match.state === "completed") {
        if (!match.winner) errors.push(`${match.stage} fixture ${match.fixtureId} has no locked winner.`);
        if (
          match.winner &&
          match.teamA &&
          match.teamB &&
          match.winner !== match.teamA &&
          match.winner !== match.teamB
        ) {
          errors.push(`${match.stage} fixture ${match.fixtureId} has an invalid locked winner.`);
        }
      }
    }
  }

  const finalRound = snapshot.rounds.at(-1);
  if (!finalRound || finalRound.matches.length !== 1) {
    errors.push("Bracket must end with exactly one final.");
  }
  return [...new Set(errors)];
}

function addCount(store: Map<string, number>, key: string, amount = 1) {
  store.set(key, (store.get(key) ?? 0) + amount);
}

function addFixtureCount(
  store: Map<string, Map<string, number>>,
  matchId: string,
  team: string,
) {
  if (!store.has(matchId)) store.set(matchId, new Map());
  addCount(store.get(matchId) as Map<string, number>, team);
}

function sortedProbabilities(
  counts: Map<string, number>,
  denominator: number,
  eligibleTeams: string[],
): TeamProbabilityResult[] {
  return eligibleTeams
    .map((team) => ({ team, probability: (counts.get(team) ?? 0) / denominator }))
    .sort((left, right) => right.probability - left.probability || left.team.localeCompare(right.team));
}

function pairKey(teamA: string, teamB: string) {
  return [teamA, teamB].sort((left, right) => left.localeCompare(right)).join("\u0000");
}

function chooseWinner(
  match: ScenarioMatch,
  teamA: string,
  teamB: string,
  snapshot: ScenarioSnapshot,
  choice: ScenarioChoice,
  random: () => number,
  sourceCounts: Record<ProbabilitySource, number>,
): string {
  if (choice === "team_a") return teamA;
  if (choice === "team_b") return teamB;

  const resolution = resolveAdvanceProbability(teamA, teamB, match, snapshot);
  sourceCounts[resolution.source] += 1;
  return random() < resolution.teamAProbability ? teamA : teamB;
}

function completedTournamentResult(
  snapshot: ScenarioSnapshot,
  settings: ScenarioSettings,
): ScenarioSimulationResult {
  const finalMatch = snapshot.rounds.at(-1)?.matches[0];
  if (!finalMatch?.winner || !finalMatch.teamA || !finalMatch.teamB) {
    throw new ScenarioValidationError("Completed tournament snapshot does not contain a valid final.");
  }
  const finalTeams = [finalMatch.teamA, finalMatch.teamB].sort((a, b) => a.localeCompare(b));
  return {
    simulations: settings.simulations,
    seed: normalizeSeed(settings.seed),
    forcedOutcomeCount: 0,
    championProbabilities: [{ team: finalMatch.winner, probability: 1 }],
    finalistProbabilities: finalTeams.map((team) => ({ team, probability: 1 })),
    finalPairProbabilities: [{ teamA: finalTeams[0], teamB: finalTeams[1], probability: 1 }],
    fixtureAdvancementProbabilities: { [finalMatch.id]: { [finalMatch.winner]: 1 } },
    probabilitySourceCounts: { published_matchup: 0, published_tournament_form: 0 },
    completedMatchesLocked: snapshot.rounds.flatMap((round) => round.matches).filter((m) => m.state === "completed").length,
  };
}

export function simulateScenario(
  snapshot: ScenarioSnapshot,
  settings: ScenarioSettings,
): ScenarioSimulationResult {
  const errors = validateScenarioSnapshot(snapshot);
  if (errors.length) throw new ScenarioValidationError(errors[0]);
  if (!SIMULATION_OPTIONS.has(settings.simulations)) {
    throw new ScenarioValidationError("Simulation count must be 1,000, 5,000, or 10,000.");
  }
  if (snapshot.status === "complete") return completedTournamentResult(snapshot, settings);

  const seed = normalizeSeed(settings.seed);
  const random = createSeededRandom(seed);
  const championCounts = new Map<string, number>();
  const finalistCounts = new Map<string, number>();
  const finalPairCounts = new Map<string, number>();
  const fixtureCounts = new Map<string, Map<string, number>>();
  const sourceCounts: Record<ProbabilitySource, number> = {
    published_matchup: 0,
    published_tournament_form: 0,
  };
  const completedMatchesLocked = snapshot.rounds
    .flatMap((round) => round.matches)
    .filter((match) => match.state === "completed").length;

  for (let run = 0; run < settings.simulations; run += 1) {
    let previousWinners: string[] = [];

    for (let roundIndex = 0; roundIndex < snapshot.rounds.length; roundIndex += 1) {
      const round = snapshot.rounds[roundIndex];
      const winners: string[] = [];

      for (let matchIndex = 0; matchIndex < round.matches.length; matchIndex += 1) {
        const match = round.matches[matchIndex];
        let teamA = match.teamA;
        let teamB = match.teamB;

        if ((!teamA || !teamB) && roundIndex > 0) {
          teamA = previousWinners[matchIndex * 2] ?? null;
          teamB = previousWinners[matchIndex * 2 + 1] ?? null;
        }
        if (!teamA || !teamB) {
          throw new ScenarioValidationError(`Unable to populate ${match.stage} fixture ${match.fixtureId}.`);
        }

        let winner: string;
        if (match.state === "completed") {
          winner = match.winner as string;
        } else {
          const choice = settings.choices[match.id] ?? "model";
          winner = chooseWinner(match, teamA, teamB, snapshot, choice, random, sourceCounts);
        }
        winners.push(winner);
        addFixtureCount(fixtureCounts, match.id, winner);

        if (roundIndex === snapshot.rounds.length - 1) {
          addCount(championCounts, winner);
          addCount(finalistCounts, teamA);
          addCount(finalistCounts, teamB);
          addCount(finalPairCounts, pairKey(teamA, teamB));
        }
      }
      previousWinners = winners;
    }
  }

  const finalPairProbabilities: FinalPairResult[] = [...finalPairCounts.entries()]
    .map(([key, count]) => {
      const [teamA, teamB] = key.split("\u0000");
      return { teamA, teamB, probability: count / settings.simulations };
    })
    .sort((left, right) =>
      right.probability - left.probability ||
      `${left.teamA} ${left.teamB}`.localeCompare(`${right.teamA} ${right.teamB}`),
    );

  const fixtureAdvancementProbabilities = Object.fromEntries(
    [...fixtureCounts.entries()].map(([matchId, counts]) => [
      matchId,
      Object.fromEntries(
        [...counts.entries()].map(([team, count]) => [team, count / settings.simulations]),
      ),
    ]),
  );

  return {
    simulations: settings.simulations,
    seed,
    forcedOutcomeCount: Object.values(settings.choices).filter((choice) => choice !== "model").length,
    championProbabilities: sortedProbabilities(championCounts, settings.simulations, snapshot.activeTeams),
    finalistProbabilities: sortedProbabilities(finalistCounts, settings.simulations, snapshot.activeTeams),
    finalPairProbabilities,
    fixtureAdvancementProbabilities,
    probabilitySourceCounts: sourceCounts,
    completedMatchesLocked,
  };
}
