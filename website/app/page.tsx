import Link from "next/link";
import Bracket from "@/components/Bracket";
import HeroBackdrop from "@/components/HeroBackdrop";
import { Section, SectionHead, StatCard, ProbRing, Meter, Disclaimer } from "@/components/ui";
import { Trophy, Pitch, Chart, Shield, Lock, Sim, Signal, Gauge, Database, Network, Team, Lab, Arrow, Check, Route } from "@/components/icons";
import CountryFlag from "@/components/CountryFlag";
import { formatPct, formatPhase, getBracket, getChampionForecast, getFinalistPairs, getOverview, getTeams } from "@/lib/data";

const BADGES = ["Python", "XGBoost", "Monte Carlo", "Elo", "football-data.org", "Next.js", "Streamlit"];

const PIPELINE = [
  { icon: <Database width={18} height={18} />, t: "Historical Data", d: "~50k international matches" },
  { icon: <Shield width={18} height={18} />, t: "Leakage-Safe Features", d: "shift-before-rolling, pre-match only" },
  { icon: <Gauge width={18} height={18} />, t: "Elo · Form · Context", d: "25 engineered signals" },
  { icon: <Network width={18} height={18} />, t: "XGBoost Model", d: "win / draw / loss probabilities" },
  { icon: <Chart width={18} height={18} />, t: "Match Probabilities", d: "calibrated per matchup" },
  { icon: <Sim width={18} height={18} />, t: "Monte Carlo", d: "full-bracket simulation" },
  { icon: <Trophy width={18} height={18} />, t: "Live Forecast", d: "champion & finalist odds" },
];

const RANK_ACCENT = ["var(--gold-c)", "var(--cyan)", "var(--cyan)", "var(--fg-2)", "var(--fg-2)"];

