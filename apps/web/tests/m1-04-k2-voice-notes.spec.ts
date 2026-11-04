/**
 * M1-04 — the K2 voice-note screens (goals/m1-04-k2-screens.yaml). Nimish, 3 Nov 2026: "All parts should just function
 * like a well-oiled machine, right?" What needs doing carries Record a note and Notes to confirm; Record sends her
 * recording to the engine; Confirm shows what she said beside the class already marked, red problems first; the form
 * is paint mode and its Save is her confirmation. All of it behind voice.screens_enabled.
 *
 * Placeholder rows only: a K2 class of the test's own ("M104"), 22 children known by Sr. No. alone, two activities
 * numbered 904 and 907, and the signed-in tester on the staff list with a grant for that class. Notes are made as the
 * engine makes them (drafted, with a typed transcript); no recording of anyone. The switch is on only inside a test.
 */
import { mkdirSync } from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import postgres from "postgres";
import { aK2Note, k2Class, noNotesWaiting, ROLLS, voiceSwitch } from "./k2-rows";
import { SIGNED_IN } from "../playwright.config";
import { blankWork, countLine, daysLate, findActivities, listsOf, moveTo, paint, problemsOf, type Activity, type Work } from "../lib/voice-check";

const sql = postgres(process.env.DATABASE_URL!, { max: 2 });
// written beside the contact sheet Nimish reads (docs/screens/m1-04/index.html), never into test-results/, which each
// run empties: the pictures in the pull request are the ones this spec last took
const SHOTS = path.resolve(__dirname, "../../../docs/screens/m1-04");
const DESKTOP = { width: 1280, height: 900 };
const PHONE = { width: 390, height: 844 };
let klass: string;
let staff: string;

const observations = (note: string) => sql<{ n: number }[]>`select count(*)::int as n from activity_observation where note_id = ${note}`;
const formRows = (since: Date) => sql<{ outcome: string; n: number }[]>`
  select outcome, count(*)::int as n from activity_observation o join school_class c on c.id = o.class_id
  where c.id = ${klass} and o.route = 'form' and o.stored_at >= ${since} group by outcome order by outcome`;

async function shoot(page: Page, name: string) {
  for (const [size, at] of [["1280", DESKTOP], ["390", PHONE]] as const) {
    await page.setViewportSize(at);
    await page.screenshot({ path: path.join(SHOTS, `${name}-${size}.png`), fullPage: true });
  }
  await page.setViewportSize(DESKTOP);
}

test.beforeAll(async () => {
  mkdirSync(SHOTS, { recursive: true });
  ({ klass, staff } = await k2Class(sql));
});
test.afterAll(async () => {
  await voiceSwitch(sql, false);
  await sql.end();
});
test.beforeEach(async ({ page }) => {
  await voiceSwitch(sql, true);
  await page.setViewportSize(DESKTOP);
});

test("while voice notes are switched off no K2 group shows and every K2 address is not found", async ({ page }) => {
  const note = await aK2Note(sql, { klass, staff }, "Activity 904. Above 3.");
  await voiceSwitch(sql, false);
  await page.goto("/today");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("What needs doing");
  await expect(page.locator("[data-group=record], [data-group=notes]")).toHaveCount(0);
  // a page streams, so its status is 200 and it says so (as tests/s7-paper-from-library.spec.ts reads one); the recording is 404
  for (const url of [`/voice/record?class=${klass}`, `/voice/form?class=${klass}`, `/voice/notes/${note}`]) {
    await page.goto(url);
    await expect(page.getByText("This page could not be found."), url).toBeVisible();
  }
  expect((await page.request.get(`/api/voice/${note}`)).status()).toBe(404);
});

test("What needs doing carries Record a note and Notes to confirm, and a row opens its note", async ({ page }) => {
  await noNotesWaiting(sql, { klass, staff });
  const note = await aK2Note(sql, { klass, staff }, "Activity 904. Above 3, 7. Below 5. Absent 9. The rest did as expected.");
  await page.goto("/today");
  const record = page.locator("[data-group=record]");
  await expect(record.getByRole("link", { name: "Record a note" })).toBeVisible();
  const notes = page.locator("[data-group=notes]");
  await expect(notes.locator("[data-group-count]")).toHaveText("1 to confirm");
  await expect(notes.locator("[data-status=toConfirm]").first()).toBeVisible();
  await notes.locator("summary").click();
  await notes.locator(`a[data-action=note][href="/voice/notes/${note}"]`).click();
  await expect(page).toHaveURL(new RegExp(`/voice/notes/${note}$`));
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Confirm this note");
  await page.goto("/today?open=record");
  await expect(page.locator(`a[href="/voice/record?class=${klass}"]`).first()).toBeVisible();
  await shoot(page, "1-today");
});

