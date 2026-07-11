# ⚽ Dynamic FIFA 2026 Tournament Outcome Predictor

A live machine-learning forecasting system that combines **real FIFA World Cup 2026 results**, **XGBoost matchup probabilities**, and **Monte Carlo tournament simulation** to continuously update finalist and champion forecasts — with automated validation, honest probability-source labeling, and a full audit trail on every run.

> Independent analytics project. Not affiliated with or endorsed by FIFA. Predictions are probabilistic estimates, not guarantees.

## Live demo

- **Website (Vercel):** https://dynamic-fifa-2026-predictor.vercel.app — auto-redeploys from `main` on every matchday push
- **Source (GitHub):** https://github.com/prince-092002/Dynamic-Fifa-2026-Predictor
- **Interactive dashboard (Streamlit):** _pending — deploy `dashboard/app.py` on Streamlit Community Cloud_

## Architecture

```text
GitHub Repository (source + docs + public-safe data)
        │
        ├────────────────────────────┐
        ▼                            ▼
  Vercel Website              Streamlit Dashboard
  Next.js 15 + Tailwind       Streamlit + Plotly
  static, rebuilt on push     deep interactive analytics
        │                            │
        └─────────────┬──────────────┘
                      ▼
          public_data/*.json  (stable public contracts)
                      ▼
   Python + XGBoost + Monte Carlo backend
   football-data.org live provider · quality gate · validation suite
```

## What it does

- Ingests real tournament fixtures, results, standings, and bracket state from **football-data.org** (with rate-limit resilience, last-good data preservation, and honest freshness disclosure).
- Locks **completed real results** — a finished match is never re-simulated.
- Builds **leakage-safe features** for each newly resolved knockout matchup (chronological history, shift-before-rolling, no target leakage) and predicts it with a trained **XGBoost** win/draw/loss classifier.
- Runs **Monte Carlo tournament simulations** (seeded, reproducible) to estimate reach-final and championship probabilities.
- Attributes every simulation decision to its probability source: `completed_result → live XGBoost → pre-tournament model → Elo fallback → neutral fallback`. Fallback is never mislabeled as a model prediction.
- Validates everything: a 19-check live integrity suite, broader data validation, public-export contracts, dashboard inputs, feature-equivalence proofs, and a sandboxed integration test for the resolved-matchup flow.
- Leaves an audit trail per run: manifest, phase transitions, probability-source history, provider freshness, and forecast history.

## Machine-learning methodology (short version)

~50k historical international matches → leakage-safe features (Elo-derived strength, recent form, goals, head-to-head, rest/schedule, tournament context) → model comparison (baselines, logistic regression, XGBoost) → selected XGBoost classifier → live matchup probabilities → Monte Carlo bracket simulation. Full details: the website's `/methodology` page, the dashboard's *Model & Methodology* page, and [docs/BACKEND_REFERENCE.md](docs/BACKEND_REFERENCE.md).

## How to run locally

```bash
pip install -r requirements.txt
cp .env.example .env       # add your own keys (only needed to refresh live data)
```

### Refresh after a real match (the one operational command)

```bash
python main.py refresh-portfolio --n-simulations 10000 --no-retrain
```

This fetches live state, locks new results, predicts newly resolved matchups with XGBoost, re-runs the Monte Carlo forecast, validates everything, **fail-closed publishes** `public_data/` (an invalid export never replaces the last known-good one), and writes a machine-readable refresh manifest with an explicit `eligible_for_publication` verdict. Then check what automation may commit:

```bash
python main.py check-commit-safety
```

Full post-match procedure, GitHub Actions usage, and failure behavior: [docs/MATCHDAY_OPERATIONS.md](docs/MATCHDAY_OPERATIONS.md). The lower-level `update --mode matchday --run-live-forecast …` command remains available.

### Rebuild / validate public exports only

```bash
python main.py build-public-exports
python main.py validate-public-exports
python main.py validate-dashboard
python main.py validate-deployment-readiness
```

### Launch the dashboard

```bash
streamlit run dashboard/app.py
```

### Launch the website locally

```bash
cd website
npm install
npm run dev        # development
npm run build      # production build (also run by Vercel)
```

## Deployment

### Vercel (website)

1. Push this repository to GitHub.
2. In Vercel: **Add New Project → Import** the repository.
3. Set **Root Directory** to `website` (framework auto-detected: Next.js).
4. Optional env vars: `NEXT_PUBLIC_DASHBOARD_URL`, `NEXT_PUBLIC_GITHUB_URL` (used for outbound buttons; the site renders fully without them). No API key is required — the site renders from committed `public_data/`.
5. Deploy. Every push (e.g. after a matchday update) redeploys automatically.

### Streamlit Community Cloud (dashboard)

1. In Streamlit Cloud: **New app** → pick the GitHub repository.
2. Entry point: `dashboard/app.py`.
3. No secrets are required — the dashboard renders saved outputs from `public_data/` and `outputs/` without calling football-data.org.
4. Deploy.

### Operational flow after each real match

```text
match completes → run refresh-portfolio → eligibility + commit-safety gates pass
→ commit/push allowlisted public artifacts
→ Vercel redeploys the website → Streamlit reads the newest repository outputs
```

### GitHub Actions

- `validate.yml` — offline CI on every PR/push: backend validation suite, pytest, website lint + production build. No secrets, no live API calls.
- `portfolio-refresh.yml` — **manual dispatch only**: runs the full matchday refresh in CI (requires the `FOOTBALL_DATA_ORG_KEY` repository secret), refuses publication unless all validations pass, and commits only strictly allowlisted generated artifacts. Supports a `dry_run` input.

## Repository structure

```text
main.py                     CLI (40+ commands)
src/                        backend: fetch, cleaning, features, modeling, simulation,
                            live_state, validation, update, public_export
dashboard/                  Streamlit analytics app (app.py + 8 pages)
website/                    Next.js 15 public site (see website/README.md)
public_data/                public-safe JSON contracts consumed by both apps
outputs/                    generated state, predictions, simulations, reports
data/                       raw + processed datasets
handoff/                    per-phase engineering handoffs
docs/                       backend command reference
PUBLIC_DATA_CONTRACT.md     schema + freshness contract for public_data/
```

## Validation philosophy

Checks must have genuine failure conditions. Expected conditions (e.g. TBD knockout template slots) are visible warnings, not silenced; genuine defects fail loudly. Key commands: `validate`, `validate-features`, `validate-live-forecast` (19 checks), `validate-live-feature-equivalence`, `validate-live-matchup-flow` (sandboxed), `validate-public-exports`, `validate-dashboard`, `validate-deployment-readiness`.

## Known limitations

- Semifinal/final pairings inside simulation branches use Elo fallback until their real participants are known (labeled, expected, shrinks each round).
- Player-level statistics are not part of the verified data pipeline and are therefore not displayed.
- Forecast-history charts appear only after multiple recorded forecast runs — history is never backfilled or invented.
- football-data.org free tier can rate-limit secondary endpoints; core data is preserved and freshness is disclosed honestly.
- No license file yet; add one before publicizing the repository if reuse terms matter to you.

## Disclaimer

Independent analytics project. Not affiliated with or endorsed by FIFA. Team names and results come from football-data.org. Predictions are probabilistic estimates, not guarantees.
