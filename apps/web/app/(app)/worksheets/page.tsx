import { Body, NotYet, PageHeader } from "@/components/shell";
import { tableCounts } from "@/lib/queries";

export default async function WorksheetsPage() {
  const c = await tableCounts();
  return (
    <>
      <PageHeader
        stage="Stage 2 · Print"
        title="Worksheets"
        sub="This week's sheet for each child, with the reason it was chosen, and the pack the teacher approves before it prints."
      />
      <Body>
        <NotYet
          what={[
            "One row per child: the skill set and difficulty prescribed, and the rule that chose it.",
            "The pack in handout order: named sheets, spares per difficulty, one teacher key.",
            "Approve the pack, or change one child in words and only that child re-runs.",
          ]}
          when="Arrives with W2, assemble and print. It reads the prescriptions W4 writes each Friday; before that, the CLI renders sheets from the bank."
          facts={[
            ["prescriptions", c.prescription],
            ["sheet instances", c.sheet_instance],
            ["children on roll", c.child],
          ]}
        />
      </Body>
    </>
  );
}
