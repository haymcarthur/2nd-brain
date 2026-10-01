# 2nd Brain

A second brain for your AI: a folder of small files it reads so it already knows your projects,
people, and preferences before you start. It keeps itself up to date.

It runs in **Claude Code in the Claude desktop app** (a paid Claude plan is needed). There's no terminal.

## Start

1. Have a [GitHub](https://github.com/signup) account.
2. Open the Claude desktop app and choose **Code**. Leave it on **Local** and **No folder**.
3. Paste this and send it:

   > Set up my second brain from github.com/haymcarthur/2nd-brain and call it my-2nd-brain

   Change **my-2nd-brain** to whatever you'd like to call yours (for example `sams-brain`) before you
   send it.

Claude makes a **private** copy on your GitHub account, puts it in a folder with the name you chose
(**my-2nd-brain** if you kept it) in your home folder, and walks you through the rest: connecting your
work tools and filling the brain from the last 60 days of your work. It connects Microsoft 365, Slack,
Atlassian (Jira and Confluence), GitHub, Figma, Lucid, monday.com and UserTesting, and you can leave out any
you don't use. Want another source, like Notion, Google or Zoom? Just ask and it hooks it in.

> On a Mac, the first time, you may be asked to install Apple's developer tools. Click **Install**.

**After setup, always open that folder:** in Code, choose **Local**, then pick the folder with the name
you chose (**my-2nd-brain** if you kept it). That's where your brain lives, and it's what turns on
automatic saving.

## How it works

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

The idea is that your brain stays current from everywhere your work already happens. Whenever you work in
it, Claude is already up to speed, and you never have to hunt down information again.

## Tips

- **To hand Claude a file**, drop it in your Downloads folder and tell Claude it's there, or attach it in
  chat.
- **Correct it out loud.** *"That's wrong, Sam leads that team"* gets fixed right away.
- **Change your sources any time.** *"Stop pulling Slack"* or *"start pulling from Lucid"*.
- **Keep secrets out.** Anything sensitive goes in `private/`, which never leaves your computer.

## What's inside

| Folder | What it holds |
|---|---|
| `me/` | About you: role, priorities, how you write and work |
| `reference/` | People, terms, links, company rules |
| `projects/` | One folder per project: current state, to-dos, notes |
| `decisions/` | One file per decision |
| `private/` | Sensitive notes, never uploaded |
| `BRIEFING.md` | The latest catch-up: what changed, where things stand, where to start |

## Contributing

Suggestions are welcome. [Open an issue](https://github.com/haymcarthur/2nd-brain/issues) to report a
problem or share an idea, or open a pull request with a change.

## For Claude: setting up from a new session

If the user pasted the bootstrap prompt in a session that isn't already inside their brain folder, do this:

1. Check for the `gh` command-line tool and that they're signed in. Install it if missing, and run
   `gh auth login --web` if not signed in (a browser window opens to approve).
2. Take `<name>` from the prompt's "call it …" part. Turn it into a valid GitHub repo name: lowercase
   it, turn spaces into hyphens, and keep only letters, digits, `-`, `_` and `.`. Fall back to
   `my-2nd-brain` if no name was given or nothing valid is left. Create their private copy: `gh repo
   create <their-github-username>/<name> --template haymcarthur/2nd-brain --private`. If that name is
   taken, add `-2` (then `-3`, and so on).
3. Wait a few seconds, then clone it into the home folder: `git clone https://github.com/<their-github-username>/<name>.git ~/<name>`. If it clones empty, wait a few seconds and retry, up to 3 times. If `~/<name>` already exists and isn't empty, use the next free `-2`/`-3` name for the folder.
4. **Never clone `haymcarthur/2nd-brain` itself** — that's the public template, not their copy.
5. Read `~/<name>/.claude/skills/get-set-up/SKILL.md` and continue from its step 2, working in that folder.
