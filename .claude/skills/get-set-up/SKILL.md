---
name: get-set-up
description: Set up this 2nd Brain for a new user, or re-check it. Use when the user says "set me up", "set up my second brain", "onboard me", "keep setting me up", or pastes "Set up my second brain from github.com/haymcarthur/2nd-brain" (optionally followed by "and call it <name>"), or when me/about-me.md still says "Not set up yet".
---

# Get set up

You do every step yourself. Never tell the user to go do something you could do. Ask the user exactly one thing:
whether any of the default sources should be left out (step 3). Everything else about them is inferred from those sources
and corrected by them during the tour.

**Explain as you go.** This is probably their first time with anything like this, and setup is also how
they learn what their brain is and why each piece matters. Every step below has an **Explain** block: say
it at that step, in plain words, adapted to what actually happened, in about 1–3 short sentences. Keep the
substance (what's happening, what it does for them, anything they need to know) and skip the jargon: say
"your private copy on GitHub", not "repo"; "a scheduled job", not "cron". Keep the commands themselves
out of sight unless something fails.

**Open with this, before step 1** (once, not on a resume):

> **Explain:** I'm setting up your second brain: notes on your projects, people, decisions and to-dos
> that I read at the start of every session, so you never have to re-explain your work. I'll make your
> private copy, connect your work tools, fill it in from your last 60 days, and schedule a weekday
> morning catch-up. One question from you along the way; I'll do the rest.

Claude Code may ask permission for some of the steps below. Choosing "Always allow" for this folder is
fine.

**Record progress as you go.** After finishing each numbered step below, add its number to
`setup.done_steps` in `.claude/state.json` and save the file. When a step can't finish yet, record
what's pending in `setup.waiting_on` as a short string and move on to the next step — don't wait.

**Resuming.** If `setup.done_steps` isn't empty when this skill starts, resume at the first unfinished
step rather than starting over. If `"seeding"` is still in `setup.waiting_on`, step 5's background agent
hadn't finished when the session ended — re-run step 5 from the top; it's safe to run again.

## 1. Make sure the brain exists on their computer

- **If this folder already has `CLAUDE.md` and `INDEX.md`:** it's cloned; go to step 2.
- **If this session isn't inside their brain folder** (they pasted the bootstrap prompt from a new session):
  1. Check `gh auth status`. If the GitHub command-line tool is missing, install it (`brew install gh`
     on a Mac if Homebrew exists; otherwise give the one download link from cli.github.com and wait). If
     not signed in, run `gh auth login --web` and tell them a browser window will open to approve.

     > **Explain (only if it needs installing or signing in):** GitHub is where your brain is safely
     > stored and backed up. I use a small GitHub tool to make your copy and save to it. A browser window
     > will open so you can approve that once.
  2. Take the name from the prompt's "call it …" part, if there is one. Turn it into a valid GitHub
     repo name: lowercase it, turn spaces into hyphens, and keep only letters, digits, `-`, `_` and `.`.
     Fall back to `my-2nd-brain` if no name was given or nothing valid is left. Create their private
     copy without cloning: `gh repo create <their-github-username>/<name> --template
     haymcarthur/2nd-brain --private`. If that name is taken, add `-2` (then `-3`, and so on) — this
     final chosen name is `<repo-name>` for the rest of this step.
  3. Wait a few seconds, then clone it into the home folder: `git clone https://github.com/<their-github-username>/<repo-name>.git ~/<repo-name>`. If it clones empty, GitHub hasn't finished materializing the template yet — wait a few seconds and retry, up to 3 times. If `~/<repo-name>` already exists and isn't empty, use the next free `-2`/`-3` name for the folder. (If git asks to install Apple's developer tools, tell them to click Install.) Never clone `haymcarthur/2nd-brain` itself. Right after the clone, record step 1 as done in `~/<repo-name>/.claude/state.json` (it couldn't be recorded before this, since the file didn't exist yet).
     > **Explain (once the clone succeeds):** Your brain lives in two synced places: the `~/<repo-name>`
     > folder on this computer, where I work, and a private copy on your GitHub, so you can open it from
     > your phone or the web. Only you can see it.
  4. Read `~/<repo-name>/.claude/skills/get-set-up/SKILL.md` and continue from step 2, doing all remaining work inside `~/<repo-name>` (paths, git commands with `-C ~/<repo-name>` or after `cd`).

## 2. Check the repo is healthy

- Not the public template: `git remote get-url origin`. If it points at `haymcarthur/2nd-brain`, this is
  the public template, not their own copy — create the private copy with `gh repo create` as in step 1,
  then tell them in one line to close this folder and re-open the new one. (Don't `git remote set-url`;
  it's denied.)
- It's private: `gh repo view --json visibility`. If it's public, make it private with `gh repo edit --visibility private --accept-visibility-change-consequences` (Claude Code will ask you to approve this one — say yes).
- It's on `main`.
- **Explain (one line, folded into the step's report):** *"It's private, and your personal email never
  appears in it."*
- Set git's name and email for this repo if missing: name from `gh api user --jq '.name // .login'`, and email as GitHub's private noreply address `<id>+<login>@users.noreply.github.com` using `gh api user --jq '.id'` and `--jq '.login'`. Never use their personal email.

## 3. Confirm the sources, then connect them

**Ask the user exactly one thing, and ask it first.** This is the first thing they see after their copy is
made (step 2 is silent). Send this as a normal message and wait for their reply:

> Next I'll connect your work tools. Every morning I read what's new in them and file it: project
> updates, new people, decisions, and to-dos (checked off when the work is done). Catch-up only **reads**
> from them; it never posts or changes anything.
>
> 1. **Microsoft 365:** email, calendar, Teams chats, meeting transcripts, OneDrive and SharePoint files
> 2. **Slack:** your DMs, mentions and active channels
> 3. **Atlassian:** your Jira tickets and Confluence pages
> 4. **GitHub:** your repositories, pull requests and issues
> 5. **Figma:** design files you work in, and comments to you
> 6. **Lucid:** your diagrams
> 7. **monday.com:** items assigned to you
> 8. **UserTesting:** your tests, results and session transcripts
>
> Reply with the numbers of any you **don't** want, or "all good" to keep them all.

If `.claude/state.json` `connectors` already has entries, they answered before this setup was interrupted:
don't ask again; go straight to checking the sources not yet recorded `"live"` or `"off"`.

Each number covers fixed source keys: 1 → `email`, `calendar`, `transcripts`, `teams`, `drive` ·
2 → `slack` · 3 → `jira`, `confluence` · 4 → `github` · 5 → `figma` · 6 → `lucid` · 7 → `monday` ·
8 → `usertesting`. Read the reply generously (names instead of numbers work too). Every key under a number
they turned down is recorded as `"off"` in `.claude/state.json` `connectors.<key>`, now, and is never
checked or pulled.

**Then check only the sources they kept.** For each one, check whether its connector tool exists and
works (for `github`, the `gh` command-line tool signed in during step 1 counts):
- **Working:** make one small test call, and record `"live"` for each of its keys.
- **Unavailable** (blocked by their workplace or their plan): record `"unavailable"` and say so in one
  line. Do this per key: if Teams is blocked but email works, only `teams` is unavailable.
- **Missing:** collect it for the walk-through below.

**Walk them through connecting the missing ones**, in one message. Start with why: *"Connecting is a
one-time sign-in that lets me read that tool on your behalf. You can disconnect any of them later in the
same place."* Then, for each, the exact path (Claude
settings → Connectors → find it by name → Connect, and approve the sign-in window that opens). Ask them to
say "done" when they've finished, or "skip" for any they'd rather leave. When they say "done", check those
sources again and record each working one as `"live"`. A source that still isn't working (some only show up
in a new session) is recorded `"not-connected"` with one line saying the next catch-up picks it up
automatically once it's connected. Never ask more than once; after this, move on.

**Close the step with one line:** *"If there's another source you want to pull from, like Notion, Google or
Zoom, just tell me and I'll hook it in."* How to hook one in is in CLAUDE.md under "Adding a source".

## 4. Schedule the morning catch-up in the cloud

> **Explain:** Now I'm scheduling your **morning catch-up**. It's a routine: a copy of me that runs on its
> own in the cloud every weekday at 7am, even when your computer is off. It opens your private copy on
> GitHub, reads what's new in your connected tools since the last run, files it into the right projects,
> and writes you a briefing (`BRIEFING.md`): what changed, what needs you, and where to start. So when you
> sit down in the morning and say *"catch me up"*, the work is already done.

Create a **Claude Code cloud routine** yourself, using the `/schedule` capability: weekdays at 7am in
their time zone, on their GitHub copy of this repo, with the prompt `catch me up`. Cloud routines are
scheduled in UTC, so convert their 7am local time to the matching UTC cron time yourself. It runs in the
cloud, so their computer can be off.

**Attach only connectors verified to work in a cloud routine**, and only the ones recorded `"live"` in
step 3. Each needs both its connector ID (from the connector list) and its address, or the attach fails:

| Source | Connector | Address |
|---|---|---|
| `email`, `calendar`, `transcripts`, `teams`, `drive` | Microsoft 365 | `https://microsoft365.mcp.claude.com/mcp` |
| `slack` | Slack | `https://mcp.slack.com/mcp` |
| `jira`, `confluence` | Atlassian | `https://mcp.atlassian.com/v1/mcp` |
| `figma` | Figma | `https://mcp.figma.com/mcp` |
| `lucid` | Lucid | `https://mcp.lucid.app/mcp` |
| `usertesting` | UserTesting | `https://ai.usertesting.com/mcp` |
| `monday` | monday.com | `https://mcp.monday.com/mcp` |

Add each attached connector's tools to the routine's allowed tools.
- **Never attach or mention anything outside this table.** `github` is **desktop-only**: the cloud can only
  open the brain's own repository, so it can't read their other repositories, pull requests or issues.
  GitHub is caught up whenever they run catch-up on their computer, and that's expected, not a problem.
- Tell them, in the step's explanation, which sources the morning run covers and that GitHub catches up
  when they work on their computer. Say it as how it works, not
  as a failure.
- **Read the routine back** right after creating it, and check that every `"live"` connector is both
  attached and in its allowed tools. A connector missing from either is silently absent from every
  morning run. Add anything missing and read it back again.
- If a connector from the table still can't be attached, tell them once, in one line, which one, and that
  it catches up when they work on their computer.
- If the routine needs Claude's GitHub app to have access to the repo, tell them one browser window will
  open to approve, and why: *"The cloud copy of me needs your permission to open your private brain on
  GitHub. You're only giving it access to this one repository."*
- **Only if a cloud routine can't be created:** fall back to a desktop scheduled task, and tell them
  plainly it only runs while their computer is on.
- If neither can be created, tell them in one line that catch-up will run whenever they say "catch me up".
- Record which kind was created in `.claude/state.json` as `"catch_up_schedule": "cloud"` or
  `"desktop"`. Leave it `null` if neither could be made.

## 5. Seed the brain in the background (60 days)

**If no source is `live`:** skip the dispatch below entirely. Write nothing invented — leave
`me/about-me.md`, `me/voice.md`, `reference/people.md`, and projects as placeholders — tell them in one
line that the brain will fill in as they work and whenever a source gets connected, mark step 5 done,
and move to step 6.

**Otherwise:** add `"seeding"` to `setup.waiting_on` in `.claude/state.json` before dispatching — this is
also what tells the session-start hook to explain an interrupted setup if the session ends before this
step finishes. Then dispatch **one background agent** (the Agent tool, with `run_in_background`) with
these exact instructions, over the **last 60 days** of every `live` source, writing into this folder:

- **No git, and no shell file operations at all.** Skip catch-up's step 1 (no fetch, checkout, or merge)
  and step 7 (no save). It also **skips `inbox/` processing entirely** (an `inbox/` folder only exists if
  the user asked for one later): catch-up step 2's "process every
  file in `inbox/`" and step 3's `git mv`/`git rm` inbox filing don't run here — the agent has no shell
  access to move or delete files safely alongside the main session, and a plain `mv`/`rm` would hit a
  permission prompt nobody's there to answer. Anything still in `inbox/` waits for the next normal
  catch-up (foreground or scheduled), which files it the usual way with `git mv`/`git rm`. The agent
  uses only the file tools (read/write inside this folder) and connector tools — never a shell command.
  Otherwise, build the profile, then run catch-up's steps 2 through 5 as the backfill.
- **State-file writes are surgical.** The only `.claude/state.json` keys it ever touches are
  `last_pulled` and `connectors`. Immediately before each write, re-read the file fresh from disk and
  change only those keys — the main session is working in this same folder at the same time, and must
  never be overwritten with a stale copy.
- **Backfill window, per source:** the later of 60 days ago and that source's current `last_pulled` — a
  re-run never re-pulls a source from scratch.
- **De-dupe, don't duplicate.** Before adding a note, to-do, person, term, or decision, check whether it
  already exists and update it instead of adding a new one. Profile files (`me/about-me.md`,
  `me/voice.md`, `reference/people.md`, each project's `STATE.md`) are rewritten in place, never
  appended to.
- **Finish by saying exactly "seeding finished"** as its last message, once both the profile and the
  backfill are done.

1. **Build their profile:**
   - **`me/about-me.md`:** role (from email signature, calendar and meeting context), what they're
     focused on right now (recurring meetings, the busiest recent threads), who they work with most,
     and how they like to work where it's evident. Remove the "Not set up yet" line.
   - **`reference/people.md`:** the ~15 people they meet and email most, with role and team where
     signatures or meetings show it.
   - **`me/voice.md`:** 3–5 short excerpts of things they wrote (sent email or chat) under "Examples",
     with anything sensitive removed, plus a few "Patterns" observed (length, tone, greetings and
     sign-offs).
   - **Projects:** a `projects/<name>/STATE.md` for each distinct effort, each added to `INDEX.md`.
     Follow catch-up's "Project size" rule: one project per effort with its own goal or deliverable,
     **never** an umbrella for a team, area or theme. When in doubt, split. Sixty days of work usually
     means more than ten projects.
   - **Marking:** every inferred statement is marked `guessed:` with its source (for example "guessed:
     from calendar, weekly 'Launch sync'").
   - **Never ask a question in this step.**
2. **Backfill:** run catch-up's steps 2 through 5 (not step 1, not step 6, and skipping the `inbox/`
   sub-steps in steps 2 and 3 — see above) with the window above, for every live source. Let it build
   out projects, people, glossary, to-dos, and decisions. Decisions
   found this way get `provenance: guessed` unless a source shows the user decided.

- **Read everything, in small pieces.** Follow catch-up's "Pull in small pieces" rules exactly: week by
  week, oldest first, small pages, every page followed, Jira split into assigned, reported and watched.
  Sixty days of a busy calendar or inbox is hundreds of items, so one big query always overflows. Set
  each source's `last_pulled` only as far as it was read in full.
- **Skip `github`.** It needs the command line, which this agent doesn't have. The main session pulls it
  (see below).

What's pulled, per live source, over the 60 days: the same items catch-up's step 2 lists for that
source (for documents, design files, diagrams, repositories and analytics, anything they created, edited
or viewed in the window, plus files of that kind linked from the other sources). Never pull from a source
recorded `"off"`.

> **Explain:** Now I'm filling your brain from the last 60 days of your work. This is what makes it
> useful on day one instead of a month from now. From your connected tools I'll write a short profile
> (your role and current focus), the people you work with most, a few examples of how you write so my
> drafts sound like you, and a folder for each project with where it stands and its open to-dos. Anything
> I work out on my own is marked **guessed**, with where I got it, so you know what to double-check. It
> runs in the background and can take a while. You can keep working here in the meantime; just keep this
> session open until it finishes.

**Meanwhile, in this main session:** don't run `save` — including CLAUDE.md's save-as-you-go rule —
until the agent's last message says "seeding finished" (the `save` skill enforces this itself while
`"seeding"` is in `setup.waiting_on`). Don't write `last_pulled` or `connectors` yourself in the
meantime either, so the two sessions never race on the same keys.

**GitHub, from this main session:** if `github` is `live`, pull it yourself while the agent runs, using
the `gh` command-line tool, read-only: over the last 60 days, the repositories they pushed to, and the
pull requests and issues they opened, reviewed or commented on (`gh search prs`/`gh search issues` with
`--author`, `--reviewed-by`, `--commenter` and an `updated:>=` date). Hold what you find in this session;
don't write files or `last_pulled` until the agent says "seeding finished". Then file it the catch-up way
(projects, people, to-dos) and set `last_pulled.github`.

When the agent reports "seeding finished," file the GitHub findings, remove `"seeding"` from
`setup.waiting_on`, and mark step 5 done. If the session ends before that message arrives, resuming re-runs step 5 from the top — the
window and de-dupe rules above make that safe.

## 6. How it works

While the seeding from step 5 runs in the background, explain the idea of the brain, not its parts. Don't
name skills or files, and don't list tips: details like correcting things, handing over files, or keeping
secrets in `private/` get explained the first time they come up (CLAUDE.md rule 15). Lead in with: *"While
that runs, here's how your brain works. Almost all of it happens on its own."* Then say this (the same text
is in the README's "How it works"). In the first bullet, name the sources **they actually connected**, in
plain words (for example "your email and calendar, meeting transcripts, and Slack conversations"), never
a source they turned off or that isn't connected:

- **It fills itself in from the sources you connected.** Every weekday morning, your brain reads
  what's new in the tools you connected during setup: your email and calendar, meeting transcripts,
  Teams and Slack conversations, Jira tickets and Confluence pages, and the design and project tools you
  added. Want a fresh pull any time? Just say *"catch me up"*.
- **It sorts everything into the right place.** Each piece lands where it belongs: a new person goes on
  your people list, an update goes to its project, a to-do gets added or checked off, and a decision gets
  recorded.
- **It remembers your sessions, too.** When you brainstorm, brain-dump or decide something with Claude,
  the ideas and decisions are saved into your brain as you go. Saying *"save"* at the end of a session
  catches anything since the last automatic save.
- **It gets you up to speed on any project.** Say *"let's work on the launch"* and Claude brings in what
  matters: where it stands, open to-dos, recent decisions, and a suggested next step.
- **It learns your repeat work.** When you do the same kind of task a few times, Claude offers to turn it
  into a shortcut you can run with one sentence.

Close with the point of it all: *"The idea is that your brain stays current from everywhere your work
already happens. Whenever you work here, Claude is already up to speed, and you never have to hunt down
information again."*

## 7. Tour

Once step 5 is done (the background agent reported "seeding finished," or there was no live source to
seed from), show a short "here's what I built": each project with a link to its `STATE.md`, plus how
many people, terms, and to-dos were added. Invite corrections, and say why they matter: *"This is my first
draft of your work, and some of it is guessed. Anything wrong? Just tell me in plain words, like 'Sam
leads that team' or 'that project is done', and I'll fix it. Every correction makes the next session
better."* (Not-connected sources were already mentioned once, in step 3 — don't repeat it here.)

## 8. Save

Record step 8 as done in `.claude/state.json` **first** — so the `save` skill's own commit includes it —
then run `save`.

> **Explain (one line):** *"Saving now: everything I built is stored on this computer and backed up to
> your private copy on GitHub. From here on, saving happens on its own after each meaningful piece of
> work."*

## 9. Last thing

Now that save has run, remove the setup files — but only after the Save step has actually finished;
removal never happens if setup stopped early:
1. Delete the setup files: `git rm -r .claude/skills/get-set-up`.
2. Edit README.md to delete the whole `## Contributing` and `## For Claude: setting up from a new session`
   sections, from each heading to the end of that section. They're about the public template, not
   their own brain.
3. Edit CLAUDE.md's "Starting a session" paragraph: replace the sentence that offers to run
   `get-set-up` with: "If the user asks to set up again, tell them setup is already done; to add a
   source, connect it in Settings → Connectors and the next catch-up includes it."
4. `git add -A README.md CLAUDE.md`, commit with the message "Setup complete: removed the setup files",
   and push. In a session on a branch, use the save skill's step 6 route.

> **Explain (one line):** *"Setup's done, so I've removed its instructions from your brain. That way it
> can never run again by accident, and your brain only holds your own work."*

Record nothing new in `.claude/state.json` for this — `setup.done_steps` already shows setup is
complete.

The closing message stays the same. Tell them, as the very last thing: **from now on, open your brain folder.** In
Code, choose **Local**, then pick the **`<repo-name>`** folder (say the actual folder name, for example
`my-2nd-brain`) in your home folder. Start a new session there now. Explain why: opening that folder is
what lets me read your brain at the start of every session, and what turns on the automatic saves and
backups.