export default function Home() {
  const overview = getOverview();
  const bracket = getBracket();
  const champion = getChampionForecast();
  const pairs = getFinalistPairs();
  const teams = getTeams()?.teams ?? [];
  const teamBy = new Map(teams.map((t) => [t.team, t]));
  const teamCodes = Object.fromEntries(teams.map((t) => [t.team, t.code]));
  const contenders = (champion?.entries ?? []).slice().sort((a, b) => b.champion_probability - a.champion_probability).slice(0, 5);
  const live = overview?.forecast_mode === "true_live_forecast";

  return (
    <>
      {/* ============ HERO (fixed poster) ============ */}
      <HeroBackdrop />
      <section className="relative flex min-h-[86vh] flex-col items-center justify-center px-4 pb-20 pt-16 text-center md:min-h-[90vh]">
        <div className="reveal flex flex-wrap items-center justify-center gap-2.5">
          {live && <span className="badge-live"><span className="dot-live" /> LIVE FORECAST ACTIVE</span>}
          <span className="chip"><Pitch width={14} height={14} /> {formatPhase(overview?.current_phase)}</span>
          <span className="chip"><Lock width={14} height={14} /> {overview?.completed_matches ?? "—"} matches locked</span>
          {overview?.simulations && <span className="chip"><Sim width={14} height={14} /> {overview.simulations.toLocaleString()} simulations</span>}
        </div>

        <p className="reveal reveal-2 kicker hero-copy mt-7">Dynamic Tournament Intelligence</p>
        <h1 className="reveal reveal-2 poster-title mt-2">FIFA 2026</h1>
        <p className="reveal reveal-3 poster-sub hero-copy mt-3 text-lg text-white md:text-2xl">
          Live finalist &amp; champion forecasting — <span className="text-white">powered by machine learning</span>
        </p>
        <p className="reveal reveal-3 hero-copy mx-auto mt-4 max-w-2xl text-[0.98rem] text-white md:text-lg">
          ~50,000 historical matches · Elo ratings · XGBoost matchup probabilities · Monte Carlo simulation —
          fused into one forecast that updates the moment a real match ends.
        </p>

        <div className="reveal reveal-3 mt-8 flex flex-wrap items-center justify-center gap-3">
          {process.env.NEXT_PUBLIC_DASHBOARD_URL && (
            <a href={process.env.NEXT_PUBLIC_DASHBOARD_URL} target="_blank" rel="noreferrer" className="btn btn-primary">
              Explore Live Dashboard <Arrow width={16} height={16} />
            </a>
          )}
          <a href="#snapshot" className="btn btn-ghost">See the Forecast</a>
          <Link href="/about" className="btn btn-ghost">How It Works</Link>
        </div>

        <ul className="reveal reveal-4 mt-9 flex max-w-2xl flex-wrap justify-center gap-2">
          {BADGES.map((b) => <li key={b} className="chip">{b}</li>)}
        </ul>
        <Disclaimer className="hero-copy mt-7" />
        <a href="#snapshot" aria-label="Scroll to forecast" className="reveal reveal-4 mt-10 hidden md:block"><span className="scroll-cue mx-auto block" /></a>
      </section>

      <div className="mx-auto max-w-[78rem] px-4">
        {/* ============ LIVE SNAPSHOT (broadcast row) ============ */}
        {overview && (
          <Section id="snapshot">
            <SectionHead kicker="Live tournament snapshot" title="The state of play" icon={<Signal width={14} height={14} />}
              sub={overview.public_label ?? undefined} />
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard icon={<Pitch width={17} height={17} />} label="Current phase" value={formatPhase(overview.current_phase)} accent="var(--cyan)" hint={`${overview.known_unresolved_matchups} matchups unresolved`} />
              <StatCard icon={<Lock width={17} height={17} />} label="Matches complete" value={overview.completed_matches ?? "—"} accent="var(--pitch)" hint="locked · never re-simulated" />
              <StatCard icon={<Team width={17} height={17} />} label="Teams remaining" value={overview.teams_alive} accent="var(--gold-c)" hint={`${overview.teams_eliminated} eliminated`} />
              <StatCard icon={<Signal width={17} height={17} />} label="Source quality" value={`${overview.source_quality_score ?? "—"}/100`} accent="var(--cyan)"
                hint={overview.data_source_mode === "fresh_api" ? `fresh · ${overview.data_age_minutes ?? 0} min` : String(overview.data_source_mode)} />
            </div>

            {/* Featured champion */}
            {overview.top_champion && (
              <div className="card-feature mt-4 grid gap-6 p-6 md:grid-cols-[1fr_auto] md:items-center">
                <div className="bg-floodlight absolute inset-0 opacity-60" aria-hidden />
                <div className="relative">
                  <span className="kicker inline-flex items-center gap-2 text-gold"><Trophy width={14} height={14} /> Most likely champion</span>
                  <div className="mt-2 flex items-center gap-3">
                    <CountryFlag code={teamBy.get(overview.top_champion)?.code} country={overview.top_champion} size="xl" />
                    <span className="display text-3xl md:text-4xl text-fg">{overview.top_champion}</span>
                  </div>
                  <p className="mt-2 max-w-md text-sm text-fg2">
                    Highest championship probability across {overview.simulations?.toLocaleString()} Monte Carlo simulations of the remaining bracket. Final:{" "}
                    <span className="text-fg">{overview.top_finalist_pair}</span> ({formatPct(overview.top_finalist_pair_probability)}).
                  </p>
                </div>
                <div className="relative flex items-center justify-center md:pr-4">
                  <ProbRing value={overview.top_champion_probability ?? 0} size={128} stroke={11} color="var(--gold-c)" label="champion" />
                </div>
              </div>
            )}
          </Section>
        )}

        {/* ============ WHO WILL WIN ============ */}
        {contenders.length > 0 && (
          <Section id="forecast">
            <SectionHead kicker="The title race" title="Who will win?" icon={<Trophy width={14} height={14} />}
              sub={`Championship probability from the current live forecast${champion?.simulations ? ` · ${champion.simulations.toLocaleString()} simulations` : ""}.`} />
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {contenders.map((c, i) => {
                const t = teamBy.get(c.team);
                const featured = i === 0;
                return (
                  <div key={c.team} className={`${featured ? "card-feature lg:col-span-1 lg:row-span-1" : "card card-hover"} p-5`}>
                    <div className="flex items-start justify-between">
                      <div>
                        <span className={`stat-num text-sm ${featured ? "text-gold" : "text-fg3"}`}>#{i + 1}</span>
                        <div className="mt-1 flex items-center gap-2">
                          <CountryFlag code={t?.code} country={c.team} size="lg" />
                          <span className="display text-xl text-fg">{c.team}</span>
                        </div>
                        <div className="mt-1 text-xs text-fg2">{t?.next_matchup ? `Next: ${t.next_matchup.opponent}` : t ? formatPhase(t.status) : ""}</div>
                      </div>
                      <ProbRing value={c.champion_probability} size={featured ? 84 : 66} stroke={featured ? 8 : 7} color={RANK_ACCENT[i]} label="champ" />
                    </div>
                    {t?.reach_final_probability != null && (
                      <div className="mt-4">
                        <div className="mb-1 flex justify-between text-xs text-fg2"><span>Reach final</span><span className="stat-num text-fg">{formatPct(t.reach_final_probability)}</span></div>
                        <Meter value={t.reach_final_probability} color={featured ? "var(--gold-c)" : "var(--cyan)"} />
                      </div>
                    )}
                  </div>
                );
              })}
              <Link href="/teams" className="card card-hover flex items-center justify-between p-5 text-fg2 hover:text-fg">
                <span className="flex items-center gap-2"><Team width={18} height={18} /> Explore all {teams.length} teams</span>
                <Arrow width={18} height={18} />
              </Link>
            </div>
            {pairs?.entries?.length ? (
              <div className="card mt-4 p-5">
                <span className="kicker inline-flex items-center gap-2"><Route width={14} height={14} /> Finals</span>
                <div className="mt-3 space-y-2.5">
                  {pairs.entries.slice().sort((a, b) => b.probability - a.probability).slice(0, 5).map((p) => (
                    <div key={p.finalist_pair_key} className="flex items-center gap-3">
                      <span className="w-56 shrink-0 truncate text-sm text-fg">{p.finalist_pair_key}</span>
                      <div className="flex-1"><Meter value={p.probability} color="var(--blue)" /></div>
                      <span className="stat-num w-16 shrink-0 text-right text-sm text-fg">{formatPct(p.probability)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
            <p className="mt-3 text-xs text-fg3">Probabilistic estimates from the latest live forecast — not guarantees.</p>
          </Section>
        )}

        {/* ============ ENGINE PIPELINE ============ */}
        <Section id="engine">
          <SectionHead kicker="Inside the engine" title="How the forecast is built" icon={<Network width={14} height={14} />}
            sub="A leakage-safe pipeline from raw history to a live, continuously updated tournament forecast." />
          <ol className="grid gap-3 md:grid-cols-4 lg:grid-cols-7">
            {PIPELINE.map((s, i) => (
              <li key={s.t} className="card card-hover group relative p-4">
                <div className="flex items-center gap-2">
                  <span className="grid h-8 w-8 place-items-center rounded-lg border border-line-strong bg-surface text-cyan transition-colors group-hover:text-pitch">{s.icon}</span>
                  <span className="stat-num text-xs text-fg3">{String(i + 1).padStart(2, "0")}</span>
                </div>
                <div className="mt-3 font-display text-sm font-semibold text-fg">{s.t}</div>
                <div className="mt-1 text-xs text-fg2">{s.d}</div>
                {i < PIPELINE.length - 1 && <span className="absolute -right-2 top-1/2 hidden -translate-y-1/2 text-line-strong lg:block"><Arrow width={16} height={16} /></span>}
              </li>
            ))}
          </ol>
        </Section>

        {/* ============ CREDIBILITY ============ */}
        <Section id="credibility" className="relative">
          <SectionHead kicker="Technical depth" title="Engineered for credibility, not hype" icon={<Lab width={14} height={14} />} />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["~50,000", "Historical matches", <Database key="d" width={17} height={17} />, "var(--cyan)"],
              [`${overview?.source_quality_score ?? 100}/100`, "Live source quality", <Signal key="s" width={17} height={17} />, "var(--pitch)"],
              ["0", "Completed matches re-simulated", <Lock key="l" width={17} height={17} />, "var(--gold-c)"],
              [overview?.simulations ? overview.simulations.toLocaleString() : "10,000", "Simulations / forecast", <Sim key="m" width={17} height={17} />, "var(--blue)"],
            ].map(([v, l, ic, ac]) => (
              <div key={l as string} className="card p-5">
                <span style={{ color: ac as string }}>{ic as React.ReactNode}</span>
                <div className="stat-num mt-3 text-3xl text-fg">{v as string}</div>
                <div className="mt-1 text-sm text-fg2">{l as string}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {["Chronological validation", "Pre-match Elo", "Shift-before-rolling", "Fixed-seed reproducibility", "Completed matches locked", "19-check live integrity"].map((p) => (
              <span key={p} className="chip"><Check width={14} height={14} /> {p}</span>
            ))}
          </div>
        </Section>

        {/* ============ BRACKET ============ */}
        <Section id="bracket">
          <SectionHead kicker="Knockout path" title="The road to the final" icon={<Route width={14} height={14} />}
            sub="Completed results are locked; unresolved matchups show the live XGBoost advance probability." />
          {bracket ? <Bracket bracket={bracket} teamCodes={teamCodes} /> : <div className="card p-6 text-fg2">Bracket data unavailable.</div>}
        </Section>

        {/* ============ STORY ============ */}
        <Section id="story">
          <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
            <div className="card-elev p-7">
              <SectionHead kicker="Project story" title="Why live tournament forecasting is hard" />
              <div className="space-y-3 text-sm text-fg2">
                <p>Static match prediction is a solved-ish problem: train a model, score a fixture. <span className="text-fg">Live tournament forecasting is different.</span> The bracket rewrites itself after every match, completed results must be treated as immutable truth, and each new result reshapes who can still reach the final.</p>
                <p>This platform locks every completed result, regenerates leakage-safe features for each newly resolved matchup, predicts it with XGBoost, and re-runs thousands of Monte Carlo simulations from the <span className="text-fg">actual current bracket</span> — so champion and finalist odds update the moment a match ends, without ever re-simulating history.</p>
                <p>Every probability is auditable: each simulation decision is attributed to its source (completed result, live model, or Elo fallback), and a 19-check integrity suite runs on every forecast.</p>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              {[
                ["Completed results are truth", "A finished match is locked and never re-simulated.", <Lock key="1" width={16} height={16} />, "var(--pitch)"],
                ["Honest probability sources", "Elo fallback is never labeled as a model prediction.", <Shield key="2" width={16} height={16} />, "var(--cyan)"],
                ["Reproducible by seed", "Fixed-seed runs reproduce identical forecasts.", <Sim key="3" width={16} height={16} />, "var(--gold-c)"],
              ].map(([t, d, ic, ac]) => (
                <div key={t as string} className="card rail p-4" style={{ ["--accent" as string]: ac as string }}>
                  <div className="flex items-center gap-2 pl-2 text-fg" style={{ color: ac as string }}>{ic as React.ReactNode}<span className="font-display text-sm font-semibold text-fg">{t as string}</span></div>
                  <p className="mt-1 pl-2 text-sm text-fg2">{d as string}</p>
                </div>
              ))}
            </div>
          </div>
        </Section>

        {/* ============ DASHBOARD CTA ============ */}
        <Section id="cta">
          <div className="card-feature relative overflow-hidden p-8 md:p-12">
            <div className="bg-floodlight absolute inset-0 opacity-70" aria-hidden />
            <div className="bg-grid absolute inset-0 opacity-40" aria-hidden />
            <div className="relative max-w-2xl">
              <span className="kicker inline-flex items-center gap-2 text-gold"><Chart width={14} height={14} /> Deep analytics</span>
              <h2 className="display mt-3 text-3xl md:text-4xl text-fg">Enter the live analytics dashboard</h2>
              <p className="mt-3 text-fg2">Explore the full knockout bracket, champion & finalist forecasts, live XGBoost matchup predictions, team dossiers, forecast evolution, model diagnostics, and system health — all updating from the real tournament.</p>
              <div className="mt-6 flex flex-wrap gap-3">
                {process.env.NEXT_PUBLIC_DASHBOARD_URL && <a href={process.env.NEXT_PUBLIC_DASHBOARD_URL} target="_blank" rel="noreferrer" className="btn btn-gold">Enter Live Dashboard <Arrow width={16} height={16} /></a>}
                <Link href="/methodology" className="btn btn-ghost">Open the Analytics Lab <Lab width={16} height={16} /></Link>
              </div>
            </div>
          </div>
        </Section>
      </div>
    </>
  );
}
