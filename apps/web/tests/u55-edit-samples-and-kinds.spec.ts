/**
 * U55 — An educator changes a skill's samples, the kinds a level asks, and its words, on the skill's page
 * (goals/edt_edit_samples_and_kinds.yaml). Nimish, 2026-10-24: "Ayush goes on the curriculum page in an English thing.
 * Now he reads the whole thing. What happens if he wants to make any changes there? … Is that capability here, or is it
 * just blue? What does 'change the words first' do? It should simply have the capability to edit the skill, where the
 * nature or the description of the skill can be changed."
 *
 * At 1440 px, on an English Grade 4 skill approved at every level: Ayush changes a Hard sample's wrong answer, is told in
 * words why his first try fails and nothing is saved, fixes it, saves; only Hard waits for approval again, and is
 * approved again. A kind is added to a level only with three samples; a level's sentence is changed from the page; a
 * Maths skill says in words why its questions are not edited there. Approvals and words are put back after; an edit
 * is a version that is never deleted, so a run leaves the sample as it was saved.
 */
import { expect, test } from "@playwright/test";
import postgres from "postgres";

test.describe.configure({ mode: "serial" });
test.use({ viewport: { width: 1440, height: 900 } });
const sql = postgres(process.env.DATABASE_URL!, { max: 2 });

type Slot = { code: string; ord: number; answer: string; options: string[]; wrong: string[] };
let slot: Slot;
let kept: { level_approved: unknown; difficulty: unknown; name: string; learning_objective: string };
let bare = ""; // a level of the skill that does not ask "Write the word"
let approvedHere = false; // whether this spec approved "Write the word", to take back after

test.beforeAll(async () => {
  // an English Grade 4 skill with a Hard choice question and no passage (U54 reads Grade 3's)
  [slot] = await sql<Slot[]>`
    select e.skill_code as code, e.ord, e.answer #>> '{}' as answer, e.options,
           array(select w ->> 'answer' from jsonb_array_elements(e.wrong) w) as wrong
    from english_sample_now e
    join skill_level_question_type l on l.skill_code = e.skill_code and l.difficulty = e.difficulty
      and l.question_type = e.question_type
    where e.skill_code like 'EN4.%' and e.difficulty = 'Hard' and e.question_type = 'ENG.CHOOSE'
      and e.passage_code is null and jsonb_array_length(e.wrong) >= 1
    order by e.skill_code, e.ord limit 1`;
  [kept] = await sql<(typeof kept)[]>`
    select level_approved, difficulty, name, learning_objective from skill where code = ${slot.code}`;
  await sql`update skill set level_approved = (select jsonb_object_agg(k, jsonb_build_object('by', 'Achal', 'at', now()))
                                               from jsonb_object_keys(difficulty) k) where code = ${slot.code}`;
  [{ bare }] = await sql<{ bare: string }[]>`
    select l.difficulty as bare from skill_level l join difficulty d on d.tenant_id = l.tenant_id and d.code = l.difficulty
    where l.skill_code = ${slot.code} and not exists (select 1 from skill_level_question_type k where k.skill_code = l.skill_code
      and k.difficulty = l.difficulty and k.question_type = 'ENG.WRITE_WORD') order by d.ord limit 1`;
  // a kind is added only from the approved ones; a database built afresh approves no English kind (bin/testdb)
  approvedHere = (await sql`
    insert into question_type_approval (tenant_id, question_type, approved_by)
    select tenant_id, code, 'U55' from question_type where code = 'ENG.WRITE_WORD' on conflict do nothing returning 1`).length > 0;
});

test.afterAll(async () => {
  await sql`update skill set name = ${kept.name}, learning_objective = ${kept.learning_objective},
              difficulty = ${sql.json(kept.difficulty as never)}, level_approved = ${sql.json(kept.level_approved as never)}
            where code = ${slot.code}`;
  if (approvedHere) await sql`delete from question_type_approval where question_type = 'ENG.WRITE_WORD' and approved_by = 'U55'`;
  await sql.end();
});

test("Ayush edits a Hard sample's wrong answer, is told in words why the first try fails, fixes it, and Hard waits for approval again", async ({ page }) => {
  await page.goto(`/skill-sets/${slot.code}`);
  const hard = page.getByRole("region", { name: "Hard", exact: true });
  await expect(hard.getByText(/^Approved ·/)).toBeVisible();
  const card = hard.locator(`section[data-kind="ENG.CHOOSE"] li[data-sample="${slot.ord}"]`);
  await card.getByRole("link", { name: `Edit sample ${slot.ord}` }).click();
  const form = hard.getByRole("form", { name: `Change sample ${slot.ord}` });
  await expect(form).toBeVisible();

  const edits = async () =>
    (await sql<{ n: number }[]>`select count(*)::int as n from english_sample_edit where skill_code = ${slot.code}`)[0].n;
  const before = await edits();
  // first try: a "wrong" answer that is the right one — refused, in words, beside the field, and what was typed stays
  await form.getByLabel("Wrong answer 1").fill(slot.answer);
  await form.getByRole("button", { name: "Save this sample" }).click();
  await expect(form.getByRole("alert").first()).toContainText("Not saved");
  await expect(form.locator('[data-wrong="0"]')).toContainText("is a right answer, not a wrong one.");
  await expect(form.getByLabel("Wrong answer 1")).toHaveValue(slot.answer);
  expect(await edits(), "a refused save stores nothing").toBe(before);

  // fixed: a printed option that is not the right answer
  const other = slot.options.find((o) => o !== slot.answer && !slot.wrong.slice(1).includes(o))!;
  await form.getByLabel("Wrong answer 1").fill(other);
  await form.getByRole("button", { name: "Save this sample" }).click();
  await expect(page).toHaveURL(/changed=sample/);
  await expect(page.getByText("Hard waits for approval again")).toBeVisible();
  const saved = hard.locator(`section[data-kind="ENG.CHOOSE"] li[data-sample="${slot.ord}"]`);
  await expect(saved.getByLabel("Likely wrong answers")).toContainText(other);
  await expect(saved).toContainText("Changed by");
  await expect(hard.getByText("Waiting for approval", { exact: true })).toBeVisible();
  // only Hard: Easy keeps its approval
  await expect(page.getByRole("region", { name: "Easy", exact: true }).getByText(/^Approved ·/)).toBeVisible();

  // the approver reads it again, and approves it again
  await hard.getByRole("button", { name: "Approve Hard" }).click();
  await expect(page.getByRole("region", { name: "Hard", exact: true }).getByText(/^Approved ·/)).toBeVisible();
});

