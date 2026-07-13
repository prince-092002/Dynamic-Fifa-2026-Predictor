# Asset Inventory & Governance

## Imagery approach

This redesign uses **no stock photographs and no official FIFA/World Cup artwork**. All football atmosphere (night stadium, floodlights, pitch geometry, grid) is generated in **CSS and inline SVG data-URIs**, authored in-repo. The only bundled imagery is **country flags** (public-domain national flags via the open-source `flag-icons` library). This was a deliberate choice:

- **Zero trademark risk** — no FIFA/World Cup logos, emblems, posters, or trademarked artwork; only public-domain country flags and in-repo CSS/SVG.
- **Minimal external footprint** — atmosphere is CSS/SVG; flags ship with the app (no runtime CDN).
- **Fully brand-safe** — football-tournament-*inspired*, never implying official affiliation.

> **Governance note:** an official FIFA World Cup 2026 emblem PNG was present in an earlier working draft and was **removed** before publication (it violated the no-official-artwork rule). The site logo mark is an **original in-repo WC26 crest** (`website/components/Crest.tsx`) — a trophy/star/pitch-arc badge drawn as inline SVG in the project palette. No trademarked artwork.

| Asset | Type | Location | Purpose | Source | License |
|---|---|---|---|---|---|
| Floodlit stadium canvas | CSS radial gradients + SVG pitch lines (data-URI) | `website/app/globals.css` `.bg-stadium` | Global page atmosphere | Authored in-repo | Project-owned |
| Section floodlight / grid / pitch-glow | CSS | `globals.css` `.bg-floodlight/.bg-grid/.bg-pitch-glow` | Hero, CTA, page-header atmosphere | Authored in-repo | Project-owned |
| Icon set (20 icons) | Inline SVG | `website/components/icons.tsx`, `dashboard/theme.py` | Professional iconography (no emoji) | Authored in-repo | Project-owned |
| Dashboard stadium canvas | CSS gradients | `dashboard/theme.py` `inject_theme()` | Dashboard atmosphere | Authored in-repo | Project-owned |
| Country flags (website) | SVG via `flag-icons` CSS | `website/components/CountryFlag.tsx` (ISO code → flag) | Team identity | [flag-icons](https://github.com/lipis/flag-icons) | MIT (public-domain flags) |
| Country flags (dashboard) | SVG files | `dashboard/assets/flags/*.svg` | Team identity | Public-domain national flags | Public domain |
| Hero background photo | JPEG (261 KB, 1672×941) | `website/public/images/hero-trophy.jpg` → `HeroBackdrop.tsx` | Fixed homepage hero background | User-supplied render | User-owned asset |
| Fonts: Space Grotesk, Inter | Web fonts | `next/font/google` (website), Google Fonts `@import` (dashboard) | Typography | Google Fonts | SIL Open Font License (freely usable; not redistributed as files) |

> **Hero imagery note:** the homepage fixed hero (`HeroBackdrop.tsx`) uses a **user-supplied stadium + trophy image** (`public/images/hero-trophy.jpg`), layered under dark scrim/vignette gradients for text readability and set to a fixed, scroll-fading background. It depicts a **generic gold trophy** — not the official FIFA World Cup Trophy design or any FIFA logo/emblem — and no player likenesses. The image is the user's own uploaded asset; usage rights are the site owner's responsibility. The "independent — not affiliated with FIFA" disclaimer is retained on the hero.

## Optional licensed-photo slot (documented, not required)

If **properly licensed** hero photography is desired later:

1. Create `website/public/images/` and add optimized images (e.g. `hero.webp`, ≤ ~250 KB, ~1920px wide).
2. In the hero `<section>` of `website/app/page.tsx` (behind `<HeroBackdrop />`), add a background layer:
   ```tsx
   <div className="fixed inset-0 -z-[1] bg-cover bg-center opacity-25"
        style={{ backgroundImage: "url(/images/hero.webp)" }} aria-hidden />
   ```
3. Record the file, source URL, license, and attribution in this table.
4. **Only use** imagery you have the rights to: generic/owned football photography or a stock license (Unsplash/Pexels/etc.). **Player photos** additionally require **publicity/likeness** clearance. **Never** use official FIFA/World Cup posters, logos, trademarked artwork, or unlicensed press/agency photos of real players.

The site is fully complete and premium without any photos; this slot is purely optional enhancement.
