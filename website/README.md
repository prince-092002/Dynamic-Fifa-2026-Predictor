# FIFA 2026 Predictor — Website

Next.js 15 + TypeScript + Tailwind CSS 4 public site. Fully static: every page is prerendered at build time from `../public_data/*.json` (see `../PUBLIC_DATA_CONTRACT.md`). No API keys, no client-side fetching, no backend duplication.

## Local development

```bash
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build    # production build (55 static pages)
```

Regenerate the data the site renders from the repository root:

```bash
python main.py build-public-exports
```

## Deploy to Vercel

1. Push the repository to GitHub.
2. Vercel → Add New Project → import the repository.
3. **Root Directory: `website`** (Next.js auto-detected). The build reads `../public_data/` from the repository clone.
4. Optional environment variables (outbound link buttons only; the site renders without them):
   - `NEXT_PUBLIC_DASHBOARD_URL` — deployed Streamlit dashboard URL
   - `NEXT_PUBLIC_GITHUB_URL` — repository URL
5. Deploy. Pushing new `public_data/` after a matchday update redeploys automatically.

## Structure

```text
app/            routes: / , /teams , /team/[slug] , /methodology , /about
components/     Nav, Footer, Bracket, TeamExplorer, ProbBar, SourceBadge
lib/data.ts     build-time fs readers (server only)
lib/types.ts    shared types + display helpers (client safe)
app/globals.css design tokens (FIFA-2026-inspired palette) + Tailwind 4
```

Design tokens live as CSS variables in `globals.css` (`--background-primary`, `--accent-cyan`, `--accent-magenta`, …). Probability sources are always labeled with text + symbol, never color alone.
