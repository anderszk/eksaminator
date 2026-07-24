import type { Metadata } from "next";
import { Inter, Playfair_Display, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/ui/nav";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Eksaminator",
  description: "Tren på masterforsvaret ditt",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nb" className={`${inter.variable} ${playfair.variable} ${jetbrains.variable}`}>
      <body>
        <Nav />
        <div style={{ paddingTop: "56px" }}>
          {children}
        </div>
      </body>
    </html>
  );
}
