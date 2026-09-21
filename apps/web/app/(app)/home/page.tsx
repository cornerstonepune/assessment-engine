import { Body, NotYet, PageHeader } from "@/components/shell";
import { tableCounts } from "@/lib/queries";
import { deadline } from "@/lib/deadline";

export default async function HomePage() {
  const c = await deadline(tableCounts());
  return (
    <>
      <PageHeader
        stage="Stage 5 · Home"
        title="Home Assignments"
        sub="Friday evening: the home sheet aimed at each child's recurring pattern, and the note a parent reads."
      />
      <Body>
        <NotYet
          what={[
            "Per child: the home sheet, the pattern it targets, and the parent note draft in the school's voice.",
            "One batch approval for the class; edit any single note before it goes.",
          ]}
          when="Arrives with W4, close the loop, after Thursday's practice and Friday's assessment have both been read."
          facts={[
            ["home sheets", c.home_sheet],
            ["parent notes", c.parent_note],
          ]}
        />
      </Body>
    </>
  );
}
