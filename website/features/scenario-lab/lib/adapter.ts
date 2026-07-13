import type {
  OfficialTeamProbability,
  ScenarioSnapshot,
  ScenarioSourcePayload,
} from "../types";

function createInvalidSnapshot(error: string): ScenarioSnapshot {
  return {
    status: "invalid",
    error,
    snapshotId: "unavailable",
    generatedAt: null,
    currentPhase: "unknown",
    forecastMode: "unknown",
    officialLabel: "Official forecast unavailable",
    provider: "unknown",
    rounds: [],
    teams: {},
    activeTeams: [],
    knownUnresolvedMatchIds: [],
    publishedMatchups: [],
    officialProbabilities: [],
    officialFinalPairs: [],
  };
}

export function buildScenarioSnapshot(payload: ScenarioSourcePayload): ScenarioSnapshot {
  if (!payload.overview || !payload.bracket?.rounds?.length || !payload.teams.length) {
    return createInvalidSnapshot("Scenario Lab data is temporarily unavailable.");
  }

  const teams = Object.fromEntries(
    payload.teams.map((team) => [
      team.team,
      {
        name: team.team,
        slug: team.slug,
        code: team.code,
        status: team.status,
        played: team.played,
        wins: team.wins,
        draws: team.draws,
        goalDifference: team.goal_difference,
      },
    ]),
  );

  const publishedMatchups = payload.matchupPredictions
    .filter(
      (match) =>
        match.team_a &&
        match.team_b &&
        match.team_a_advance_probability !== null &&
        match.team_b_advance_probability !== null,
    )
    .map((match) => ({
      stage: match.stage,
      teamA: match.team_a,
      teamB: match.team_b,
      teamAAdvanceProbability: match.team_a_advance_probability as number,
      teamBAdvanceProbability: match.team_b_advance_probability as number,
      sourceLabel: match.source_label,
    }));

  const rounds = payload.bracket.rounds.map((round) => ({
    stage: round.stage,
    matches: round.matches.map((match) => {
      const published = publishedMatchups.find(
        (item) => item.teamA === match.team_a && item.teamB === match.team_b,
      );
      return {
        id: `fixture-${match.fixture_id}`,
        fixtureId: match.fixture_id,
        stage: match.stage,
        date: match.date,
        state: match.state,
        teamA: match.team_a,
        teamB: match.team_b,
        winner: match.winner ?? null,
        teamAAdvanceProbability:
          match.team_a_advance_probability ?? published?.teamAAdvanceProbability ?? null,
        teamBAdvanceProbability:
          match.team_b_advance_probability ?? published?.teamBAdvanceProbability ?? null,
        probabilitySource: published?.sourceLabel ?? match.source_label ?? null,
      };
    }),
  }));

  const finalistByTeam = new Map(
    payload.finalistForecast.map((entry) => [entry.team, entry.reach_final_probability]),
  );
  const officialProbabilities: OfficialTeamProbability[] = payload.championForecast.map((entry) => ({
    team: entry.team,
    championProbability: entry.champion_probability,
    finalistProbability: finalistByTeam.get(entry.team) ?? 0,
  }));

  const knownUnresolvedMatchIds = rounds
    .flatMap((round) => round.matches)
    .filter((match) => match.state !== "completed" && match.teamA && match.teamB)
    .map((match) => match.id);

  const finalRound = rounds.at(-1);
  const finalMatch = finalRound?.matches[0];
  const tournamentComplete = Boolean(finalMatch?.state === "completed" && finalMatch.winner);
  const activeTeams = payload.teams
    .filter((team) => team.status === "alive" || team.status === "champion")
    .map((team) => team.team);

  if (!tournamentComplete && knownUnresolvedMatchIds.length === 0) {
    return createInvalidSnapshot("The remaining bracket does not contain a known matchup to simulate.");
  }

  return {
    status: tournamentComplete ? "complete" : "ready",
    error: null,
    snapshotId: payload.overview.run_id ?? payload.bracket._meta?.run_id ?? "published-snapshot",
    generatedAt:
      payload.bracket._meta?.generated_at ?? payload.overview._meta?.generated_at ?? null,
    currentPhase: payload.overview.current_phase ?? payload.bracket.current_phase,
    forecastMode: payload.overview.forecast_mode ?? "unknown",
    officialLabel: payload.overview.public_label ?? "Official live forecast",
    provider: payload.overview.provider,
    rounds,
    teams,
    activeTeams,
    knownUnresolvedMatchIds,
    publishedMatchups,
    officialProbabilities,
    officialFinalPairs: payload.finalPairs.map((pair) => ({
      teamA: pair.finalist_team_1,
      teamB: pair.finalist_team_2,
      probability: pair.probability,
    })),
  };
}
