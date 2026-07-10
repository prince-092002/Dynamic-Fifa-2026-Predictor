"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/#forecast", label: "Live Forecast" },
  { href: "/#bracket", label: "Bracket" },
  { href: "/teams", label: "Teams" },
  { href: "/methodology", label: "Methodology" },
  { href: "/about", label: "About" },
];

export const DASHBOARD_URL = process.env.NEXT_PUBLIC_DASHBOARD_URL || "";
export const GITHUB_URL = process.env.NEXT_PUBLIC_GITHUB_URL || "";

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-bg/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3" aria-label="Main navigation">
        <Link href="/" className="flex items-center gap-2 font-bold tracking-tight">
          <span aria-hidden>⚽</span>
          <span className="bg-gradient-to-r from-cyan to-magenta bg-clip-text text-transparent">FIFA 2026 Predictor</span>
        </Link>
        <button
          className="rounded border border-line px-3 py-1 text-sm md:hidden"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label="Toggle navigation menu"
        >
          Menu
        </button>
        <ul className={`${open ? "flex" : "hidden"} absolute left-0 top-full w-full flex-col gap-1 border-b border-line bg-bg2 p-4 md:static md:flex md:w-auto md:flex-row md:items-center md:gap-5 md:border-0 md:bg-transparent md:p-0`}>
          {LINKS.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                onClick={() => setOpen(false)}
                aria-current={pathname === link.href ? "page" : undefined}
                className={`text-sm transition-colors hover:text-cyan ${pathname === link.href ? "font-semibold text-cyan" : "text-fg2"}`}
              >
                {link.label}
              </Link>
            </li>
          ))}
          {DASHBOARD_URL && (
            <li>
              <a href={DASHBOARD_URL} target="_blank" rel="noreferrer" className="rounded bg-cyan/15 px-3 py-1.5 text-sm font-semibold text-cyan hover:bg-cyan/25">
                Dashboard ↗
              </a>
            </li>
          )}
          {GITHUB_URL && (
            <li>
              <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="text-sm text-fg2 hover:text-cyan">
                GitHub ↗
              </a>
            </li>
          )}
        </ul>
      </nav>
    </header>
  );
}
