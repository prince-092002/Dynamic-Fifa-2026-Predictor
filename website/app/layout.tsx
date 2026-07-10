import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Dynamic FIFA 2026 Tournament Outcome Predictor",
  description:
    "A live machine-learning forecasting system combining real tournament results, XGBoost matchup probabilities, and Monte Carlo simulation. Independent analytics project — not affiliated with FIFA.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <Nav />
        <main className="mx-auto max-w-6xl px-4">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
