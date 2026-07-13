// Fixed "poster" hero backdrop for the homepage.
//
// Brand & rights safety: these are ORIGINAL, generic footballer SILHOUETTES drawn in
// SVG — not photographs, and not the likeness of any real, identifiable person. No FIFA
// or club artwork is used. A documented slot for *licensed* player photography exists in
// docs/design/ASSET_INVENTORY.md if real imagery is ever properly licensed.

// One reusable athletic footballer silhouette (feet at y=300, centred on x=60).
const BALLER =
  "M60 23a17 17 0 1 1 0 34 17 17 0 0 1 0-34Z" + // head
  "M41 64Q60 53 79 64L74 150Q60 158 46 150Z" + // jersey/torso
  "M42 66Q30 92 31 130Q31 139 38 138Q45 137 46 116Q48 86 53 70Z" + // left arm
  "M78 66Q90 92 89 130Q89 139 82 138Q75 137 74 116Q72 86 67 70Z" + // right arm
  "M46 150L43 293Q43 300 50 300L57 300Q60 300 59 291L59 152Q52 156 46 150Z" + // left leg
  "M74 150L77 293Q77 300 70 300L63 300Q60 300 61 291L61 152Q68 156 74 150Z"; // right leg

/** place the silhouette so its feet land on `baseY` at horizontal centre `cx`. */
function figure(cx: number, baseY: number, scale: number, flip: boolean, key: string) {
  const t = `translate(${cx} ${baseY}) scale(${flip ? -scale : scale} ${scale}) translate(-60 -300)`;
  return <path key={key} d={BALLER} transform={t} fill="url(#silFill)" />;
}

export default function HeroBackdrop() {
  return (
    <div className="hero-backdrop" aria-hidden>
      <div className="beam" />
      <svg className="figures" viewBox="0 0 1280 360" preserveAspectRatio="xMidYMax meet" role="presentation">
        <defs>
          <linearGradient id="silFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#33456a" stopOpacity="0" />
            <stop offset="0.32" stopColor="#2a3a5c" stopOpacity="0.5" />
            <stop offset="0.72" stopColor="#1a2740" stopOpacity="0.92" />
            <stop offset="1" stopColor="#0a1120" stopOpacity="1" />
          </linearGradient>
          <radialGradient id="spot" cx="0.5" cy="1" r="0.9">
            <stop offset="0" stopColor="#29d17f" stopOpacity="0.16" />
            <stop offset="1" stopColor="#29d17f" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* pitch-light pool the players stand in */}
        <ellipse cx="640" cy="352" rx="560" ry="70" fill="url(#spot)" />

        {/* walkout line — four figures, varied scale & facing, one with a ball */}
        {figure(250, 342, 1.02, false, "a")}
        {figure(500, 348, 1.14, true, "b")}
        {figure(775, 340, 1.0, false, "c")}
        {figure(1015, 346, 1.09, true, "d")}

        {/* match ball at the near player's feet (original geometry) */}
        <g transform="translate(300 330)" opacity="0.9">
          <circle r="15" fill="#0d1524" stroke="#33456a" strokeWidth="1.2" />
          <path d="M0 -8 6.6 -2.2 4.2 6.4 -4.2 6.4 -6.6 -2.2Z" fill="#223049" />
        </g>
      </svg>
      <div className="floor" />
    </div>
  );
}
