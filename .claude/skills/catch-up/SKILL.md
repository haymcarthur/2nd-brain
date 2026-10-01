---
name: catch-up
description: Pull in what's new from every connected source, file it across the brain, and brief the user on where everything stands with a recommended place to start. Use when the user says "catch me up", "what's new", "what did I miss", "morning briefing", or at the start of a scheduled morning run.
---

# Catch-up

Catch-up acts on its own and never asks for confirmation. It's the whole morning in one: pull, file,
then brief. (If the user names one project, the `start` skill handles it and runs this first when needed.)

## 1. Get onto `main` and pick up stray work

- `git fetch --prune`, then `git checkout main` and `git pull` (if on a branch that can't switch, skip to
  the second bullet as today).
- List remote branches with `git for-each-ref --format=%(refname) refs/remotes/origin`, excluding
  `refs/remotes/origin/HEAD` and `refs/remotes/origin/main`, then shorten each remaining ref by dropping
  the `refs/remotes/` prefix (`refs/remotes/origin/feature` → `origin/feature`). For each one with commits
  not in `main`, merge that ref directly — `git merge --no-edit origin/feature`, not `git merge --no-edit
  origin/origin/feature` — then `git push`. The repo's cleanup Action deletes the merged branch; don't
  delete it yourself.
- **If a merge conflicts:** in each conflicted file keep both sides' content (never discard either), `git add`
  the files, and `git commit --no-edit`. If a file can't sensibly hold both (for example `.claude/state.json`),
  keep `main`'s version of that file and note the other side's content in the project's `notes/`. Never stop
  to ask. If the merge still can't be completed, `git merge --abort`, leave that branch alone, and mention
  it in one line in your report.
- If this session itself is on a branch that can't switch (cloud or phone), work here; `save` brings it back.

## 2. Pull what's new

The default source keys are `email`, `calendar`, `transcripts`, `teams`, `slack`, `drive`, `jira`,
`confluence`, `github`, `figma`, `lucid`, `monday`, `usertesting`, plus any the user added later (see
CLAUDE.md, "Adding a source"). Each has a state in `.claude/state.json`
`connectors.<key>`: `"live"`, `"off"` (the user chose not to feed it in), `"not-connected"`, or
`"unavailable"`.

At the start of every run, check which connector tools are actually available right now:
- **`"off"` is the user's choice (setup records every source they turned down as `"off"`). Never pull from it and never change it**, even if its tool works. Only
  the user turns it back on ("start pulling from Figma" → `"live"`; "stop pulling Slack" → `"off"`).
- A key recorded `"not-connected"` whose tool now works gets marked `"live"`, included starting this
  run, and mentioned once in your report (for example "Slack is now connected; I'll include it").
- A key recorded `"not-connected"` whose tool still doesn't exist stays `"not-connected"` — never
  mention it.
- **Never downgrade a key already recorded `"live"`, even if its tool is missing in this run.** Skip that
  source for this run: leave `connectors.<key>` and `last_pulled.<key>` exactly as they were, so a later
  run with the tool picks up from the same time and nothing is lost. Then record the skip in
  `.claude/state.json` `skipped.<key>` as the date it was **first** skipped (keep an existing date). This
  is what step 6 reports, so a source that's quietly missing from the scheduled run gets noticed and fixed.
- When a `"live"` source pulls successfully, remove its `skipped.<key>` entry.
- **Desktop-only sources** (`github`, and any source the user added that isn't attached to the
  morning routine): a scheduled run skips them without recording them in `skipped` or mentioning them.
  They're pulled whenever catch-up runs on the user's computer, from the same `last_pulled` time, so
  nothing is lost. Only a source attached to the routine that then fails to load counts as `skipped`.

For each key that is `"live"` **and has a working tool in this run**, pull items **since its
`last_pulled` time** (with no time recorded, pull the last 7 days):
- **email:** inbox and sent.
- **calendar:** events.
- **transcripts:** transcripts and recaps of meetings they attended.
- **teams:** chats and channel messages involving them.
- **slack:** DMs, mentions, and channels they're active in.
- **drive:** documents they created, edited or opened.
- **jira:** issues assigned to, reported by or watched by them, updated in the window.
- **confluence:** pages they created, edited or viewed.
- **github:** repositories, pull requests and issues they created, pushed to, reviewed or commented
  on (use the `gh` command-line tool when there's no connector).
- **figma:** files they created, edited or viewed, and comments that mention them.
- **lucid:** documents they created, edited or viewed.
- **monday:** items and boards assigned to, created by or followed by them, updated in the window. Open
  items with due dates become to-dos.
- **usertesting:** tests and studies they created or ran, with new results and session transcripts.
- **Any added source:** whatever its `sources_added.<key>` note in `.claude/state.json` says to pull.

**Pull in small pieces, and read everything.** Most sources return far more than one call can hold:
- For any window longer than a week, pull **one week at a time, oldest week first**.
- Use small page sizes (about 25) and ask only for the fields you need (subject, sender, date, status,
  title), not full bodies. Open the full text only for items worth keeping.
- **Follow every page** (`nextOffset`, `hasNextPage`, a cursor) until there are no more. Never stop at
  page one.
- Split queries that combine conditions. For Jira, pull assigned, reported and watched tickets as three
  queries.
- If a result is still too big, halve the window or the page size and retry. If a result was saved to a
  file because it was too big, read that file in parts with the file-reading tool. Never skip it.

**Where a tool can't list "what they touched"** (some design and analytics connectors only open a file
you name), also open any file of that kind linked from the other sources in the same window — a Figma
link in an email, a Lucid link in a ticket — and treat it as touched.

