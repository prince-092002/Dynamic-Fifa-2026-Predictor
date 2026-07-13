# Scenario Lab Version 1

## Purpose

Scenario Lab lets a visitor force outcomes for currently known unresolved matches and simulate the rest of the tournament in the browser. It is a hypothetical analysis tool, not a replacement for the official live forecast.

## Architecture and isolation

- Route: `website/app/scenario-lab/page.tsx`
- Feature code: `website/features/scenario-lab/`
- Execution: client-side TypeScript only
- Persistence: none
- Network/API calls: none
- Server writes: none
- Production model access: none

The server-rendered page reads the same immutable published JSON used by the rest of the static website and reduces it to a Scenario Lab snapshot. The client receives that snapshot and never writes it back. Visitor settings and results live only in React state for the current browser session.

Scenario Lab is not part of `refresh-portfolio`, the Python pipeline, GitHub Actions, Streamlit, provider diagnostics, or the official Monte Carlo simulator.

## Published inputs

- `public_data/latest_overview.json`: phase, forecast label, run ID, and snapshot metadata
- `public_data/knockout_bracket.json`: completed and unresolved bracket state
- `public_data/matchup_predictions.json`: published probabilities for currently known matchups
- `public_data/champion_forecast.json`: official champion comparison
- `public_data/finalist_forecast.json`: official finalist comparison
- `public_data/finalist_pairs.json`: official final-pair comparison
- `public_data/teams.json`: alive status, flags, and completed-tournament statistics

These files are read-only inputs. Scenario Lab does not alter their schemas or contents.

## Probability priority

1. A currently known matchup uses its published matchup-level advance probability. When the source is a published live XGBoost prediction, the interface says so.
2. No pairwise probability matrix or published Elo table currently exists.
3. A hypothetical future pairing uses a browser-only tournament-form rating built from already-published completed-match inputs: points per game and goal difference per game. The rating is converted to a pairwise probability using a standard logistic rating curve and is bounded to 5%-95%.

The tournament-form resolver is never labeled as XGBoost or as a fresh official prediction. Missing inputs fail safely instead of silently substituting invented probabilities.

## Simulation method

- Completed matches are locked to their published winners.
- Only unresolved matches are sampled.
- A visitor may let the resolver decide or force either team to advance in a currently known unresolved match.
- Winners occupy the next bracket slots in order, preserving the published knockout structure.
- The final two teams are counted as finalists and the sampled final winner is counted as champion.
- Aggregate champion probabilities sum to 100%, finalist probabilities to 200%, and final-pair probabilities to 100%.

The simulator uses a seeded Mulberry32 pseudo-random-number generator. Identical snapshot, selections, simulation count, and seed produce identical probability outputs. The supported counts are 1,000, 5,000, and 10,000, with 5,000 as the default.

## Files created

- `website/app/scenario-lab/page.tsx`
- `website/features/scenario-lab/types.ts`
- `website/features/scenario-lab/lib/adapter.ts`
- `website/features/scenario-lab/lib/prng.ts`
- `website/features/scenario-lab/lib/probability.ts`
- `website/features/scenario-lab/lib/simulation.ts`
- `website/features/scenario-lab/components/ScenarioLab.tsx`
- `website/features/scenario-lab/tests/simulation.test.ts`
- `website/tsconfig.scenario-tests.json`
- `docs/scenario_lab_v1.md`

Existing website files changed: navigation, read-only data getters/types, Scenario Lab styling, and package scripts. No production dependency was added.

## Testing

Run from `website/`:

```bash
npm run test:scenario
npm run typecheck
npm run lint
npm run build
```

The isolated suite covers loading, completed locks, model-decides behavior, both forced choices, multiple forces, downstream slots, eliminated-team exclusion, probability sums, reproducibility, immutability, reset, missing data, tournament completion, and 10,000-run performance.

## Known limitations

- Hypothetical future matchups cannot use XGBoost because no official prediction exists until participants are known.
- A published pairwise Elo matrix is unavailable, so hypothetical future pairings use the documented tournament-form resolver.
- Scenarios are not saved and disappear on refresh or navigation.
- Version 1 does not include strength sliders, arbitrary probability editing, accounts, custom brackets, storage, or social sharing.

## Removal

Remove the `/scenario-lab` route and `website/features/scenario-lab/`, delete the Scenario Lab navigation entry and CSS block, remove the Scenario Lab getter/type and test script/config, then delete this document. No production pipeline or official artifact needs to be changed or regenerated.

## Possible Version 2 extensions

Potential future work includes a separately published immutable pairwise strength matrix, shareable URL-encoded scenarios, richer sensitivity analysis, or an optional Web Worker if future simulations become materially larger. None are implemented in Version 1.

## Official versus scenario

The official forecast is generated by the production Python pipeline using live tournament data, the production model, and the official Monte Carlo simulator. A user scenario is generated locally from published inputs and visitor choices. It cannot update the official model, live bracket, public artifacts, repository, or deployment.
