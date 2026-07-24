import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/ui/nav";

export const metadata: Metadata = {
  title: "Eksaminator",
  description: "Masteroppgave forsvarstiener",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="nb">
      <body>
        <Nav />
        <main>{children}</main>
      </body>
    </html>
  );
}