If the brain has an `inbox/` folder (only if the user asked for one), process every file in it.

If `drive_inbox` is set and `drive` is `live`, also list files in that drive folder and file any not
already recorded in `.claude/state.json` `drive_inbox_filed` (an id, or `name + modified time` when the
connector has no id) — don't rely on `last_pulled.drive` alone, since a file can land there between runs
in ways that timestamp misses. Treat each one like an `inbox/` file: when the connector returns its
content, save the useful original into the right project's `notes/`; otherwise write a note with the
content or a summary, plus the file's drive link. After filing, append its id (or name + modified time)
to `drive_inbox_filed`.

After each source is read **completely**, write its `last_pulled` in `.claude/state.json` as now (UTC,
ISO-8601). If a source was only partly read, set `last_pulled` to the end of the last week that was read
in full, never to now, so the next run goes back for the rest. A source that fails keeps its old time, so
a skipped or failed day loses nothing.

## 3. File it

For each item worth keeping (keep only what the user would miss later):
- Work out which project it belongs to. If none fits, use `projects/general/`.
- **Project size:** a project is one effort with its own goal or deliverable (a feature, a test, a talk,
  a report), usually with its own meetings, tickets or threads. It is **not** a team, a product area, or a
  theme: "Marketing" or "AI work" is an umbrella, and each effort inside it gets its own folder.
  When in doubt, split; small projects are cheap, and a lumped one hides what's going on. If the user
  works inside a bigger area, say so in each project's STATE.md (for example "Part of: Marketing"), not by merging them.
- Update that project's `STATE.md` so it's true now: re-read it right before editing and change only the
  section you're updating (another session may be writing to it too). Put useful detail in `projects/<name>/notes/` as a dated file.
- Record decisions it shows, following the `save` skill's step 2 (decided → active and supersede,
  still being discussed → proposed, now clearly decided → promote).
- If there's an `inbox/` folder, move processed files from it into the project's `notes/` with `git mv`, or remove them with `git rm`
  if they're worthless, so the move is recorded. If the file isn't tracked yet, `git add` it first, then
  `git mv` or `git rm` it.
- **Transcripts:** if speaker labels are missing or partial, don't attribute a statement to a named person.
- **Design, diagram and analytics files:** record what changed and why it matters to the project, with
  the file's link, not a description of every frame.

## 4. Grow reference quietly

New people go in `reference/people.md`, new terms in `reference/glossary.md`, and links in `reference/links.md`.

## 5. Keep to-dos fresh

- **Add** a to-do only after CLAUDE.md's "Before adding any to-do" checks: current state looked up,
  the user's own, dated when it arose. On a 60-day fill, that date means anything older than about 3
  weeks with no later mention goes straight to `## Parked`.
- **Close** to-dos per CLAUDE.md's "Close on evidence, from anywhere" rule, using everything this run pulled.
- Run the aging pass exactly as in the `save` skill's step 4.


**Then run add-ons.** Run every add-on in `me/add-ons/` whose `runs-in` includes catch-up and whose
`status` is `active`, following its file. An add-on whose `ends:` date has passed or condition is met
gets one line under "Needs you" in the briefing (once), so it can be retired.

## 6. Write the briefing

Rewrite `BRIEFING.md` in place (never append), dated now, from every project's `STATE.md`:

- **What changed:** one line per project touched in this run, with a link to its `STATE.md`. If nothing
  came in, say so in one line.
- **Where things stand:** one line per active project (skip any with no activity in about 3 weeks and no
  open to-dos), with the nearest due or waiting-on item.
- **Needs you:** to-dos that are overdue, due in the next 2 days, or someone is waiting on; a decision
  still `proposed` after about 30 days; an add-on whose `ends:` is met; and any source in `skipped` (see below). Leave the section out if
  it's empty.
- **Start here:** one recommendation and why, in one line: the soonest deadline, then whatever someone
  is waiting on, then the project with the most new activity. Link its `STATE.md`.

**A source in `skipped`:** on a scheduled run, write it under "Needs you" as *"<Source> wasn't reachable
from the morning catch-up since <date>. It's caught up whenever you run catch-up here."* In a session
with the user, if this run pulled it fine, it's a scheduled-run problem: attach that connector to the
morning routine yourself, the same way setup step 4 created it (and add its tools to the routine's
allowed tools). Only if that fails, tell them in one line which connector to add to the routine in
Claude's settings. Never skip reporting it: a silent skip is how a source goes missing for weeks.

Then set `.claude/state.json` `last_catch_up` to now (UTC, ISO-8601).

## 7. Save and report

Run the `save` skill (it commits and lands on `main`, including `BRIEFING.md`). Then:
- **With the user present:** show the briefing (about 10 lines), ending with the **Start here** line.
- **On a scheduled run** (no user present): just save. The briefing is waiting in `BRIEFING.md` for the
  next session, and a later "catch me up" picks up anything newer and rewrites it.
