# ADR 0082 — A child's pages are one copy wherever they lie in a scan; a page taken twice is read from the later

**Status:** accepted (2026-10-16).
Goal: goals/l11-a-scan-is-read-whole.yaml

## What happened

The Grade 3 scan of 2026-10-16 held roll 4's first page twice, as the file's first and ninth pages, and roll 1's first
page not at all. Pages were made one copy only where they lay together (`sorting.group`). Page 1 became a copy of its
own, and the reading of pages 9–10 then replaced it (`copies._replaces`: a later reading of the same paper from the
same file stands in for the earlier). Run on the old code, a whole copy followed by its own first page kept 3 of 12
answers. A copy whose pages lay apart kept 9 of 12. The run said nothing of either, nor of roll 1's missing page.

## Decision

- A code printed for one child (`CS` + 6 hex) is theirs alone, so every page carrying it is one copy, kept where it
  first appears in the file (`sorting.gather`). A library worksheet's code is on every child's copy of it, so its copies
  are still told apart by where they lie and how long the worksheet is.
- Each stretch of a copy's pages is placed against the paper on its own (`boxes.placed`). Each photograph is placed
  alone where a stretch holds more photographs than the paper has pages.
- A page photographed more than once is read from its **later** photograph, and the copy says so.
- A page of the paper not in the file is said, by page, on the copy's line. The lines are kept on the run
  (`flow_run.result`) and shown under Read a scan to the people whose classes they are.

## Rejected

- **Keep grouping by position and only report the problem.** The answers would still be dropped. Saying so would not
  stop a person signing off a paper scored on a third of it.
- **Read the first photograph of a page taken twice.** A person who scans a page again does it because the first was
  bad. The later one is the one they meant.
- **Read both and keep the more confident reading per answer.** Two readings of one answer means two candidates for a
  person, and rule 5's three signals per box would have to be reconciled across photographs. Nothing on 16 Oct needed
  it: the page was the same sheet both times.

## Consequences

A copy gathered from pages apart is cut to a file named by every page it holds (`copy01-p9-10-CS….pdf`), never to a
name an earlier sorting cut, so an old cut is never read for a new copy. A child whose page is missing is scored on the
pages that are there until that page is scanned and sent. The site and the run then say which page is missing.