test("an approval does not land on a sample changed after the page was opened", async ({ page }) => {
  await sql`update skill set level_approved = level_approved - 'Hard' where code = ${slot.code}`;
  await page.goto(`/skill-sets/${slot.code}`);
  const hard = page.getByRole("region", { name: "Hard", exact: true });
  await expect(hard.getByRole("button", { name: "Approve Hard" })).toBeVisible();
  // someone else saves the sample again while the page is open
  await sql`
    insert into english_sample_edit (tenant_id, skill_code, difficulty, question_type, ord, sample, replaced, edited_by)
    select e.tenant_id, e.skill_code, e.difficulty, e.question_type, e.ord,
           jsonb_build_object('ask', e.ask, 'passage_code', e.passage_code, 'text', e.text, 'options', e.options,
                              'answer', e.answer, 'accept', e.accept, 'rubric_code', e.rubric_code,
                              'key_points', e.key_points, 'not_words', e.not_words, 'wrong', e.wrong), null, 'U55, meanwhile'
    from english_sample_now e
    where e.skill_code = ${slot.code} and e.difficulty = 'Hard' and e.question_type = 'ENG.CHOOSE' and e.ord = ${slot.ord}`;
  await hard.getByRole("button", { name: "Approve Hard" }).click();
  await expect(page.getByText("Nothing was approved: it changed since this page was opened.")).toBeVisible();
  await expect(page.getByRole("region", { name: "Hard", exact: true }).getByRole("button", { name: "Approve Hard" })).toBeVisible();
});

test("a kind is added to a level only with three samples, each checked", async ({ page }) => {
  expect(bare, "the skill has a level that does not ask Write the word").toBeTruthy();
  await page.goto(`/skill-sets/${slot.code}`);
  const level = page.getByRole("region", { name: bare, exact: true });
  await level.getByLabel(`Add a kind of question to ${bare}`).selectOption({ label: "Write the word" });
  await level.getByRole("button", { name: `Add to ${bare}` }).click();
  const form = page.getByRole("region", { name: bare, exact: true }).getByRole("form", { name: "Add Write the word" });
  await expect(form).toContainText("Add three samples for this kind");
  // only the first of the three begun: refused, and each said
  await form.getByRole("group", { name: "Sample 1" }).getByLabel("What the child is told").fill("Write the word for a baby cat.");
  await form.getByRole("button", { name: "Add this kind" }).click();
  await expect(form.getByRole("alert").first()).toContainText("Not saved");
  await expect(form.getByRole("group", { name: "Sample 2" })).toContainText("Write what the child is told to do.");
  await expect(form.getByRole("group", { name: "Sample 1" }).getByLabel("What the child is told")).toHaveValue("Write the word for a baby cat.");
  await expect(page.locator(`#level-${bare} [data-level-kind="ENG.WRITE_WORD"]`)).toHaveCount(0);
});

test("a level's sentence is changed from the skill's page, and that level waits for approval again", async ({ page }) => {
  await page.goto(`/skill-sets/${slot.code}`);
  await expect(page.getByRole("link", { name: "Change the description and each level’s sentence" }).first()).toBeVisible();
  await page.getByRole("region", { name: "Hard", exact: true }).getByRole("link", { name: "Change this level’s sentence" }).click();
  await expect(page).toHaveURL(new RegExp(`/skill-sets/${slot.code.replace(/\./g, "\\.")}/edit#words-Hard$`));
  const box = page.locator("#words-Hard textarea");
  await box.fill(`${await box.inputValue()} Each choice is close.`);
  await page.getByRole("button", { name: "Save the words" }).click();
  await expect(page.getByRole("region", { name: "Hard", exact: true })).toContainText("Each choice is close.");
  await expect(page.getByRole("region", { name: "Hard", exact: true }).getByText("Waiting for approval", { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Easy", exact: true }).getByText(/^Approved ·/)).toBeVisible();
});

test("a Maths skill says in words that its questions are made by code and not edited here", async ({ page }) => {
  const [m] = await sql<{ code: string }[]>`
    select s.code from skill s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code
    where t.subject_code <> 'ENG' and s.status = 'ratified' order by s.code limit 1`;
  await page.goto(`/skill-sets/${m.code}`);
  await expect(page.getByText("A Maths skill’s questions are made by code from each level’s rule")).toBeVisible();
  await expect(page.getByRole("link", { name: /^Edit sample/ })).toHaveCount(0);
});
