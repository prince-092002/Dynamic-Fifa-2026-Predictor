"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Trophy, Team, Lab, Globe, Github, Arrow, Sim } from "./icons";
import Crest from "./Crest";

const LINKS = [
  { href: "/", label: "Home", icon: <Trophy width={16} height={16} /> },
  { href: "/#bracket", label: "Bracket", icon: <Route16 /> },
  { href: "/teams", label: "Teams", icon: <Team width={16} height={16} /> },
  { href: "/scenario-lab", label: "Scenario Lab", icon: <Sim width={16} height={16} /> },
  { href: "/methodology", label: "Analytics Lab", icon: <Lab width={16} height={16} /> },
  { href: "/about", label: "About", icon: <Globe width={16} height={16} /> },
];

function Route16() {
  return <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="18" r="2.2" /><circle cx="18" cy="6" r="2.2" /><path d="M8 18h6a3 3 0 0 0 3-3V9" /></svg>;
}

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  return (
    <header className="sticky top-0 z-50 border-b border-line/70 bg-bg/80 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-[78rem] items-center justify-between px-4 py-3" aria-label="Main">
        <Link href="/" className="group flex items-center gap-2.5">
          <Crest width={40} height={40} className="shrink-0 drop-shadow-[0_8px_20px_rgba(245,196,81,0.35)]" />
          <span className="font-display text-sm font-bold tracking-tight">
            FIFA 2026 <span className="text-fg3">Intelligence</span>
          </span>
        </Link>

        <button className="rounded-lg border border-line-strong px-3 py-1.5 text-sm md:hidden" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Toggle menu">Menu</button>

        <ul className={`${open ? "flex" : "hidden"} absolute left-0 top-full w-full flex-col gap-1 border-b border-line bg-bg2 p-4 md:static md:flex md:w-auto md:flex-row md:items-center md:gap-1 md:border-0 md:bg-transparent md:p-0`}>
          {LINKS.map((l) => {
            const active = pathname === l.href || (l.href !== "/" && pathname.startsWith(l.href.split("#")[0]) && l.href !== "/#bracket");
            return (
              <li key={l.label}>
                <Link href={l.href} onClick={() => setOpen(false)} aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${active ? "bg-surface text-fg" : "text-fg2 hover:bg-surface/60 hover:text-fg"}`}>
                  <span className={active ? "text-cyan" : "text-fg3"}>{l.icon}</span>{l.label}
                </Link>
              </li>
            );
          })}
          {dashboard && (
            <li className="md:ml-2">
              <a href={dashboard} target="_blank" rel="noreferrer" className="btn btn-primary !py-2 !px-3.5 text-sm">
                Live Dashboard <Arrow width={15} height={15} />
              </a>
            </li>
          )}
          {github && (
            <li>
              <a href={github} target="_blank" rel="noreferrer" aria-label="GitHub repository" className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-fg2 hover:text-fg md:px-2">
                <Github width={17} height={17} />
              </a>
            </li>
          )}
        </ul>
      </nav>
    </header>
  );
}
