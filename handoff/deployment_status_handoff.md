# Deployment Status Handoff

Saved: 2026-07-10  
Scope: attempt to deploy the completed Phase 6/6B portfolio system to GitHub, Vercel, and Streamlit Cloud. Records exactly what was verified, what was changed, and the exact remaining user actions. No secrets included. No deployment was faked.

## Outcome in one line

The repository is fully deployment-ready on branch `main` (HEAD `df0cf8b`), all validations/tests/builds pass, but **no actual GitHub/Vercel/Streamlit deployment was possible from this environment** because it has no `gh` CLI, no `vercel` CLI, no Streamlit deploy CLI, and no GitHub/Vercel auth tokens. Every deployment step is browser- or authenticated-CLI-only and is left as a one-command user action below.

## Environment audit (verified this session)

- `gh` — not installed. `vercel` — not installed. `npx vercel` — would require install (declined). No `GITHUB_TOKEN`/`VERCEL_TOKEN`/`GH_TOKEN` in env.
- Git: branch `main`, **no remote configured** (none invented). Clean history of 4 commits.
- Node v24.14.0, Python 3.12.2, Streamlit 1.58, Plotly 6.8 all present locally.

## Change made this session

- Commit **`df0cf8b`** "Untrack raw provider snapshots before public release": `git rm --cached` the 1.4 MB of `outputs/live_state/provider_snapshots/**` (16 files) and added them to `.gitignore`. Rationale: the deployment brief's Step 1 explicitly lists `provider_snapshots/` as should-not-be-tracked; they are sanitized (verified: no token/auth content) but are bulky raw third-party API payloads that no app reads (website + dashboard consume `public_data/` and the normalized CSVs, which stay tracked). Working files preserved; reversible. The commit-safety allowlist already blocked automation from committing these going forward.
- Note (not changed): `outputs/live_state/api_football_live_*.json` stubs remain tracked (tiny, empty API-Football responses). Optional future cleanup; not a secret or deployment risk.

## Verification run (all passed, this session)

```text
python -m compileall src main.py scripts dashboard   -> OK
python -m pytest tests -q                             -> 16 passed
python main.py validate                               -> no failures
python main.py validate-features / -simulation / -bracket / -live-forecast -> pass
python main.py validate-public-exports                -> pass (31 checks)
python main.py validate-dashboard                     -> pass (10 checks)
python main.py validate-deployment-readiness          -> ready (8/8)
cd website && npm ci && npm run lint && npm run build  -> clean, 55 static pages
streamlit run dashboard/app.py --server.headless true  -> health "ok"
Secret scan over all tracked files                     -> 0 hits
Tracked forbidden files (.env / kaggle.json / provider_snapshots) -> none
```

## Git state

```text
df0cf8b  Untrack raw provider snapshots before public release   <- HEAD (main)
277f64c  Phase 6B: matchday automation, fail-closed publication, commit safety, GitHub Actions
efa514a  Phase 6 handoff and current status documentation
3e240d4  Phase 6: public website, Streamlit dashboard, public data exports, deployment readiness
```

Working tree: 6 uncommitted files, all regenerated validation reports with only timestamp differences (volatile, correctly uncommitted; do not affect a push).

## Deployment target compatibility (verified, not deployed)

- **Vercel (website/):** production build passes; reads `../public_data/*.json` at build time via `fs`. Works with Root Directory = `website` because Vercel checks out the whole repo. No prebuild sync and no provider API key required.
- **Streamlit (dashboard/app.py):** headless startup healthy; reads only saved outputs; no API calls, no retraining, no simulation on load; no secrets required; paths resolve from the file location so the working directory does not matter.
- **GitHub Actions:** `validate.yml` (offline, secret-free) and `portfolio-refresh.yml` (manual dispatch, requires `FOOTBALL_DATA_ORG_KEY` secret) are committed and YAML-valid; never executed on GitHub (no remote yet).

## Exact remaining user actions

```bash
# 1. Create the GitHub repo and push (from the project root)
gh repo create dynamic-fifa-2026-predictor --public --source=. --remote=origin --push
#   or, via the web UI, then:
#   git remote add origin https://github.com/<you>/dynamic-fifa-2026-predictor.git
#   git push -u origin main

# 2. Configure the Actions secret (value never printed or committed)
gh secret set FOOTBALL_DATA_ORG_KEY      # optional: API_FOOTBALL_KEY

# 3. Vercel: New Project -> import repo -> Root Directory = website -> Deploy (no env vars needed to render)
# 4. Streamlit Community Cloud: New app -> repo, branch main, main file dashboard/app.py -> Deploy
# 5. Set NEXT_PUBLIC_GITHUB_URL and NEXT_PUBLIC_DASHBOARD_URL in Vercel to the real URLs;
#    update README "Live demo" links with the real URLs; commit + push; Vercel redeploys.
# 6. GitHub -> Actions -> "Portfolio Refresh (matchday)" -> Run workflow with dry_run: true (first test).
```

README live-demo links were intentionally left as placeholders (update only with real URLs).

## Known limitations

- The only blocker is environmental: no deployment CLIs / no browser here. All three platform deployments and the first hosted Actions run remain user steps.
- Workflows are locally validated but never run on GitHub-hosted runners; first dispatch should use `dry_run: true`.
- Some pre-6B tracked reports embed absolute local paths (excluded from the automation allowlist; harmless in history).

## Recommended next step

Complete the six user actions above (≈15 minutes of authenticated clicks). After deployment, operate the tournament with `python main.py refresh-portfolio --n-simulations 10000 --no-retrain` after each match. Begin **Phase 7 (post-tournament backtesting and calibration)** once the final is played and the forecast-history files span the full knockout stage.
