import { nb } from "@/lib/nb";

export default function EksamenPage({ params }: { params: { sessionId: string } }) {
  return (
    <div>
      <p>Eksamen — {params.sessionId}</p>
    </div>
  );
}
