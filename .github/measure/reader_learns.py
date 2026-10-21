"""Whether the reader learns from every check on live (ADR 0032, docs/notes/reader-learns-audit.md): run inside the engine
by engine-logs.yml, in a read-only transaction. Counts and dates only: never a child's name, an answer or a scan (rule 6)."""

from engine.core import db

SINCE = "2026-09-01"

# what became of each answer the reader was handed, from the reason its reading carries (`raw_read.why`)
FATE = """case
  when coalesce(r.raw_read::jsonb ->> 'why', '') like '%%not a number%%' then 'never read'
  when coalesce(r.raw_read::jsonb ->> 'why', '') like 'this child%%' then 'notebook flag'
  when coalesce(r.raw_read::jsonb ->> 'why', '') like 'read as a right answer; a person checks every%%' then 'kind not trusted'
  when coalesce(r.raw_read::jsonb ->> 'why', '') like 'read as a right answer; spot-checked%%' then 'spot check'
  when coalesce(r.raw_read::jsonb ->> 'why', '') like 'read as a wrong%%' then 'wrong, held'
  when coalesce(r.raw_read::jsonb ->> 'why', '') like 'read as blank%%' then 'blank, held'
  when coalesce(r.raw_read::jsonb ->> 'why', '') <> ''
    or coalesce(r.raw_read::jsonb ->> 'answer_state', '') not in ('written', 'blank') then 'reader unsure'
  else 'auto-accepted' end"""
FATES = ["auto-accepted", "kind not trusted", "spot check", "wrong, held", "blank, held", "reader unsure", "notebook flag"]


def show(title, rows):
    print(f"-- {title}")
    for r in rows:
        print("  " + " | ".join(f"{k}={v}" for k, v in dict(r).items()))