test("the board's rules: a stranger, a child in two lists, no activity, a future date, each red until fixed, and the count line adds up", () => {
  const acts: Activity[] = [{ code: "A904", no: "904", name: "Placeholder sorting" }, { code: "A907", no: "907", name: "Placeholder counting" }];
  const ctx = { enrolled: ROLLS, klass: "K2 M104", activities: acts, today: "2026-11-03" };
  let w: Work = { ...blankWork("2026-11-03"), marks: { "31": ["above"], "3": ["below", "absent"] } };
  expect(problemsOf(w, ctx).map((p) => p.text)).toEqual(["#3 is in Below and Absent", "#31 is not in K2 M104. Which child?", "Which activity? Search by number or name.", "Pick the level you expected."]);
  w = moveTo(w, "31", "4");
  w = { ...paint(w, "3", "absent"), activity: "A904", level: 2 };
  expect(problemsOf(w, ctx)).toEqual([]);
  expect(problemsOf({ ...w, day: "2026-11-04" }, ctx).map((p) => p.text)).toEqual(["That date is in the future. Pick the date."]);
  expect(countLine(w, ROLLS)).toBe("2 named; the other 20 not seen");
  expect(countLine({ ...w, rest: true }, ROLLS)).toBe("1 above, 1 absent, 20 as expected = 22");
  expect(listsOf(w)).toEqual({ above: ["4"], below: [], not_willing: [], absent: ["3"] });
  expect(paint(paint(w, "4", "above"), "4", "above").marks["4"]).toEqual(["above"]); // off, then on again
  expect(findActivities(acts, "907").map((a) => a.code)).toEqual(["A907"]);
  expect(findActivities(acts, "sort").map((a) => a.code)).toEqual(["A904"]);
  const none: Activity = { code: "A000", no: "", name: "Placeholder unnumbered" };
  expect(findActivities([...acts, none], "unnumbered").map((a) => a.code)).toEqual(["A000"]); // by its name, never lost
  expect(findActivities([...acts, none], "9").map((a) => a.code)).toEqual(["A904", "A907"]); // a number never matches it
  // heard at 03:54 in Pune on 4 Nov (22:24 UTC on 3 Nov), about 3 Nov: a day late, by the school's clock
  expect(daysLate("2026-11-03", "2026-11-03T22:24:00Z", "Asia/Kolkata")).toBe(1);
  expect(daysLate("2026-11-04", "2026-11-03T22:24:00Z", "Asia/Kolkata")).toBe(0);
});

