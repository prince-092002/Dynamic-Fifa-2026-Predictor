import type { Metadata } from "next";
import { Space_Grotesk, Inter } from "next/font/google";
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const display = Space_Grotesk({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-display" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata: Metadata = {
  title: "Dynamic FIFA 2026 — Tournament Intelligence Platform",
  description:
    "A live football intelligence platform combining ~50,000 historical matches, Elo ratings, XGBoost matchup probabilities, and Monte Carlo simulation to forecast the FIFA World Cup 2026. Independent analytics project — not affiliated with FIFA.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body className="min-h-screen antialiased">
        <div className="bg-stadium" aria-hidden />
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
