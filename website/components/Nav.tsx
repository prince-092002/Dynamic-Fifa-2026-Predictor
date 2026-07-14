"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Trophy, Team, Lab, Globe, Github, Arrow, Sim, Chart, Menu, Close } from "./icons";
import Crest from "./Crest";

const LINKS = [
  { href: "/", label: "Home", icon: <Trophy width={15} height={15} /> },
  { href: "/#bracket", label: "Bracket", icon: <Route16 /> },
  { href: "/prediction-history", label: "Prediction History", icon: <Chart width={15} height={15} /> },
  { href: "/teams", label: "Teams", icon: <Team width={15} height={15} /> },
  { href: "/scenario-lab", label: "Scenario Lab", icon: <Sim width={15} height={15} /> },
  { href: "/methodology", label: "Analytics Lab", icon: <Lab width={15} height={15} /> },
  { href: "/about", label: "About", icon: <Globe width={15} height={15} /> },
];

function Route16() {
  return <svg width={15} height={15} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="18" r="2.2" /><circle cx="18" cy="6" r="2.2" /><path d="M8 18h6a3 3 0 0 0 3-3V9" /></svg>;
}

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const dashboard = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
  const github = process.env.NEXT_PUBLIC_GITHUB_URL || "";
  return (
    <header className="site-header sticky top-0 z-50">
      <nav className="site-nav" aria-label="Main navigation">
        <Link href="/" className="site-brand" aria-label="FIFA 2026 Intelligence home">
          <Crest width={38} height={38} className="site-brand-mark" />
          <span className="site-brand-copy">
            <strong>FIFA 2026</strong>
            <small>Intelligence</small>
          </span>
        </Link>

        <ul className="site-primary-nav">
          {LINKS.map((link) => {
            const active = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href.split("#")[0]) && link.href !== "/#bracket");
            return (
              <li key={link.label}>
                <Link href={link.href} aria-current={active ? "page" : undefined} className={`site-nav-link ${active ? "is-active" : ""}`}>
                  <span className="site-nav-icon">{link.icon}</span>
                  <span>{link.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="site-nav-actions">
          {dashboard && (
            <a href={dashboard} target="_blank" rel="noreferrer" className="site-dashboard-cta">
              <span>Live Dashboard</span><Arrow width={15} height={15} />
            </a>
          )}
          {github && (
            <a href={github} target="_blank" rel="noreferrer" aria-label="Open GitHub repository" title="GitHub repository" className="site-github-action">
              <Github width={18} height={18} />
            </a>
          )}
        </div>

        <button
          type="button"
          className="site-menu-trigger"
          onClick={() => setOpen((current) => !current)}
          aria-expanded={open}
          aria-controls="site-mobile-menu"
          aria-label={open ? "Close navigation menu" : "Open navigation menu"}
        >
          {open ? <Close width={20} height={20} /> : <Menu width={20} height={20} />}
        </button>

        <div id="site-mobile-menu" className={`site-mobile-menu ${open ? "is-open" : ""}`}>
          <ul>
            {LINKS.map((link) => {
              const active = pathname === link.href || (link.href !== "/" && pathname.startsWith(link.href.split("#")[0]) && link.href !== "/#bracket");
              return (
                <li key={link.label}>
                  <Link href={link.href} onClick={() => setOpen(false)} aria-current={active ? "page" : undefined} className={`site-mobile-link ${active ? "is-active" : ""}`}>
                    <span>{link.icon}</span><span>{link.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
          {(dashboard || github) && (
            <div className="site-mobile-actions">
              {dashboard && (
                <a href={dashboard} target="_blank" rel="noreferrer" className="site-dashboard-cta" onClick={() => setOpen(false)}>
                  <span>Live Dashboard</span><Arrow width={15} height={15} />
                </a>
              )}
              {github && (
                <a href={github} target="_blank" rel="noreferrer" className="site-mobile-github" onClick={() => setOpen(false)}>
                  <Github width={18} height={18} /><span>GitHub repository</span>
                </a>
              )}
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}
