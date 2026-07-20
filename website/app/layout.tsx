import type { Metadata } from "next";
import { Space_Grotesk, Inter, Anton } from "next/font/google";
import "flag-icons/css/flag-icons.min.css";
import "./globals.css";
import Nav from "@/components/Nav";
import Footer from "@/components/Footer";

const display = Space_Grotesk({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-display" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
// Tall, geometric, high-impact display face used only for the hero "FIFA 2026" title.
const poster = Anton({ subsets: ["latin"], weight: "400", variable: "--font-poster" });

const TITLE = "Spain Win the FIFA World Cup | Dynamic FIFA 2026 Predictor";
const DESCRIPTION =
  "The completed Dynamic FIFA 2026 Tournament Outcome Predictor records Spain as world champions after a 1–0 extra-time victory over Argentina. The model's final pre-match simulation gave Spain a 51.9% championship probability. Independent analytics project — not affiliated with FIFA.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    type: "website",
    siteName: "Dynamic FIFA 2026 Predictor",
  },
  twitter: {
    card: "summary",
    title: TITLE,
    description: DESCRIPTION,
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${poster.variable}`}>
      <body className="min-h-screen antialiased">
        <div className="bg-stadium" aria-hidden />
        <Nav />
        <main>{children}</main>
        <Footer />
      </body>
    </html>
  );
}