with db.connect() as c:
    c.execute("set transaction read only")
    show("notebooks", c.execute(
        "select count(*) as notebooks, min(updated_at) as oldest_rebuild, max(updated_at) as newest_rebuild,"
        " count(*) filter (where notes ->> 'floor' = '70') as floor_70, count(*) filter (where notes ->> 'floor' = '80') as floor_80,"
        " count(*) filter (where notes ->> 'floor' = '90') as floor_90, count(*) filter (where notes ->> 'floor' = '95') as floor_95,"
        " count(*) filter (where jsonb_array_length(notes -> 'route') > 0) as with_routed_kinds,"
        " count(*) filter (where notes -> 'confusions' <> '{}'::jsonb) as with_confusions,"
        " count(*) filter (where jsonb_array_length(notes -> 'samples') > 0) as with_samples"
        " from child_reading_profile"))
    # the last time a person checked something of each child, against when the child's notebook was last written
    last_check = (
        "with checks as (select si.child_id, greatest(max(r.confirmed_at), max(rc.created_at)) as at"
        " from item_result r join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " left join read_correction rc on rc.item_result_id = r.id"
        " where c.superseded_by is null and (r.state = 'confirmed' or rc.id is not null) group by 1),"
        " reads as (select si.child_id, max(c.created_at) as at from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " where c.superseded_by is null group by 1)"
    )
    show("checked children and their notebooks", c.execute(
        last_check + " select count(*) as checked_children, count(p.id) as with_notebook,"
        " count(*) filter (where p.updated_at >= k.at) as notebook_newer_than_last_check,"
        " count(*) filter (where p.updated_at < k.at) as checked_since_notebook,"
        " count(*) filter (where p.updated_at < k.at and rd.at > k.at) as read_again_since_check_yet_notebook_older"
        " from checks k left join child_reading_profile p on p.child_id = k.child_id left join reads rd on rd.child_id = k.child_id"))
    show("answers per paper, week by week, by what became of them", c.execute(
        f"select date_trunc('week', c.created_at)::date as week, count(distinct c.id) as papers,"
        f" count(distinct si.child_id) as children, count(*) filter (where fate <> 'never read') as read,"
        + ", ".join(f" count(*) filter (where fate = '{f}') as \"{f}\"" for f in FATES)
        + f", round(count(*) filter (where fate not in ('never read', 'auto-accepted'))::numeric / count(distinct c.id), 1)"
        f" as to_a_person_per_paper"
        f" from (select r.*, {FATE} as fate from item_result r) r"
        " join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        f" where c.superseded_by is null and c.created_at >= '{SINCE}' group by 1 order by 1"))
    show("each kind against the gate", c.execute(
        "select fmt, n, \"right\", trusted, checks_to_trust from kind_trust order by fmt"))
    # a signed-off answer that never waited for a person is in answer_checked as the reader's own reading confirmed
    show("checks no person was asked about (auto-accepted, then signed off with the paper)", c.execute(
        "select fmt, count(*) as checks, count(*) filter (where how = 'signed off' and why = '' and answer_state = 'written')"
        " as never_shown_to_a_person from answer_checked where not never_read group by 1 order by 1"))
    show("of each kind's trust window, the checks no person was asked about", c.execute(
        "with w as (select fmt, how, why, answer_state, row_number() over (partition by tenant_id, fmt"
        " order by read_at desc, item_key desc, item_result_id desc) as rn from answer_checked where stood),"
        " g as (select coalesce((select value::int from threshold where key = 'marking.agreement_window'), 50) as size)"
        " select fmt, count(*) as in_window, count(*) filter (where how = 'signed off' and why = '' and answer_state = 'written')"
        " as never_shown from w, g where rn <= g.size group by 1 order by 1"))
    show("the papers read on 16 Oct", c.execute(
        last_check + " select count(distinct c.id) as papers, count(distinct si.child_id) as children,"
        " count(*) filter (where r.state = 'confirmed') as signed_off,"
        " (select count(*) from read_correction rc join capture c2 on c2.id = rc.capture_id"
        "   where c2.created_at::date = '2026-10-16' and c2.superseded_by is null) as typed,"
        " max(k.at) as last_check_of_these_children,"
        " count(distinct si.child_id) filter (where p.updated_at >= k.at) as notebook_rebuilt_after_last_check,"
        " count(distinct si.child_id) filter (where p.id is null) as no_notebook,"
        " count(distinct si.child_id) filter (where rd.at > c.created_at) as read_again_since"
        " from capture c join sheet_instance si on si.id = c.sheet_instance_id join item_result r on r.capture_id = c.id"
        " left join checks k on k.child_id = si.child_id left join child_reading_profile p on p.child_id = si.child_id"
        " left join reads rd on rd.child_id = si.child_id"
        " where c.created_at::date = '2026-10-16' and c.superseded_by is null"))
    show("the kinds notebooks route to a person", c.execute(
        "select k as fmt, count(*) as notebooks from child_reading_profile, jsonb_array_elements_text(notes -> 'route') k"
        " group by 1 order by 1"))
    # the next read uses the notebook: a reading holding a digit this child has had confused twice is flagged (`profiles.apply`)
    show("readings since 1 Oct holding a digit the child's notebook says is confused", c.execute(
        "select count(*) filter (where r.raw_read::jsonb ->> 'why' like 'this child%%') as flagged_by_notebook,"
        # the reader stood behind it (no doubt of its own, or only marking's hold) and the notebook did not flag it
        " count(*) filter (where coalesce(r.raw_read::jsonb ->> 'why', '') = '' or r.raw_read::jsonb ->> 'why' like 'read as%%')"
        "   as stood_behind_not_flagged,"
        " count(*) filter (where (coalesce(r.raw_read::jsonb ->> 'why', '') = '' or r.raw_read::jsonb ->> 'why' like 'read as%%')"
        "   and r.raw_read::jsonb ? 'boxes') as of_them_read_in_boxes"
        " from item_result r join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " join child_reading_profile p on p.child_id = si.child_id"
        " where c.superseded_by is null and c.created_at >= '2026-10-01'"
        "   and coalesce(nullif(r.raw_read::jsonb ->> 'child_answer', ''), r.raw_read::jsonb ->> 'guess', '') <> ''"
        "   and exists (select 1 from jsonb_each_text(p.notes -> 'confusions') e where e.value::int >= 2"
        "     and position(split_part(e.key, '>', 1) in coalesce(nullif(r.raw_read::jsonb ->> 'child_answer', ''),"
        "       r.raw_read::jsonb ->> 'guess')) > 0)"))
    # what a child's floor is measured on: the region reader's readings or the box reader's (ADR 0035)
    show("checks by reader", c.execute(
        "select case when r.raw_read::jsonb ? 'boxes' then 'in boxes' else 'by region' end as reader, count(*) as checks,"
        " min(a.read_on) as first, max(a.read_on) as last"
        " from answer_checked a join item_result r on r.id = a.item_result_id where not a.never_read group by 1"))
    show("the second reader", c.execute(
        "select (select string_agg(version || case when active then ' active' else '' end, ', ')"
        "   from prompt where purpose = 'read_with_examples') as prompt_versions,"
        " count(*) filter (where r.raw_read::jsonb ->> 'guess_by' like 'read_with_examples%%') as guesses_offered,"
        " max(c.created_at) filter (where r.raw_read::jsonb ->> 'guess_by' like 'read_with_examples%%') as last_guess_on_a_paper_read"
        " from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null"))
    # the second reader is asked only where the first doubted its reading and offered no guess (`second_reader._groups`)
    show("readings since 1 Oct the reader doubted, by whether it offered its own guess", c.execute(
        "select count(*) filter (where coalesce(r.raw_read::jsonb ->> 'guess', '') <> ''"
        "   and coalesce(r.raw_read::jsonb ->> 'guess_by', '') = '') as first_readers_guess,"
        " count(*) filter (where r.raw_read::jsonb ->> 'guess_by' like 'read_with_examples%%') as second_readers_guess,"
        " count(*) filter (where coalesce(r.raw_read::jsonb ->> 'guess', '') = '') as no_guess,"
        " count(*) filter (where coalesce(r.raw_read::jsonb ->> 'guess', '') = '' and r.raw_read::jsonb -> 'box' is null)"
        "   as no_guess_and_no_box"
        " from item_result r join capture c on c.id = r.capture_id"
        " where c.superseded_by is null and c.created_at >= '2026-10-01'"
        "   and coalesce(r.raw_read::jsonb ->> 'why', '') <> '' and r.raw_read::jsonb ->> 'why' not like 'read as%%'"
        "   and r.raw_read::jsonb ->> 'why' not like '%%not a number%%' and r.raw_read::jsonb ->> 'why' not like 'this child%%'"))
    show("the rows the loop reads", c.execute(
        "select key, value from threshold where key in ('read.route_above_overturn', 'marking.agreement_gate',"
        " 'marking.agreement_window', 'marking.spot_check_rate', 'read.auto_confirm_above') order by key"))
