import { Body, NotYet, PageHeader } from "@/components/shell";
import { tableCounts } from "@/lib/queries";

export default async function GrowthPage() {
  const c = await tableCounts();
  return (
    <>
      <PageHeader
        stage="Stage 4 · Understand"
        title="Child Growth"
        sub="One child: what they can do on each rung, in six states, and what changed since last week."
      />
      <Body>
        <NotYet
          what={[
            "The map: every rung with its state, not enough yet through stretch ready, and the evidence behind each.",
            "The trajectory across assessments, and the narrative observations a teacher wrote or the reader saw.",
            "The next prescribed sheet, and why.",
          ]}
          when="Arrives with W3's graph rebuild. The first maps come from the legacy import checked against Aseem's five reports."
          facts={[
            ["children on roll", c.child],
            ["evidence events", c.evidence_event],
            ["skill states", c.child_skill_state],
          ]}
        />
      </Body>
    </>
  );
}
