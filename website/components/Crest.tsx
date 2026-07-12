// Original WC26 crest mark (Medallion) — trophy · star · pitch arc in the project palette.
// In-repo SVG artwork. Not a FIFA logo/emblem; implies no official affiliation.

export default function Crest({
  width = 40,
  height = 40,
  className,
}: {
  width?: number;
  height?: number;
  className?: string;
}) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label="WC26 crest"
      fill="none"
    >
      <defs>
        <linearGradient id="wc26-gold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fbe6a3" />
          <stop offset=".5" stopColor="#f5c451" />
          <stop offset="1" stopColor="#d99a2f" />
        </linearGradient>
        <radialGradient id="wc26-field" cx=".5" cy=".36" r=".78">
          <stop offset="0" stopColor="#182742" />
          <stop offset="1" stopColor="#060a13" />
        </radialGradient>
        <linearGradient id="wc26-pitch" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#29d17f" />
          <stop offset="1" stopColor="#38bdf8" />
        </linearGradient>
      </defs>
      {/* badge */}
      <circle cx="32" cy="32" r="30" fill="url(#wc26-field)" stroke="url(#wc26-gold)" strokeWidth="2.5" />
      <circle cx="32" cy="32" r="25.5" fill="none" stroke="#38bdf8" strokeOpacity=".32" strokeWidth="1" />
      {/* star */}
      <path
        d="M32 6.4 33.47 9.98 37.33 10.27 34.38 12.77 35.29 16.53 32 14.5 28.71 16.53 29.62 12.77 26.67 10.27 30.53 9.98Z"
        fill="url(#wc26-gold)"
      />
      {/* trophy */}
      <path d="M23 19C17.4 19 17.4 28 23 28" fill="none" stroke="url(#wc26-gold)" strokeWidth="2" />
      <path d="M41 19C46.6 19 46.6 28 41 28" fill="none" stroke="url(#wc26-gold)" strokeWidth="2" />
      <path d="M22.5 18h19v3.6c0 7.4-4 11.6-9.5 11.6s-9.5-4.2-9.5-11.6z" fill="url(#wc26-gold)" />
      <rect x="30.3" y="33.2" width="3.4" height="3.4" fill="url(#wc26-gold)" />
      <path d="M27.4 40 28.8 36.6h6.4L36.6 40z" fill="url(#wc26-gold)" />
      <rect x="25.8" y="40" width="12.4" height="2.3" rx="1.1" fill="url(#wc26-gold)" />
      {/* pitch arc + centre spot */}
      <path d="M18 46.2C24.5 50.8 39.5 50.8 46 46.2" fill="none" stroke="url(#wc26-pitch)" strokeWidth="2" strokeLinecap="round" />
      <circle cx="32" cy="48.1" r="1.15" fill="url(#wc26-pitch)" />
    </svg>
  );
}
