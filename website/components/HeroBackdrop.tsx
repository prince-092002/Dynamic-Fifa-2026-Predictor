"use client";

// Fixed homepage hero background — a floodlit stadium + trophy photograph, with dark
// scrim/vignette layers so the foreground content stays readable. The image is a
// user-supplied generic trophy/stadium render (not an official FIFA trophy or logo).
// The layer is position:fixed and scroll-fades as you leave the hero so it never bleeds
// into the sections below.

import { useEffect, useState } from "react";

export default function HeroBackdrop() {
  const [opacity, setOpacity] = useState(1);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let raf = 0;
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const fade = window.innerHeight * 0.85;
        setOpacity(Math.max(0, 1 - window.scrollY / fade));
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); cancelAnimationFrame(raf); };
  }, []);

  return (
    <div className="hero-backdrop" style={{ opacity }} aria-hidden>
      <div className="hero-photo" />
      <div className="hero-scrim" />
    </div>
  );
}
