import type { SVGProps } from "react";

/* Professional inline-SVG icon set (stroke-based, currentColor). No emoji. */
type P = SVGProps<SVGSVGElement>;
const base = (p: P) => ({
  width: 20, height: 20, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, ...p,
});

export const Trophy = (p: P) => (<svg {...base(p)}><path d="M7 4h10v4a5 5 0 0 1-10 0V4Z"/><path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3"/><path d="M10 13v3M14 13v3M8 20h8M9 20a3 3 0 0 1 6 0"/></svg>);
export const Pitch = (p: P) => (<svg {...base(p)}><rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M12 5v14M3 9h3v6H3M21 9h-3v6h3"/><circle cx="12" cy="12" r="2.4"/></svg>);
export const Chart = (p: P) => (<svg {...base(p)}><path d="M4 4v16h16"/><path d="M8 15l3-4 3 2 4-6"/></svg>);
export const Bolt = (p: P) => (<svg {...base(p)}><path d="M13 3 5 13h5l-1 8 8-11h-5l1-7Z"/></svg>);
export const Shield = (p: P) => (<svg {...base(p)}><path d="M12 3 5 6v5c0 4.2 3 7.3 7 9 4-1.7 7-4.8 7-9V6l-7-3Z"/><path d="m9.5 12 1.8 1.8L15 10"/></svg>);
export const Calendar = (p: P) => (<svg {...base(p)}><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/></svg>);
export const Network = (p: P) => (<svg {...base(p)}><circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="6" r="2.4"/><circle cx="12" cy="18" r="2.4"/><path d="M7.6 7.6 10.4 16M16.4 7.6 13.6 16M8 6h8"/></svg>);
export const Database = (p: P) => (<svg {...base(p)}><ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/></svg>);
export const Sim = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18M8 8l2 4-2 4M16 8l-2 4 2 4"/></svg>);
export const Team = (p: P) => (<svg {...base(p)}><circle cx="9" cy="8" r="3"/><path d="M3 20a6 6 0 0 1 12 0"/><path d="M16 6a3 3 0 0 1 0 6M22 20a6 6 0 0 0-4-5.7"/></svg>);
export const Globe = (p: P) => (<svg {...base(p)}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.7 3.8 9S14.5 18.5 12 21c-2.5-2.5-3.8-5.7-3.8-9S9.5 5.5 12 3Z"/></svg>);
export const Tactics = (p: P) => (<svg {...base(p)}><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="9" r="1.3"/><circle cx="16" cy="9" r="1.3"/><circle cx="12" cy="15" r="1.3"/><path d="m8 9 4 6 4-6"/></svg>);
export const Lab = (p: P) => (<svg {...base(p)}><path d="M9 3h6M10 3v6l-5 8a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-8V3"/><path d="M7.5 15h9"/></svg>);
export const Gauge = (p: P) => (<svg {...base(p)}><path d="M4 18a8 8 0 1 1 16 0"/><path d="m12 14 3.5-3.5"/><circle cx="12" cy="18" r="1"/></svg>);
export const Route = (p: P) => (<svg {...base(p)}><circle cx="6" cy="18" r="2.2"/><circle cx="18" cy="6" r="2.2"/><path d="M8 18h6a3 3 0 0 0 3-3V9M8.2 16.5 16 8"/></svg>);
export const Arrow = (p: P) => (<svg {...base(p)}><path d="M5 12h14M13 6l6 6-6 6"/></svg>);
export const Check = (p: P) => (<svg {...base(p)}><path d="m5 12 4.5 4.5L19 7"/></svg>);
export const Lock = (p: P) => (<svg {...base(p)}><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>);
export const Signal = (p: P) => (<svg {...base(p)}><path d="M5 20v-4M10 20v-8M15 20v-12M20 20V6"/></svg>);
export const Github = (p: P) => (<svg {...base(p)}><path d="M9 19c-4 1.2-4-2-6-2m12 4v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6 0C6.9 1 5.9 1.3 5.9 1.3a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 4.5 7.7c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V19"/></svg>);
export const Menu = (p: P) => (<svg {...base(p)}><path d="M4 7h16M4 12h16M4 17h16"/></svg>);
export const Close = (p: P) => (<svg {...base(p)}><path d="m6 6 12 12M18 6 6 18"/></svg>);
