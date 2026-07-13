"use client";

// Cinematic "semifinal poster" hero backdrop.
//
// Rights & brand safety: each figure is an ORIGINAL, generic footballer rendered in a
// nation's KIT COLOURS (Argentina, France, Spain, England) — no facial features are drawn,
// so no real person's likeness is reproduced, and no photograph or copyrighted image is
// used. The players are identified the way a lineup graphic does it: by nation, shirt
// number and name (factual — these four are genuinely in the semifinals). No FIFA/club
// artwork; independent project, not affiliated with FIFA.

import { useEffect, useState } from "react";

type Kit = {
  key: string;
  jersey: string;
  stripe?: string;
  number: string;
  numberColor: string;
  shorts: string;
  socks: string;
  cx: number;
  scale: number;
  flip: boolean;
  ball?: boolean;
};

const SKIN = "#c99a6b";
const HAIR = "#241a12";
const BOOT = "#12151c";

// Argentina (Messi 10) · France (Mbappé 10) · Spain (Yamal 19) · England (Kane 9)
const KITS: Kit[] = [
  { key: "arg", jersey: "#eaf3fb", stripe: "#57b4e6", number: "10", numberColor: "#0b1b3a", shorts: "#101a2e", socks: "#eaf3fb", cx: 168, scale: 1.16, flip: false, ball: true },
  { key: "fra", jersey: "#20439c", number: "10", numberColor: "#eaf3fb", shorts: "#eef2f8", socks: "#b0142c", cx: 470, scale: 1.24, flip: true },
  { key: "esp", jersey: "#c8102e", number: "19", numberColor: "#ffd24a", shorts: "#0b2a6b", socks: "#0b1b2b", cx: 812, scale: 1.24, flip: false },
  { key: "eng", jersey: "#f4f7fb", number: "9", numberColor: "#14203a", shorts: "#14203a", socks: "#f4f7fb", cx: 1114, scale: 1.16, flip: true },
];

const BASE_Y = 372;

function Player(k: Kit) {
  const t = `translate(${k.cx} ${BASE_Y}) scale(${k.flip ? -k.scale : k.scale} ${k.scale}) translate(-60 -300)`;
  return (
    <g transform={t} key={k.key}>
      {/* boots */}
      <path d="M42 286q-4 0 -4 6l1 5q1 3 7 3h9q3 0 2-6l-2-8Z" fill={BOOT} />
      <path d="M78 286q4 0 4 6l-1 5q-1 3-7 3h-9q-3 0-2-6l2-8Z" fill={BOOT} />
      {/* socks */}
      <path d="M43 244l2 44h11l-1-44Z" fill={k.socks} />
      <path d="M77 244l-2 44H64l1-44Z" fill={k.socks} />
      {/* thighs (skin) */}
      <path d="M45 186l-2 60h12l1-60Z" fill={SKIN} />
      <path d="M75 186l2 60H65l-1-60Z" fill={SKIN} />
      {/* shorts */}
      <path d="M44 148q16 8 32 0l3 42q-19 7-38 0Z" fill={k.shorts} />
      {/* arms (skin) */}
      <path d="M41 64q-11 27-8 63q0 8 6 7q6-1 7-21q1-27 4-45Z" fill={SKIN} />
      <path d="M79 64q11 27 8 63q0 8-6 7q-6-1-7-21q-1-27-4-45Z" fill={SKIN} />
      {/* jersey */}
      <path d="M40 60q20-10 40 0l-3 92q-17 8-34 0Z" fill={k.jersey} />
      {/* argentina stripes */}
      {k.stripe && (
        <>
          <path d="M51 57l-2 96h6l2-96Z" fill={k.stripe} opacity="0.92" />
          <path d="M63 56l0 97h6l-1-97Z" fill={k.stripe} opacity="0.92" />
        </>
      )}
      {/* sleeve caps */}
      <path d="M40 60q-6 6-4 18l10-5-2-13Z" fill={k.jersey} />
      <path d="M80 60q6 6 4 18l-10-5 2-13Z" fill={k.jersey} />
      {/* number */}
      <text x="60" y="116" textAnchor="middle" fontFamily="system-ui, sans-serif" fontWeight="800" fontSize="30" fill={k.numberColor}>{k.number}</text>
      {/* neck + head (no facial features) */}
      <rect x="55" y="52" width="10" height="9" fill={SKIN} />
      <circle cx="60" cy="41" r="15" fill={SKIN} />
      <path d="M45 41q2-17 15-17t15 17q-5-7-15-7t-15 7Z" fill={HAIR} />
    </g>
  );
}

export default function HeroBackdrop() {
  const [opacity, setOpacity] = useState(1);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const fade = window.innerHeight * 0.82;
        setOpacity(Math.max(0, 1 - window.scrollY / fade));
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(raf); };
  }, []);

  return (
    <div className="hero-backdrop" style={{ opacity }} aria-hidden>
      <div className="beam" />
      <svg className="figures" viewBox="0 0 1280 396" preserveAspectRatio="xMidYMax slice" role="presentation">
        <defs>
          <radialGradient id="pool" cx="0.5" cy="1" r="0.85">
            <stop offset="0" stopColor="#29d17f" stopOpacity="0.18" />
            <stop offset="1" stopColor="#29d17f" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="ground" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0a1120" stopOpacity="0" />
            <stop offset="1" stopColor="#05080f" stopOpacity="0.9" />
          </linearGradient>
        </defs>
        <ellipse cx="640" cy="384" rx="620" ry="72" fill="url(#pool)" />
        {KITS.map(Player)}
        {/* match ball at the near player's feet */}
        <g transform="translate(228 360)">
          <circle r="15" fill="#f4f7fb" stroke="#c3ccd8" strokeWidth="1" />
          <path d="M0 -7 6.1 -2.1 3.8 6 -3.8 6 -6.1 -2.1Z" fill="#14203a" />
        </g>
        <rect x="0" y="330" width="1280" height="66" fill="url(#ground)" />
      </svg>
      <div className="floor" />
    </div>
  );
}