test("Confirm shows what she said beside the class already marked, red problems first, the button off until each is fixed, then writes her observations", async ({ page }) => {
  const note = await aK2Note(sql, { klass, staff }, "Activity 904, level 2. Above 3. Below 31. Absent 3. The rest did as expected.");
  await page.goto(`/voice/notes/${note}`);
  const heard = page.locator("[data-heard]");
  await expect(heard.locator("[data-line=above]")).toContainText("Above 3");
  await expect(heard.locator("[data-line=below]")).toContainText("Below 31");
  await expect(page.locator("[data-cell-mark=above]")).toHaveCount(1);
  await expect(page.locator("[data-roll='3']")).toHaveAttribute("data-cell-mark", "above"); // the first of its two marks
  const problems = page.locator("[data-problem]");
  await expect(problems).toHaveText([/#3 is in Above and Absent/, /#31 is not in K2 M104\. Which child\?/]);
  await expect(page.locator("[data-problems] [data-status=fixThis]").first()).toBeVisible();
  const confirm = page.getByRole("button", { name: "Confirm this note" });
  await expect(confirm).toBeDisabled();
  await expect(page.locator("[data-roll] [data-tone=act], [data-roll].text-terracotta")).toHaveCount(0); // a child is never red
  await shoot(page, "3-confirm-with-problems");
  await page.getByRole("button", { name: "Tap the child who is #31" }).click();
  await page.locator("[data-roll='12']").click();
  await page.getByRole("button", { name: "Keep Absent" }).click();
  await expect(problems).toHaveCount(0);
  await expect(page.locator("[data-count-line]")).toHaveText("1 below, 1 absent, 20 as expected = 22");
  await expect(confirm).toBeEnabled();
  await shoot(page, "4-confirm-ready");
  await confirm.click();
  await expect(page).toHaveURL(/\/today\?open=notes/);
  expect((await observations(note))[0].n).toBe(22);
  await page.goto(`/voice/notes/${note}`);
  await expect(page.locator("main")).toContainText("Confirmed");
});

test("the form is paint mode: nothing ticked, the rest off, and Save under the count line writes the observations", async ({ page }) => {
  const since = new Date();
  await page.goto(`/voice/form?class=${klass}`);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Fill the form");
  await expect(page.locator("[data-cell-mark=none]")).toHaveCount(ROLLS.length);
  await expect(page.locator("[data-rest]")).toHaveAttribute("aria-checked", "false");
  await expect(page.locator("[data-count-line]")).toHaveText("0 named; the other 22 not seen");
  const save = page.getByRole("button", { name: "Save", exact: true });
  await expect(save).toBeDisabled();
  await shoot(page, "5-form-empty");
  await page.locator("[data-activity-search]").fill("907");
  await page.getByRole("button", { name: "907 · Placeholder counting activity" }).click();
  await page.getByRole("group", { name: "Level expected" }).getByRole("button", { name: "2" }).click();
  await page.locator("[data-mark-pick=below]").click();
  await page.locator("[data-roll='4']").click();
  await page.locator("[data-mark-pick=absent]").click();
  await page.locator("[data-roll='6']").click();
  await expect(page.locator("[data-count-line]")).toHaveText("2 named; the other 20 not seen");
  await page.locator("[data-rest]").click();
  await expect(page.locator("[data-count-line]")).toHaveText("1 below, 1 absent, 20 as expected = 22");
  await expect(save).toBeEnabled();
  await shoot(page, "6-form-filled");
  await save.click();
  await expect(page).toHaveURL(/\/today\?open=notes/);
  expect(await formRows(since)).toEqual([
    { outcome: "absent", n: 1 },
    { outcome: "as_expected", n: 20 },
    { outcome: "below", n: 1 },
  ]);
});

test("Record sends her recording and opens the note being read; a refused microphone points to the form", async ({ browser }) => {
  const refused = await browser.newContext({ storageState: SIGNED_IN, viewport: DESKTOP });
  await refused.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException("denied", "NotAllowedError"));
  });
  const no = await refused.newPage();
  await no.goto(`/voice/record?class=${klass}`);
  await expect(no.getByRole("heading", { level: 1 })).toContainText("Record a note");
  await shoot(no, "2-record");
  await no.locator("[data-record]").click();
  await expect(no.locator("p[role=alert]")).toContainText("The phone did not let us record. Use the form, or allow the microphone in settings.");
  await expect(no.locator("p[role=alert]").getByRole("link", { name: "Use the form instead" })).toHaveAttribute("href", `/voice/form?class=${klass}`);
  await refused.close();

  const allowed = await browser.newContext({ storageState: SIGNED_IN, viewport: DESKTOP });
  await allowed.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = () => Promise.resolve({ getTracks: () => [{ stop() {} }] } as unknown as MediaStream);
    class FakeRecorder {
      mimeType = "audio/webm";
      ondataavailable: ((e: { data: Blob }) => void) | null = null;
      onstop: (() => void) | null = null;
      start() {}
      stop() {
        this.ondataavailable?.({ data: new Blob([new Uint8Array(4096)], { type: "audio/webm" }) });
        this.onstop?.();
      }
    }
    (window as unknown as { MediaRecorder: unknown }).MediaRecorder = FakeRecorder;
  });
  const yes = await allowed.newPage();
  await yes.goto(`/voice/record?class=${klass}`);
  await yes.locator("[data-record]").click();
  await expect(yes.locator("[data-stop]")).toBeVisible();
  await yes.locator("[data-stop]").click();
  await expect(yes.locator("[data-playback]")).toBeVisible();
  await yes.locator("[data-send]").click();
  await expect(yes).toHaveURL(/\/voice\/notes\/[0-9a-f-]{36}$/);
  await expect(yes.locator("[data-reading]")).toContainText("Reading your note");
  const sent = yes.url().split("/").pop()!;
  const [row] = await sql<{ status: string; staff_id: string }[]>`select status, staff_id::text from pii.educator_note where id = ${sent}`;
  expect(row).toEqual({ status: "received", staff_id: staff });
  await shoot(yes, "7-reading");
  await allowed.close();
});

