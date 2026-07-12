# Asset Inventory & Governance

## Imagery approach

This redesign uses **no stock photographs and no official FIFA/World Cup artwork**. All football atmosphere (night stadium, floodlights, pitch geometry, grid) is generated in **CSS and inline SVG data-URIs**, authored in-repo. The only bundled imagery is **country flags** (public-domain national flags via the open-source `flag-icons` library). This was a deliberate choice:

- **Zero trademark risk** — no FIFA/World Cup logos, emblems, posters, or trademarked artwork; only public-domain country flags and in-repo CSS/SVG.
- **Minimal external footprint** — atmosphere is CSS/SVG; flags ship with the app (no runtime CDN).
- **Fully brand-safe** — football-tournament-*inspired*, never implying official affiliation.

> **Governance note:** an official FIFA World Cup 2026 emblem PNG was present in an earlier working draft and was **removed** before publication (it violated the no-official-artwork rule). The site logo mark is the in-repo `Trophy` SVG icon.

| Asset | Type | Location | Purpose | Source | License |
|---|---|---|---|---|---|
| Floodlit stadium canvas | CSS radial gradients + SVG pitch lines (data-URI) | `website/app/globals.css` `.bg-stadium` | Global page atmosphere | Authored in-repo | Project-owned |
| Section floodlight / grid / pitch-glow | CSS | `globals.css` `.bg-floodlight/.bg-grid/.bg-pitch-glow` | Hero, CTA, page-header atmosphere | Authored in-repo | Project-owned |
| Icon set (20 icons) | Inline SVG | `website/components/icons.tsx`, `dashboard/theme.py` | Professional iconography (no emoji) | Authored in-repo | Project-owned |
| Dashboard stadium canvas | CSS gradients | `dashboard/theme.py` `inject_theme()` | Dashboard atmosphere | Authored in-repo | Project-owned |
| Country flags (website) | SVG via `flag-icons` CSS | `website/components/CountryFlag.tsx` (ISO code → flag) | Team identity | [flag-icons](https://github.com/lipis/flag-icons) | MIT (public-domain flags) |
| Country flags (dashboard) | SVG files | `dashboard/assets/flags/*.svg` | Team identity | Public-domain national flags | Public domain |
| Fonts: Space Grotesk, Inter | Web fonts | `next/font/google` (website), Google Fonts `@import` (dashboard) | Typography | Google Fonts | SIL Open Font License (freely usable; not redistributed as files) |

## Optional real-photo slot (documented, not required)

If licensed hero photography is desired later:

1. Create `website/public/images/` and add optimized images (e.g. `hero-stadium.webp`, ≤ ~200 KB, 1920px wide).
2. In the hero `<section>` of `website/app/page.tsx`, add a background layer:
   ```tsx
   <div className="absolute inset-0 bg-cover bg-center opacity-30"
        style={{ backgroundImage: "url(/images/hero-stadium.webp)" }} aria-hidden />
   ```
   keep the existing `.bg-floodlight` overlay above it for text contrast.
3. Record the file, source URL, license, and attribution in this table.
4. **Only use** properly licensed generic football imagery (e.g. Unsplash/Pexels license, or owned photography). **Never** use official FIFA/World Cup posters, logos, or trademarked artwork.

The site is fully complete and premium without any photos; this slot is purely optional enhancement.
