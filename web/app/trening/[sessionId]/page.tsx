import { nb } from "@/lib/nb";

export default function TreningPage({ params }: { params: { sessionId: string } }) {
  return (
    <div>
      <p>Trening — {params.sessionId}</p>
    </div>
  );
}