test("with recording off, the K2 educator fills the form: no Record, no microphone, no recording kept or played", async ({ page }) => {
  await voiceSwitch(sql, true, false);
  const note = await aK2Note(sql, { klass, staff }, "Activity 904. Above 3. The rest did as expected.");
  await page.goto("/today?open=record");
  const row = page.locator("[data-group=record]");
  await expect(row.locator(`a[href="/voice/form?class=${klass}"]`).first()).toBeVisible();
  await expect(page.locator('a[href^="/voice/record"]')).toHaveCount(0);
  await page.goto(`/voice/record?class=${klass}`);
  await expect(page.getByText("This page could not be found.")).toBeVisible();
  await page.goto(`/voice/form?class=${klass}`);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Fill the form");
  await expect(page.locator("main [data-icon=record]")).toHaveCount(0);
  await page.goto(`/voice/notes/${note}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Confirm this note");
  await expect(page.locator("main audio")).toHaveCount(0);
  expect((await page.request.get(`/api/voice/${note}`)).status()).toBe(404);
});

test("an activity the K2 sheet left without a number is found by its name and saved", async ({ page }) => {
  const since = new Date();
  await page.goto(`/voice/form?class=${klass}`);
  await page.locator("[data-activity-search]").fill("unnumbered");
  await page.getByRole("button", { name: "Placeholder unnumbered activity", exact: true }).click();
  await expect(page.locator("[data-activity]")).toHaveAttribute("data-activity", "ACT-K2-M104-NONE");
  await page.getByRole("group", { name: "Level expected" }).getByRole("button", { name: "2" }).click();
  await page.locator("[data-mark-pick=above]").click();
  await page.locator("[data-roll='2']").click();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page).toHaveURL(/\/today\?open=notes/);
  const [{ n }] = await sql<{ n: number }[]>`
    select count(*)::int as n from activity_observation where class_id = ${klass} and route = 'form'
      and activity_code = 'ACT-K2-M104-NONE' and stored_at >= ${since}`;
  expect(n).toBe(1);
});

test("a note that could not be read, or where nothing was heard, sends her to the form", async ({ page }) => {
  for (const [words, said] of [["mumble mumble.", "We could not read this note."], ["", "Nothing heard. Record again or use the form."]]) {
    await page.goto(`/voice/notes/${await aK2Note(sql, { klass, staff }, words)}`);
    await expect(page.locator("[data-could-not]")).toContainText(said);
    await expect(page.locator("[data-to-form]")).toHaveAttribute("href", `/voice/form?class=${klass}`);
    if (words) await shoot(page, "8-could-not-read");
  }
});

test("each K2 screen is shot at 1280 and 390 pixels with placeholder children", async () => {
  const { readdirSync, readFileSync, statSync } = await import("node:fs");
  const shots = readdirSync(SHOTS).filter((f) => f.endsWith(".png"));
  const sheet = readFileSync(path.join(SHOTS, "index.html"), "utf8");
  for (const name of ["1-today", "2-record", "3-confirm-with-problems", "4-confirm-ready", "5-form-empty", "6-form-filled", "7-reading", "8-could-not-read"])
    for (const size of ["1280", "390"]) {
      const file = `${name}-${size}.png`;
      expect(shots, file).toContain(file);
      expect(sheet, `the contact sheet shows ${file}`).toContain(`src="${file}"`);
      expect(statSync(path.join(SHOTS, file)).size, `${file} is small enough to send`).toBeLessThan(300_000);
    }
});
