import { Body, NotYet, PageHeader } from "@/components/shell";
import { tableCounts } from "@/lib/queries";

export default async function CapturePage() {
  const c = await tableCounts();
  return (
    <>
      <PageHeader
        stage="Stage 3 · Read"
        title="Capture & Mark"
        sub="Photos as they arrive, which sheet and child each one resolved to, and the few answers the reader was not sure of."
      />
      <Body>
        <NotYet
          what={[
            "The feed: each photo, its QR, the child it resolved to, or needs a re-photo.",
            "The confirm queue: only the reads below the confidence line, one tap each, or accept all above it.",
            "The clock: minutes of teacher attention this class needed this week.",
          ]}
          when="Arrives with W3, read and graph. The first photos will be the legacy import of the 37 real papers (N3)."
          facts={[
            ["captures", c.capture],
            ["item results", c.item_result],
            ["evidence events", c.evidence_event],
          ]}
        />
      </Body>
    </>
  );
}
