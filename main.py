"""Command-line interface for the FIFA 2026 data foundation."""

import argparse
import sys

from src.cleaning.build_master_dataset import build_matches_master
from src.cleaning.clean_matches import run_all_match_cleaners
from src.cleaning.clean_player_stats import clean_manual_player_stats
from src.cleaning.clean_team_stats import clean_manual_team_ratings, clean_manual_team_stats
from src.cleaning.standardize_team_names import initialize_team_name_map
from src.config import ensure_project_directories
from src.logger import get_logger
from src.utils.files import initialize_metadata_files
from src.validation.validate_data import run_all_validations

logger = get_logger(__name__)


def initialize_project_files() -> None:
    ensure_project_directories()
    initialize_metadata_files()
    initialize_team_name_map()


def run_clean() -> None:
    initialize_project_files()
    outputs = run_all_match_cleaners()
    outputs.extend([clean_manual_team_ratings(), clean_manual_team_stats(), clean_manual_player_stats()])
    print("Cleaned data outputs:")
    for output in outputs:
        print(f"  - {output}")


def run_fetch(source: str) -> None:
    initialize_project_files()
    if source == "all":
        from src.fetch.fetch_all import fetch_all_sources

        result = fetch_all_sources()
    elif source == "kaggle":
        from src.fetch.fetch_kaggle import (
            fetch_international_results,
            fetch_world_cup_2026_schedule,
            fetch_world_cup_historical,
        )

        result = [
            fetch_international_results(),
            fetch_world_cup_historical(),
            fetch_world_cup_2026_schedule(),
        ]
    elif source == "elo":
        from src.fetch.fetch_elo import fetch_world_football_elo

        result = fetch_world_football_elo()
    elif source == "fbref":
        from src.fetch.fetch_fbref import fetch_fbref_world_cup_2026_all_stats

        result = fetch_fbref_world_cup_2026_all_stats()
    elif source == "fifa":
        from src.fetch.fetch_fifa import clean_fifa_matches, fetch_fifa_data_centre_matches

        result = [fetch_fifa_data_centre_matches(), clean_fifa_matches()]
    elif source == "api-football":
        from src.fetch.fetch_api_football import (
            fetch_api_football_fixtures_2026,
            fetch_api_football_results_2026,
            fetch_api_football_standings_2026,
            fetch_api_football_team_stats_2026,
            fetch_api_football_teams_2026,
        )

        result = [
            fetch_api_football_fixtures_2026(),
            fetch_api_football_results_2026(),
            fetch_api_football_teams_2026(),
            fetch_api_football_standings_2026(),
            fetch_api_football_team_stats_2026(),
        ]
    if source != "all":
        print(result)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dynamic FIFA 2026 data pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch raw data from configured sources")
    fetch_parser.add_argument(
        "--source",
        choices=["all", "kaggle", "elo", "fbref", "fifa", "api-football"],
        default="all",
        help="Source to fetch",
    )

    subparsers.add_parser("clean", help="Clean available raw/manual data")
    subparsers.add_parser("validate", help="Validate processed CSV outputs")
    subparsers.add_parser("build-master", help="Build data/processed/matches_master.csv")
    subparsers.add_parser("init", help="Create folders, metadata, and manual templates")
    subparsers.add_parser("check-env", help="Check credentials, manual fallbacks, and processed row readiness")

    load_parser = subparsers.add_parser("load-real-data", help="Load real data from APIs, Kaggle, and manual fallbacks")
    load_parser.add_argument(
        "--prefer",
        choices=["api", "manual"],
        default="api",
        help="Prefer online/API sources or manual files first",
    )
    load_parser.add_argument("--skip-api", action="store_true", help="Skip API-Football loading")
    load_parser.add_argument("--skip-kaggle", action="store_true", help="Skip Kaggle loading")
    load_parser.add_argument("--skip-fbref", action="store_true", help="Skip FBref loading")
    load_parser.add_argument("--skip-elo", action="store_true", help="Skip World Football Elo loading")
    load_parser.add_argument("--debug", action="store_true", help="Write extra source inspection reports without printing secrets")

    subparsers.add_parser("diagnose-api-football", help="Check API-Football authentication and quota")
    subparsers.add_parser("diagnose-kaggle", help="Check Kaggle authentication and dataset reachability")
    subparsers.add_parser("validate-manual-data", help="Validate manual fallback CSV files")
    subparsers.add_parser("data-summary", help="Summarize processed CSV row counts")
    subparsers.add_parser("ready-for-features", help="Check whether feature engineering can start")
    subparsers.add_parser("feature-data-quality", help="Run feature-stage duplicate and TBD fixture cleanup")
    subparsers.add_parser("build-features", help="Build model-ready feature datasets without training a model")
    subparsers.add_parser("validate-features", help="Validate feature datasets and run leakage checks")
    subparsers.add_parser("feature-summary", help="Print and save a feature dataset summary")
    subparsers.add_parser("modeling-data-summary", help="Summarize modeling training and fixture data")
    subparsers.add_parser("train-models", help="Run the full modeling pipeline")
    subparsers.add_parser("evaluate-models", help="Print saved model comparison metrics")
    subparsers.add_parser("predict-fixtures", help="Generate FIFA 2026 fixture predictions from the selected model")
    subparsers.add_parser("modeling-summary", help="Print and save modeling phase summary")
    subparsers.add_parser("simulation-input-summary", help="Summarize simulation inputs")
    simulation_parser = subparsers.add_parser("run-simulation", help="Run Monte Carlo tournament simulation")
    simulation_parser.add_argument("--mode", choices=["auto", "partial", "full-bracket"], default="auto", help="Simulation mode")
    simulation_parser.add_argument("--n-simulations", type=int, default=10000, help="Number of simulations to run")
    simulation_parser.add_argument("--seed", type=int, default=42, help="Random seed")
    subparsers.add_parser("validate-simulation", help="Validate simulation inputs and outputs")
    subparsers.add_parser("simulation-summary", help="Print and save simulation summary")
    subparsers.add_parser("inspect-bracket", help="Create bracket source and mapping reports")
    subparsers.add_parser("validate-bracket", help="Validate bracket mapping files")
    subparsers.add_parser("bracket-summary", help="Print bracket mapping status")
    subparsers.add_parser("champion-summary", help="Print champion simulation summary")
    subparsers.add_parser("fetch-live-state", help="Fetch and normalize live FIFA/API-Football state")
    subparsers.add_parser("build-live-state", help="Build current live tournament state")
    live_parser = subparsers.add_parser("run-live-forecast", help="Run live finalist and champion forecast")
    live_parser.add_argument("--n-simulations", type=int, default=10000, help="Number of simulations to run")
    live_parser.add_argument("--seed", type=int, default=42, help="Random seed")
    live_parser.add_argument("--allow-fallback-forecast", action="store_true", help="Explicitly allow fallback-only pre-tournament forecast output")
    live_parser.add_argument("--skip-live-matchup-predictions", action="store_true", help="Skip regenerating live knockout model predictions before simulating")
    subparsers.add_parser("live-forecast-summary", help="Print live finalist forecast summary")
    subparsers.add_parser("identify-live-knockout-matchups", help="List unplayed knockout matches with both teams known")
    subparsers.add_parser("build-live-knockout-features", help="Build model features for resolved live knockout matchups")
    subparsers.add_parser("predict-live-knockout", help="Predict resolved live knockout matchups with the selected model")
    subparsers.add_parser("live-knockout-prediction-summary", help="Report and validate live knockout matchup predictions")
    subparsers.add_parser("validate-live-feature-equivalence", help="Prove the fast live feature path matches the original Phase 3 path")
    subparsers.add_parser("validate-live-matchup-flow", help="Integration check: newly resolved matchups flow to live model predictions (sandboxed)")
    subparsers.add_parser("build-public-exports", help="Build public-safe JSON exports for the website and dashboard")
    subparsers.add_parser("validate-public-exports", help="Validate public JSON exports (website data contract)")
    subparsers.add_parser("validate-dashboard", help="Validate dashboard inputs and public exports")
    subparsers.add_parser("validate-deployment-readiness", help="Check local deployment readiness (exports, dashboard, secrets, dependencies)")
    subparsers.add_parser("validate-live-forecast", help="Validate live finalist forecast outputs")
    subparsers.add_parser("diagnose-live-api", help="Deeply diagnose API-Football live FIFA 2026 access")
    subparsers.add_parser("diagnose-football-data-org", help="Diagnose football-data.org World Cup 2026 access")
    subparsers.add_parser("fetch-football-data-org", help="Fetch football-data.org raw World Cup 2026 data")
    subparsers.add_parser("normalize-football-data-org", help="Normalize football-data.org World Cup 2026 data")
    subparsers.add_parser("diagnose-live-providers", help="Diagnose all configured live data providers")
    subparsers.add_parser("select-live-provider", help="Select best available live data provider")
    subparsers.add_parser("verify-live-sources", help="Run live source verification and quality gate")
    subparsers.add_parser("live-quality-gate", help="Print live forecast quality gate")
    subparsers.add_parser("live-source-summary", help="Print live source verification summary")

    update_parser = subparsers.add_parser("update", help="Run automatic refresh workflow")
    update_parser.add_argument(
        "--mode",
        choices=["matchday", "completed-match"],
        default="matchday",
        help="Refresh mode to run",
    )
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Force a full refresh even if no new completed match is detected",
    )
    update_parser.add_argument("--run-live-forecast", action="store_true", help="Run live finalist forecast after matchday update")
    update_parser.add_argument("--n-simulations", type=int, default=10000, help="Live forecast simulation count")
    update_parser.add_argument("--no-retrain", action="store_true", help="Use existing model/predictions and fall back to Elo where needed")
    update_parser.add_argument("--allow-fallback-forecast", action="store_true", help="Explicitly allow fallback-only live forecast during update")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            initialize_project_files()
            print("Project folders, metadata, manual templates, and team-name map are ready.")
        elif args.command == "fetch":
            run_fetch(args.source)
        elif args.command == "clean":
            run_clean()
        elif args.command == "validate":
            report = run_all_validations()
            print(f"Validation report saved to {report}")
        elif args.command == "build-master":
            output = build_matches_master()
            print(f"Master dataset saved to {output}")
        elif args.command == "check-env":
            from src.loading.env_check import check_environment, print_environment_check

            result = check_environment(create_missing_env=True)
            print_environment_check(result)
        elif args.command == "diagnose-api-football":
            from src.fetch.fetch_api_football import diagnose_api_football

            result = diagnose_api_football()
            print(f"API-Football diagnostic saved to {result['report']}")
        elif args.command == "diagnose-kaggle":
            from src.fetch.fetch_kaggle import diagnose_kaggle

            result = diagnose_kaggle()
            print(f"Kaggle diagnostic saved to {result['report']}")
        elif args.command == "validate-manual-data":
            from src.loading.data_health import write_manual_data_validation

            report = write_manual_data_validation(print_table=True)
            print(f"Manual data validation saved to {report}")
        elif args.command == "data-summary":
            from src.loading.data_health import write_data_summary

            result = write_data_summary(print_table=True)
            print(f"Data summary saved to {result['md']} and {result['csv']}")
        elif args.command == "ready-for-features":
            from src.loading.data_health import write_feature_readiness_gate

            result = write_feature_readiness_gate(print_result=True)
            print(f"Feature readiness report saved to {result['report']}")
        elif args.command == "feature-data-quality":
            from src.features.data_quality import run_feature_data_quality_checks

            result = run_feature_data_quality_checks()
            print(f"Feature data quality summary saved to {result['summary']}")
        elif args.command == "build-features":
            from src.features.feature_builder import build_all_features
            from src.features.feature_reports import generate_feature_build_summary, generate_feature_dictionary
            from src.features.feature_validation import run_feature_validation
            from src.features.leakage_checks import run_leakage_checks

            build_result = build_all_features()
            validation = run_feature_validation()
            leakage = run_leakage_checks()
            dictionary = generate_feature_dictionary()
            summary = generate_feature_build_summary(validation["status"], leakage["status"])
            print("Feature build completed.")
            print(f"  training rows: {build_result['training_rows']}")
            print(f"  fixture rows: {build_result['fixture_rows']}")
            print(f"  feature dictionary: {dictionary}")
            print(f"  build summary: {summary}")
        elif args.command == "validate-features":
            from src.features.feature_validation import run_feature_validation
            from src.features.leakage_checks import run_leakage_checks

            validation = run_feature_validation()
            leakage = run_leakage_checks()
            print(f"Feature validation status: {validation['status']}")
            print(f"Leakage check status: {leakage['status']}")
        elif args.command == "feature-summary":
            from src.features.feature_reports import write_feature_summary

            report = write_feature_summary()
            print(f"Feature summary saved to {report}")
        elif args.command == "modeling-data-summary":
            from src.modeling.data_loader import load_fixture_features, load_training_dataset, summarize_modeling_data

            training = load_training_dataset()
            fixtures, _ = load_fixture_features()
            report = summarize_modeling_data(training, fixtures)
            print(f"Modeling data summary saved to {report}")
        elif args.command == "train-models":
            from src.modeling.model_pipeline import run_modeling_pipeline

            result = run_modeling_pipeline()
            print("Modeling pipeline completed.")
            print(f"  selected model: {result['selected_model']}")
            print(f"  validation log loss: {result['validation_log_loss']:.4f}")
            print(f"  test log loss: {result['test_log_loss']:.4f}")
            print(f"  predictions: {result['fixture_predictions_path']}")
        elif args.command == "evaluate-models":
            import pandas as pd
            from src.modeling.model_config import MODELING_REPORT_DIR

            path = MODELING_REPORT_DIR / "model_metrics.csv"
            if not path.exists():
                print("No saved model metrics found. Run `python main.py train-models` first.")
            else:
                df = pd.read_csv(path)
                print(df[["model", "split", "accuracy", "macro_f1", "log_loss", "brier_score"]].to_string(index=False))
        elif args.command == "predict-fixtures":
            from src.modeling.predict_fixtures import predict_fixtures

            result = predict_fixtures()
            print(f"Fixture predictions saved to {result['predictions']}")
            print(f"Predicted rows: {result['predicted_rows']}")
        elif args.command == "modeling-summary":
            from src.modeling.model_reports import write_modeling_phase_summary

            report = write_modeling_phase_summary()
            print(f"Modeling summary saved to {report}")
        elif args.command == "simulation-input-summary":
            from src.simulation.data_loader import load_simulation_inputs
            from src.simulation.tournament_structure import inspect_tournament_structure

            inputs = load_simulation_inputs()
            structure = inspect_tournament_structure(inputs["predictions"])
            print(f"Simulation input summary saved to {inputs['report']}")
            print(f"Tournament structure report saved to {structure['report']}")
        elif args.command == "run-simulation":
            from src.simulation.simulation_pipeline import run_simulation_pipeline

            result = run_simulation_pipeline(n_simulations=args.n_simulations, seed=args.seed, mode=args.mode)
            print("Simulation completed.")
            print(f"  status: {result['status']}")
            print(f"  mode: {result['mode']}")
            print(f"  simulations: {result['n_simulations']}")
            print(f"  full champion simulation possible: {result['full_champion_simulation_possible']}")
            print(f"  team advancement: {result['team_advancement_path']}")
            print(f"  champion probabilities: {result['champion_probabilities_path']}")
        elif args.command == "validate-simulation":
            import pandas as pd
            from src.simulation.data_loader import load_simulation_inputs
            from src.simulation.simulation_config import SIMULATION_OUTPUT_DIR
            from src.simulation.simulation_validation import validate_simulation

            advancement_path = SIMULATION_OUTPUT_DIR / "team_advancement_probabilities.csv"
            champion_path = SIMULATION_OUTPUT_DIR / "champion_probabilities.csv"
            completion_path = SIMULATION_OUTPUT_DIR / "bracket_completion_summary.csv"
            aggregate = {"advancement_df": pd.read_csv(advancement_path)} if advancement_path.exists() else None
            if aggregate is not None and champion_path.exists():
                aggregate["champion_df"] = pd.read_csv(champion_path)
            completion = pd.read_csv(completion_path) if completion_path.exists() else pd.DataFrame()
            n_simulations = int(aggregate["advancement_df"]["simulations"].max()) if aggregate and "simulations" in aggregate["advancement_df"] else 1
            full_possible = bool(not completion.empty and float(completion.iloc[0].get("full_bracket_completed_rate", 0)) >= 0.999)
            result = validate_simulation(inputs=load_simulation_inputs(), aggregate=aggregate, n_simulations=n_simulations, full_champion_possible=full_possible)
            print(f"Simulation validation status: {result['status']}")
            print(f"Simulation validation report saved to {result['report']}")
        elif args.command == "simulation-summary":
            from src.simulation.simulation_reports import write_simulation_summary_printable

            result = {"n_simulations": "see latest monte_carlo_summary.md", "full_champion_simulation_possible": False}
            report = write_simulation_summary_printable(result)
            print(f"Simulation summary saved to {report}")
        elif args.command == "inspect-bracket":
            from src.simulation.bracket_mapping import create_default_bracket_files

            result = create_default_bracket_files(False)
            print(f"Bracket slots: {result['slots']}")
            print(f"Round progression: {result['progression']}")
            print(f"Source report: {result['source_report']}")
        elif args.command == "validate-bracket":
            from src.simulation.bracket_validation import validate_bracket_mapping

            result = validate_bracket_mapping()
            print(f"Bracket validation status: {result['status']}")
            print(f"Bracket validation report saved to {result['report']}")
        elif args.command == "bracket-summary":
            from src.simulation.bracket_mapping import load_bracket_slots, load_round_progression
            from src.simulation.bracket_config import BRACKET_SLOTS_PATH, ROUND_PROGRESSION_PATH

            slots = load_bracket_slots()
            progression = load_round_progression()
            print("Bracket mapping status: fallback_template")
            print(f"Round of 32 slots: {len(slots)}")
            print(f"Round of 32 matches: {slots['match_slot'].nunique()}")
            print(f"Progression rows: {len(progression)}")
            print(f"Slots file: {BRACKET_SLOTS_PATH}")
            print(f"Progression file: {ROUND_PROGRESSION_PATH}")
        elif args.command == "champion-summary":
            import pandas as pd
            from src.simulation.simulation_config import SIMULATION_OUTPUT_DIR
            from src.simulation.bracket_config import BRACKET_REPORT_DIR

            champion_path = SIMULATION_OUTPUT_DIR / "champion_probabilities.csv"
            completion_path = SIMULATION_OUTPUT_DIR / "bracket_completion_summary.csv"
            source_path = SIMULATION_OUTPUT_DIR / "probability_source_summary.csv"
            champion = pd.read_csv(champion_path) if champion_path.exists() else pd.DataFrame()
            completion = pd.read_csv(completion_path) if completion_path.exists() else pd.DataFrame()
            print(f"Champion probabilities: {champion_path}")
            if not completion.empty:
                row = completion.iloc[0]
                print(f"Full bracket completion rate: {row['full_bracket_completed_rate']:.4f}")
            if not champion.empty:
                print(champion.sort_values("champion_prob", ascending=False).head(10).to_string(index=False))
            print(f"Probability source summary: {source_path}")
            print(f"Full champion report: {BRACKET_REPORT_DIR / 'full_champion_simulation_summary.md'}")
        elif args.command == "fetch-live-state":
            from src.live_state.live_pipeline import fetch_live_state_data

            result = fetch_live_state_data()
            print("Live state fetch completed.")
            print(f"  fixtures: {len(result['fixtures'])}")
            print(f"  standings rows: {len(result['standings'])}")
            for report in result.get("reports", []):
                if report:
                    print(f"  report: {report}")
        elif args.command == "build-live-state":
            from src.live_state.live_pipeline import build_live_state

            result = build_live_state()
            print("Live tournament state built.")
            print(f"  current phase: {result['current_phase']}")
            print("  state: outputs/live_state/current_tournament_state.csv")
            print("  bracket: outputs/live_state/merged_bracket_state.csv")
            print("  probabilities: outputs/live_state/remaining_match_probabilities.csv")
        elif args.command == "run-live-forecast":
            from src.live_state.live_pipeline import run_live_forecast_pipeline

            result = run_live_forecast_pipeline(
                n_simulations=args.n_simulations,
                seed=args.seed,
                allow_fallback_forecast=args.allow_fallback_forecast,
                skip_live_matchup_predictions=args.skip_live_matchup_predictions,
            )
            print("Live forecast completed." if result.get("forecast_ran", False) else "Live forecast stopped by quality gate.")
            print(f"  status: {result['status']}")
            print(f"  forecast mode: {result.get('forecast_mode', 'unknown')}")
            print(f"  public label: {result.get('public_label', 'unknown')}")
            print(f"  source quality score: {result.get('source_quality_score', 'unknown')}")
            print(f"  current phase: {result['current_phase']}")
            print(f"  finalist prediction active: {result['finalist_prediction_active']}")
            print(f"  live matchup predictions: {result.get('live_matchup_prediction_status', 'not_run')} ({result.get('live_matchups_predicted', 0)} predicted)")
            print(f"  live model probability uses: {result.get('live_model_probability_uses', 0)}")
            print(f"  top finalist pair: {result['top_finalist_pair']} ({result['top_finalist_pair_probability']:.4f})")
            print(f"  top champion: {result['top_champion']} ({result['top_champion_probability']:.4f})")
            print(f"  fallback bracket usage: {result['fallback_bracket_usage']:.2%}")
            if result.get("reason"):
                print(f"  reason: {result['reason']}")
        elif args.command == "identify-live-knockout-matchups":
            from src.live_state.live_matchup_features import REMAINING_MATCHUPS_PATH, identify_remaining_live_knockout_matches

            matchups = identify_remaining_live_knockout_matches()
            print(f"Known remaining knockout matchups: {len(matchups)}")
            for _, row in matchups.iterrows():
                print(f"  {row['stage']}: {row['team_a']} vs {row['team_b']} ({row['date']})")
            print(f"Saved to {REMAINING_MATCHUPS_PATH}")
        elif args.command == "build-live-knockout-features":
            from src.live_state.live_matchup_features import LIVE_FEATURES_PATH, build_live_knockout_features

            features = build_live_knockout_features()
            print(f"Live knockout feature rows: {len(features)}")
            if not features.empty:
                complete = int((features["feature_status"] == "complete").sum())
                print(f"  complete feature rows: {complete}")
                print(f"  rows with missing feature values: {len(features) - complete}")
            print(f"Saved to {LIVE_FEATURES_PATH}")
        elif args.command == "predict-live-knockout":
            from src.live_state.live_matchup_predictor import predict_live_knockout_matchups

            result = predict_live_knockout_matchups()
            print("Live knockout prediction completed.")
            print(f"  model: {result['model_name']}")
            print(f"  predicted rows: {result['predicted_rows']}")
            print(f"  failed rows: {result['failed_rows']}")
            print(f"  predictions: {result['predictions_path']}")
        elif args.command == "build-public-exports":
            from src.public_export.build_public_exports import build_public_exports

            result = build_public_exports()
            print(f"Public exports written to {result['directory']}: {len(result['written'])} files")
            for name in result["written"]:
                print(f"  {name}")
            if result["skipped"]:
                print(f"  skipped (no source data): {result['skipped']}")
        elif args.command == "validate-public-exports":
            from src.public_export.export_validation import validate_public_exports

            result = validate_public_exports()
            print(f"Public export validation: {result['status']} ({result['checks']} checks, {result['failed']} failed)")
            print(f"Report: {result['report']}")
        elif args.command == "validate-dashboard":
            from src.public_export.export_validation import validate_dashboard

            result = validate_dashboard()
            print(f"Dashboard validation: {result['status']} ({result['checks']} checks, {result['failed']} failed)")
            print(f"Report: {result['report']}")
        elif args.command == "validate-deployment-readiness":
            from src.public_export.deployment_readiness import validate_deployment_readiness

            result = validate_deployment_readiness()
            for key, value in result["checks"].items():
                print(f"  {key}: {value}")
            print(f"Overall: {result['status']}")
            print(f"Report: {result['report']}")
        elif args.command == "validate-live-matchup-flow":
            from src.live_state.integration_checks import run_live_matchup_flow_check

            result = run_live_matchup_flow_check()
            print(f"Live matchup flow integration status: {result['status']}")
            for name, ok, detail in result["checks"]:
                print(f"  {name}: {'pass' if ok else 'fail'} ({detail})")
            print(f"Report: {result['report']}")
        elif args.command == "validate-live-feature-equivalence":
            from src.live_state.live_matchup_features import run_feature_equivalence_validation

            result = run_feature_equivalence_validation()
            print(f"Feature equivalence status: {result['status']}")
            print(f"  rows compared: {result['rows_compared']} | features per row: {result['features_compared']}")
            print(f"  exact: {result['exact']} | tolerance-only: {result['tolerance_only']} | mismatches: {result['mismatches']}")
            print(f"  max abs diff: {result['max_abs_diff']}")
            print(f"  runtime original: {result['original_seconds']}s | fast: {result['fast_seconds']}s")
            print(f"  report: {result['report']}")
        elif args.command == "live-knockout-prediction-summary":
            from src.live_state.live_prediction_reports import validate_live_knockout_predictions, write_live_knockout_prediction_report

            report = write_live_knockout_prediction_report()
            validation = validate_live_knockout_predictions()
            print(f"Live knockout prediction report: {report}")
            print(f"Validation status: {validation['status']}")
            for check, status, message in validation["checks"]:
                print(f"  {check}: {status} ({message})")
            print(f"Validation report: {validation['report']}")
        elif args.command == "live-forecast-summary":
            import json
            import pandas as pd
            from src.live_state.live_config import LIVE_STATE_DIR, LIVE_REPORT_DIR

            summary_path = LIVE_STATE_DIR / "live_forecast_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}
            pair = pd.read_csv(LIVE_STATE_DIR / "finalist_pair_probabilities.csv") if (LIVE_STATE_DIR / "finalist_pair_probabilities.csv").exists() else pd.DataFrame()
            reach = pd.read_csv(LIVE_STATE_DIR / "team_reach_final_probabilities.csv") if (LIVE_STATE_DIR / "team_reach_final_probabilities.csv").exists() else pd.DataFrame()
            champion = pd.read_csv(LIVE_STATE_DIR / "live_champion_probabilities.csv") if (LIVE_STATE_DIR / "live_champion_probabilities.csv").exists() else pd.DataFrame()
            print(f"Current phase: {summary.get('current_phase', 'unknown')}")
            print(f"Finalist prediction active: {summary.get('finalist_prediction_active', False)}")
            print("Top finalist pairs:")
            if not pair.empty:
                print(pair.head(10).to_string(index=False))
            print("Top reach-final teams:")
            if not reach.empty:
                print(reach.head(10).to_string(index=False))
            print("Top champion probabilities:")
            if not champion.empty:
                print(champion.head(10).to_string(index=False))
            print(f"Fallback usage: {summary.get('fallback_bracket_usage', 0):.2%}")
            print(f"Reports: {LIVE_REPORT_DIR}")
        elif args.command == "validate-live-forecast":
            from src.live_state.live_validation import validate_live_forecast

            result = validate_live_forecast()
            print(f"Live forecast validation status: {result['status']}")
            print(f"Live forecast validation report saved to {result['report']}")
        elif args.command == "diagnose-live-api":
            from src.live_state.api_football_diagnostics import run_api_football_live_diagnostics

            result = run_api_football_live_diagnostics()
            print("Live API diagnostic completed.")
            print(f"  status: {result['status']}")
            print(f"  league ID: {result['league_id']}")
            print(f"  fixtures: {result['fixtures_count']}")
            print(f"  completed: {result['completed_count']}")
            print(f"  standings rows: {result['standings_count']}")
            print(f"  current phase: {result['current_phase']}")
            print(f"  report: {result['report']}")
        elif args.command == "diagnose-football-data-org":
            from src.live_state.provider_diagnostics import diagnose_football_data_org

            result = diagnose_football_data_org()
            summary = result["summary"]
            print("football-data.org diagnostic completed.")
            print(f"  provider status: {summary['provider_status']}")
            print(f"  token present: {summary['credentials_available']}")
            print(f"  fixtures: {summary['fixture_rows']}")
            print(f"  completed: {summary['completed_rows']}")
            print(f"  standings rows: {summary['standings_rows']}")
            print(f"  report: {result['report']}")
        elif args.command == "fetch-football-data-org":
            from src.live_state.provider_diagnostics import fetch_football_data_org

            result = fetch_football_data_org()
            print("football-data.org fetch completed.")
            print("  snapshots: outputs/live_state/provider_snapshots/football_data_org")
            print(f"  matches keys: {', '.join(result['matches'].keys()) if isinstance(result.get('matches'), dict) else 'none'}")
        elif args.command == "normalize-football-data-org":
            from src.live_state.provider_diagnostics import normalize_football_data_org

            result = normalize_football_data_org()
            print("football-data.org normalization completed.")
            print(f"  fixtures: {len(result['fixtures'])}")
            print(f"  teams: {len(result['teams'])}")
            print(f"  standings: {len(result['standings'])}")
            print(f"  bracket: {len(result['bracket'])}")
            print(f"  report: {result['report']}")
        elif args.command == "diagnose-live-providers":
            from src.live_state.provider_registry import diagnose_live_providers

            result = diagnose_live_providers()
            print("Live provider diagnostics completed.")
            print(result["comparison"].to_string(index=False))
            print(f"Comparison: {result['comparison_path']}")
            print(f"Report: {result['report']}")
        elif args.command == "select-live-provider":
            from src.live_state.provider_registry import select_live_provider

            result = select_live_provider()
            print(f"Selected provider: {result['provider']}")
            if result.get("selection"):
                print(f"  status: {result['selection'].get('provider_status')}")
                print(f"  fixtures: {result['selection'].get('fixture_rows')}")
                print(f"  completed: {result['selection'].get('completed_rows')}")
                print(f"  score: {result['selection'].get('selection_score')}")
            print(f"Report: {result['report']}")
        elif args.command == "verify-live-sources":
            from src.live_state.live_pipeline import run_live_source_verification

            result = run_live_source_verification()
            gate = result["quality_gate"]
            print("Live source verification completed.")
            print(f"  forecast mode: {gate['forecast_mode']}")
            print(f"  source quality score: {gate['source_quality_score']}")
            print(f"  current phase: {gate['current_phase']}")
            print(f"  fallback usage: {gate['fallback_usage_rate']:.2%}")
            print(f"  quality report: {gate['report']}")
        elif args.command == "live-quality-gate":
            from src.live_state.live_pipeline import build_live_state, fetch_live_state_data
            from src.live_state.live_quality_gate import evaluate_live_forecast_quality

            fetch_live_state_data()
            state = build_live_state()
            gate = evaluate_live_forecast_quality(live_bracket=state["bracket"], live_standings=state["standings"]["standings"], current_phase=state["current_phase"])
            print(f"Forecast mode: {gate['forecast_mode']}")
            print(f"Public label: {gate['public_label']}")
            print(f"Source quality score: {gate['source_quality_score']}")
            print(f"Current phase: {gate['current_phase']}")
            print(f"Completed result count: {gate['completed_result_count']}")
            print(f"Fallback usage: {gate['fallback_usage_rate']:.2%}")
            print(f"Finalist forecast allowed: {gate['finalist_prediction_allowed']}")
            print(f"Report: {gate['report']}")
        elif args.command == "live-source-summary":
            import json
            import pandas as pd
            from pandas.errors import EmptyDataError
            from src.live_state.live_config import LIVE_STATE_DIR
            from src.live_state.live_source_config import SOURCE_VERIFICATION_REPORT_DIR
            from src.live_state.live_pipeline import build_live_state, fetch_live_state_data
            from src.live_state.live_quality_gate import evaluate_live_forecast_quality
            from src.live_state.live_config import coerce_bool_series

            def _read_optional_csv(path):
                try:
                    return pd.read_csv(path) if path.exists() else pd.DataFrame()
                except EmptyDataError:
                    return pd.DataFrame()

            fetch_live_state_data()
            state = build_live_state()
            gate = evaluate_live_forecast_quality(live_bracket=state["bracket"], live_standings=state["standings"]["standings"], current_phase=state["current_phase"])
            gate_path = LIVE_STATE_DIR / "live_forecast_quality_gate.json"
            gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else gate
            fixtures = _read_optional_csv(LIVE_STATE_DIR / "live_fixtures_normalized.csv")
            standings = _read_optional_csv(LIVE_STATE_DIR / "live_standings_normalized.csv")
            bracket = _read_optional_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
            print(f"API/live fixture rows: {len(fixtures)}")
            print(f"Completed fixtures: {int(coerce_bool_series(fixtures.get('is_completed', pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0}")
            print(f"Standings rows: {len(standings)}")
            print(f"Bracket rows: {len(bracket)}")
            print(f"Forecast mode: {gate.get('forecast_mode', 'unknown')}")
            print(f"Source quality score: {gate.get('source_quality_score', 'unknown')}")
            print(f"Fallback usage: {gate.get('fallback_usage_rate', 0):.2%}" if isinstance(gate.get("fallback_usage_rate", 0), (int, float)) else f"Fallback usage: {gate.get('fallback_usage_rate', 'unknown')}")
            comparison_path = LIVE_STATE_DIR.parent / "reports" / "live_state" / "providers" / "provider_comparison.csv"
            if comparison_path.exists():
                comparison = pd.read_csv(comparison_path)
                if not comparison.empty:
                    print("Providers:")
                    print(comparison[["provider", "provider_status", "fixture_rows", "completed_rows", "selection_score"]].to_string(index=False))
            print(f"Reports: {SOURCE_VERIFICATION_REPORT_DIR}")
        elif args.command == "load-real-data":
            from src.loading.real_data_loader import load_real_data

            result = load_real_data(
                prefer=args.prefer,
                skip_api=args.skip_api,
                skip_kaggle=args.skip_kaggle,
                skip_fbref=args.skip_fbref,
                skip_elo=args.skip_elo,
                debug=args.debug,
            )
            print("Real data loading completed.")
            print(f"  security check report: {result['security_check_report']}")
            print(f"  env check report: {result['env_check_report']}")
            print(f"  source status report: {result['source_status_report']}")
            print(f"  data readiness report: {result['data_readiness_report']}")
            print(f"  data summary report: {result['data_summary_report']}")
            print(f"  feature readiness gate: {result['feature_readiness_gate']}")
            print(f"  manual data needed report: {result['manual_data_needed_report']}")
            print(f"  api football status report: {result['api_football_status_report']}")
            print(f"  backup folder: {result['backup_folder']}")
            if result["restored_files"]:
                print("  restored previous good files:")
                for path in result["restored_files"]:
                    print(f"    - {path}")
        elif args.command == "update":
            from src.update.update_runner import run_update

            result = run_update(mode=args.mode, force=args.force, run_live_forecast=args.run_live_forecast, n_simulations=args.n_simulations, no_retrain=args.no_retrain, allow_fallback_forecast=args.allow_fallback_forecast)
            print("Update completed:")
            print(f"  mode: {result['mode']}")
            print(f"  source: {result['source_used']}")
            print(f"  new completed matches: {result['new_completed_matches_detected']}")
            print(f"  validation: {result['validation_status']}")
            if result.get("live_forecast"):
                print(f"  live forecast: {result['live_forecast'].get('status')}")
            print("  summary: outputs/reports/latest_refresh_summary.md")
        return 0
    except Exception as exc:
        logger.exception("Command failed")
        print(f"Command failed: {exc}")
        print("Suggested fix: check .env credentials, source availability, and the logs in outputs/reports/fetch_pipeline.log.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
