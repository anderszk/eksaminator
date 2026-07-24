import Link from "next/link";
import { nb } from "@/lib/nb";

export default function Nav() {
  return (
    <nav>
      <Link href="/opplasting">{nb.nav.last_opp}</Link>
      <Link href="/oversikt">{nb.nav.oversikt}</Link>
    </nav>
  );
}
