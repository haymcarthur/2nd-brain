---
name: start
description: Load one project and orient the user before they work on it, catching the brain up first if it's stale. Use when the user says "let's work on <project>", "start <project>", "open <project>", "where are we on <project>", "catch me up on <project>", or opens a session by naming a project.
---

# Start

Start is fast: it reads what the brain already knows about one project. It pulls from sources only when
the brain may be out of date. It never asks for confirmation.

## 1. Find the project

Match what the user named against the project folders in `INDEX.md` (a close match is fine). If two fit,
pick the one with the most recent activity and say which you picked in one line. If none fits, say
"nothing in the brain on that yet" and offer to start a `projects/<name>/` for it.

## 2. Catch up first if it may be stale

Run the `catch-up` skill first (quietly; skip its briefing and go on to step 3 here) when **any** of these
is true:
- The user said "catch me up on <project>".
- `.claude/state.json` `last_catch_up` is empty or more than about a day old.
- The project hasn't been touched in about **3 days**: its folder has no commit in that time
  (`git log -1 --format=%cI -- projects/<name>/`).

Otherwise skip straight to step 3. Start never pulls one project's sources on its own, because catch-up's
`last_pulled` times cover every project at once.

## 3. Load the project

Read, in this order and nothing more:
1. `projects/<name>/STATE.md` — the current truth.
2. Decisions for this project from about the last 30 days, and any still `proposed`.
3. The 2–3 most recent files in `projects/<name>/notes/`.
4. People and terms from `reference/` that STATE.md names, only where needed.

## 4. Orient

Reply in about 6 lines, with links:
- **Where it stands:** 1–2 lines from STATE.md.
- **Open to-dos:** due-soonest first, at most 4.
- **Recent decisions:** any from the last week, one line each.
- **Suggested next step:** the one you'd take and why, named, not started.
- A link to [STATE.md](projects/<name>/STATE.md).

Then do what the user asks next. If they just say "go", start on the suggested next step.
