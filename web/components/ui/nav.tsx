"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { nb } from "@/lib/nb";

const links = [
  { href: "/opplasting",  label: nb.nav.last_opp,  icon: UploadIcon },
  { href: "/oversikt",    label: nb.nav.oversikt,   icon: GridIcon },
  { href: "/bibliotek",   label: nb.nav.bibliotek,  icon: BookIcon },
  { href: "/trening",     label: nb.nav.trening,    icon: MicIcon },
  { href: "/eksamen",     label: nb.nav.eksamen,    icon: TimerIcon },
];

export default function Nav() {
  const path = usePathname();

  return (
    <header style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      height: "56px",
      background: "rgba(250,249,245,0.88)",
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      borderBottom: "1px solid var(--border)",
      zIndex: 100,
      display: "flex",
      alignItems: "center",
      padding: "0 24px",
    }}>
      {/* Brand */}
      <Link href="/oversikt" style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        textDecoration: "none",
        color: "var(--ink)",
        fontWeight: 700,
        fontSize: "15px",
        letterSpacing: "-0.03em",
        marginRight: "32px",
        flexShrink: 0,
      }}>
        <span style={{
          width: "26px",
          height: "26px",
          background: "var(--ink)",
          borderRadius: "6px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--bg)",
          fontSize: "13px",
          fontWeight: 700,
        }}>E</span>
        Eksaminator
      </Link>

      {/* Nav links */}
      <nav style={{ display: "flex", alignItems: "center", gap: "2px", flex: 1 }}>
        {links.map(({ href, label, icon: Icon }) => {
          const active = path === href || path.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 11px",
                borderRadius: "var(--radius)",
                fontSize: "13.5px",
                fontWeight: active ? 500 : 400,
                color: active ? "var(--ink)" : "var(--ink-muted)",
                background: active ? "var(--bg-elevated)" : "transparent",
                textDecoration: "none",
                transition: "all var(--transition)",
              }}
              onMouseEnter={e => {
                if (!active) (e.currentTarget as HTMLElement).style.background = "var(--bg-hover)";
              }}
              onMouseLeave={e => {
                if (!active) (e.currentTarget as HTMLElement).style.background = "transparent";
              }}
            >
              <Icon size={14} />
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}

function UploadIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 11V3M5 6l3-3 3 3" />
      <path d="M2 13h12" />
    </svg>
  );
}

function GridIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="2" width="5" height="5" rx="1" />
      <rect x="9" y="2" width="5" height="5" rx="1" />
      <rect x="2" y="9" width="5" height="5" rx="1" />
      <rect x="9" y="9" width="5" height="5" rx="1" />
    </svg>
  );
}

function BookIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3a1 1 0 0 1 1-1h4.5a2.5 2.5 0 0 1 0 5H3a1 1 0 0 1-1-1V3Z" />
      <path d="M2 9a1 1 0 0 1 1-1h4.5a2.5 2.5 0 0 1 0 5H3a1 1 0 0 1-1-1V9Z" />
      <line x1="10" y1="4" x2="14" y2="4" />
      <line x1="10" y1="7" x2="14" y2="7" />
      <line x1="10" y1="10" x2="14" y2="10" />
      <line x1="10" y1="13" x2="14" y2="13" />
    </svg>
  );
}

function MicIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="5" y="1" width="6" height="9" rx="3" />
      <path d="M2 8a6 6 0 0 0 12 0" />
      <line x1="8" y1="14" x2="8" y2="15.5" />
      <line x1="5" y1="15.5" x2="11" y2="15.5" />
    </svg>
  );
}

function TimerIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="8" cy="9" r="6" />
      <path d="M8 6v3l2 1.5" />
      <path d="M6 1h4" />
      <path d="M8 1v2" />
    </svg>
  );
}
