import { nb } from "@/lib/nb";

export default function OversiktPage() {
  return (
    <div>
      <h1>Oversikt</h1>
      <p>{nb.empty.sessions}</p>
    </div>
  );
}
