---
name: save
description: Save what we learned into the brain and back it up. Use when the user says "save", "save what we learned", "wrap up", or "I'm done", when a hook says the session is filling up, and on your own after each meaningful piece of work (a decision, a finished draft, a topic switch).
---

# Save

Save runs quietly and never asks for confirmation. Do every step that applies, then report in one line.

**Exception:** during setup's background seeding (`"seeding"` is in `setup.waiting_on`), don't save yet —
setup's Save step will.

## 1. Update each project you touched

For every project worked on since the last save:
- **Rewrite its `STATE.md` in place** so "Where things stand" is true right now. Don't append history there.
- **Add to-dos** that clearly came up (someone is waiting on it, or there's a deadline), only after
  CLAUDE.md's "Before adding any to-do" checks (current state looked up, the user's own, dated when it
  arose). Use the exact format `- [ ] <text> · added YYYY-MM-DD` under `## To do`. Skip anything that
  wouldn't be missed.
- **Check off to-dos** that were finished in this session: `- [x] <text> · added YYYY-MM-DD · done YYYY-MM-DD`.
- **Ideas, insights, and history** go in `projects/<name>/notes/` as a dated file, not in STATE.md.
- Work that fits no project goes in `projects/general/`.
- A new project folder gets a line in `INDEX.md`.

## 2. Record decisions

For each decision made or discovered, write `decisions/YYYY-MM-DD-slug.md` from `decisions/_template.md`.
Set `provenance: decided` when the user said it, or a source (meeting, email, thread) shows it landed;
otherwise `provenance: guessed`. Then check it against active decisions on the same subject:
- **No conflict:** save it as `status: active` with its source.
- **It replaces an active one, and the source shows it was decided** (the user said so, or a meeting,
  email, or thread shows it landed): set `supersedes:` on the new one, and `status: superseded` plus
  `superseded_by:` on the old one. Never rewrite the old one's content.
- **It's still being discussed** ("leaning toward", "let's think about", no sign-off): save it as
  `status: proposed` with `supersedes:` naming what it would replace. Leave the old one active.
- **A `proposed` decision that is now clearly decided:** make it `active` and supersede the old one as above.

## 3. Grow reference quietly

New people go in `reference/people.md`, new terms in `reference/glossary.md`, links in `reference/links.md`,
and new ways of working in `me/methods.md`. Corrections to how the user writes go in `me/voice.md`
("Patterns"), with the before and after.

## 4. Keep to-dos fresh (every project, every save)

- An unchecked to-do whose `added` date is **more than about 3 weeks ago**, with no mention since, moves from
  `## To do` to `## Parked`, unchanged.
- A Parked item older than **about 90 days** moves to `projects/<name>/notes/archive.md`.
- A done (`- [x]`) item whose `done` date is **more than about 30 days ago** moves to
  `projects/<name>/notes/archive.md`.
- Never delete a to-do.

## 5. Promote from general, and record processes

- If **about 3** items or notes in `projects/general/` share a theme, create `projects/<theme>/` with a
  `STATE.md`, move them in, add it to `INDEX.md`, and mention it in your one-line report.
- If this session did a recognizable kind of repeated work (a status update, prep for a recurring meeting,
  a report), create or update `me/processes/<name>.md` per `me/processes/README.md`. Record the steps as
  actually done, the inputs, the output format, any corrections the user made, and add an Occurrences line.
- If it now has **3 or more occurrences** and `skill-offer: not-yet`, offer once, in one sentence: *"You've
  done <process> 3 times. Want me to make it a skill so you can just say '<trigger>'?"* Set `skill-offer`
  to `offered-accepted` or `offered-declined` from the answer. On yes, build
  `.claude/skills/<name>/SKILL.md` **from the process file** and link each to the other.

## 6. Back it up to `main`

Run `git status`, then land the work on `main`:
- **On `main` (the normal desktop case):** stage with
  `git add -A projects/ me/ reference/ decisions/ INDEX.md BRIEFING.md .claude/state.json .claude/skills/`
  (plus `inbox/` if the user asked for one; never `private/`), `git commit -m "save: <one-line summary>"`, then `git pull --rebase` and `git push`.
- **On another branch (a cloud or phone session, or a worktree):** stage the same way, commit on the
  branch, push it, then `gh pr create --base main --fill` and `gh pr merge --merge --delete-branch`. If
  the branch can't be deleted from here, that's fine: the repo's cleanup Action deletes merged branches.
  After the merge, the local checkout ends up on `main`. On a later save in a cloud or phone session, if
  a direct push to `main` is refused, commit on a new branch and repeat the PR route above.
- **If `git pull --rebase` stops on a conflict:** in each conflicted file keep both versions' content, `git add`
  the files, and `git rebase --continue`. If it can't be completed, `git rebase --abort`, then `git pull --no-rebase`,
  resolve the same way, `git commit --no-edit`, and push. Mention the conflict in one line. **If the push is
  rejected because the remote moved:** `git pull --rebase` again, then push.
- **If there's no remote yet** (setup not finished): commit only.

## 7. Report

One line, with links: what was saved and where. For example: *"Saved: updated
[launch/STATE.md](projects/launch/STATE.md), 1 decision, 2 to-dos. Backed up."*
