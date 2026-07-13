import type {
  ProbabilityResolution,
  ScenarioMatch,
  ScenarioSnapshot,
  ScenarioTeam,
} from "../types";

const clamp = (value: number, low: number, high: number) =>
  Math.min(high, Math.max(low, value));

function samePair(teamA: string, teamB: string, left: string, right: string) {
  return teamA === left && teamB === right;
}

function validProbability(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}

function tournamentFormRating(team: ScenarioTeam): number {
  if (team.played <= 0) {
    throw new Error(`Published tournament-form data is unavailable for ${team.name}.`);
  }
  const pointsPerGame = (team.wins * 3 + team.draws) / team.played;
  const goalDifferencePerGame = team.goalDifference / team.played;
  return 1500 + pointsPerGame * 100 + goalDifferencePerGame * 35;
}

export function resolveAdvanceProbability(
  teamA: string,
  teamB: string,
  match: ScenarioMatch,
  snapshot: ScenarioSnapshot,
): ProbabilityResolution {
  if (
    match.teamA === teamA &&
    match.teamB === teamB &&
    validProbability(match.teamAAdvanceProbability)
  ) {
    return { teamAProbability: match.teamAAdvanceProbability, source: "published_matchup" };
  }

  for (const published of snapshot.publishedMatchups) {
    if (samePair(teamA, teamB, published.teamA, published.teamB)) {
      return { teamAProbability: published.teamAAdvanceProbability, source: "published_matchup" };
    }
    if (samePair(teamA, teamB, published.teamB, published.teamA)) {
      return { teamAProbability: published.teamBAdvanceProbability, source: "published_matchup" };
    }
  }

  const left = snapshot.teams[teamA];
  const right = snapshot.teams[teamB];
  if (!left || !right) {
    throw new Error(`Published team-strength inputs are unavailable for ${teamA} vs ${teamB}.`);
  }

  const ratingDifference = tournamentFormRating(left) - tournamentFormRating(right);
  const probability = 1 / (1 + 10 ** (-ratingDifference / 400));
  return {
    teamAProbability: clamp(probability, 0.05, 0.95),
    source: "published_tournament_form",
  };
}
