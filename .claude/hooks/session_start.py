#!/usr/bin/env python3
"""SessionStart hook: point Claude at the brain, and flag if the session isn't on `main`.

Runs before Claude reads anything, so it's the only way to catch a session that opened on a new
branch or in a worktree. Never errors out.
"""
import json
import os
import subprocess
import sys
import time

SETUP_DONE_STEP = 8
SYNC_SOURCES = ("startup", "clear")
BRANCH_CAP = 20
SYNC_BUDGET = 8.0

REORIENT = (
    "This folder is a 2nd Brain. Before answering, read INDEX.md, then only the files the user's "
    "request needs. For any project, read its STATE.md first."
)
AFTER_COMPACT = (
    " The session was just compacted: re-read INDEX.md and the STATE.md of the project you were "
    "working on before continuing."
)
NOT_A_REPO = (
    " This folder isn't a git repo yet. If the user wants a second brain here, run the `get-set-up` skill."
)
WORKTREE = (
    " WARNING: this session is running in a separate worktree, not the main folder. Tell the user in "
    "one line to start new sessions with the worktree option off. When you save, bring the work back "
    "to `main` as the `save` skill describes."
)
BRANCH = (
    " WARNING: this session is on branch `{branch}`, not `main`. If you can, switch to `main` before "
    "doing any work (`git checkout main`, then `git pull`). If you can't (a cloud or phone session), "
    "work here and the `save` skill will bring the work back to `main`."
)
SETUP_NUDGE = (
    " Setup isn't finished (last completed step: {last}{waiting}). Open your first reply by telling "
    "the user in one line where setup stopped and that they can say 'keep setting me up' to continue."
)
STRAY = (
    " There is unmerged work on {names}. Before anything else, merge it into main as the catch-up "
    "skill's step 1 describes."
)
STRAY_CAP = 5
SYNC_TIMEOUT = 5


def _git_env():
    """Never let a git call block on a prompt (terminal or SSH) or inherit our stdin."""
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"
    return env


def _git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=10,
                        stdin=subprocess.DEVNULL, env=_git_env())
    return r.stdout.strip() if r.returncode == 0 else None


def _git_quiet(cwd, args, timeout=SYNC_TIMEOUT):
    """Run a git command, swallowing any failure/timeout. Returns stdout, or "" on failure."""
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=timeout,
                            stdin=subprocess.DEVNULL, env=_git_env())
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def git_facts(cwd):
    try:
        if _git(cwd, "rev-parse", "--is-inside-work-tree") != "true":
            return {"is_repo": False, "branch": None, "is_worktree": False}
        branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
        git_dir = _git(cwd, "rev-parse", "--absolute-git-dir")
        common = _git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
        return {"is_repo": True, "branch": branch, "is_worktree": bool(git_dir and common and git_dir != common)}
    except (OSError, subprocess.SubprocessError):
        return {"is_repo": False, "branch": None, "is_worktree": False}


def read_state(cwd):
    """Read .claude/state.json from the project directory. None on any failure."""
    try:
        with open(os.path.join(cwd, ".claude", "state.json"), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def sync_main(cwd):
    """Fetch and fast-forward `main` from origin. Any failure (offline, no remote, diverged) is silent."""
    _git_quiet(cwd, ["fetch", "--prune", "--quiet"])
    _git_quiet(cwd, ["merge", "--ff-only", "--quiet", "origin/main"])


def remote_branches(cwd):
    """Remote-tracking branch names under origin, excluding origin/main and its origin/HEAD alias.

    Uses the full refname, not %(refname:short): git shortens refs/remotes/origin/HEAD to the bare
    "origin" (dropping /HEAD), which would never match an "origin/HEAD" exclusion and would then get
    treated as a real branch (and falsely reported as stray whenever local main is behind origin/main).
    """
    out = _git_quiet(cwd, ["for-each-ref", "--format=%(refname)", "refs/remotes/origin"])
    if not out:
        return []
    excluded = ("refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    prefix = "refs/remotes/"
    return [ref[len(prefix):] for ref in out.splitlines() if ref not in excluded and ref.startswith(prefix)]


def branch_commit_counts(cwd, branches, deadline=None):
    """{branch: number of commits in branch not in main}, for each of `branches`.

    Stops issuing new `rev-list` calls once `deadline` (a time.monotonic() value) has passed.
    """
    counts = {}
    for b in branches:
        if deadline is not None and time.monotonic() >= deadline:
            break
        out = _git_quiet(cwd, ["rev-list", "--count", f"main..{b}"])
        try:
            counts[b] = int(out)
        except ValueError:
            counts[b] = 0
    return counts


def stray_branches(counts: dict) -> list:
    """Pure: which branches (from a {branch: count} map) have commits not in main."""
    return [b for b, c in counts.items() if c > 0]


def sync_and_find_stray(cwd):
    """Sync `main`, then find remote branches with unmerged commits, inside one time budget."""
    deadline = time.monotonic() + SYNC_BUDGET
    sync_main(cwd)
    if time.monotonic() >= deadline:
        return []
    branches = remote_branches(cwd)[:BRANCH_CAP]
    if time.monotonic() >= deadline:
        return []
    return stray_branches(branch_commit_counts(cwd, branches, deadline=deadline))


def format_stray(branches):
    if not branches:
        return ""
    shown = branches[:STRAY_CAP]
    extra = len(branches) - len(shown)
    names = ", ".join(shown)
    if extra > 0:
        names += f", and {extra} more"
    return STRAY.format(names=names)


def setup_nudge(setup):
    """Build the setup-resume nudge, or "" when setup is complete/absent/malformed."""
    if not isinstance(setup, dict):
        return ""
    raw_done = setup.get("done_steps")
    if not isinstance(raw_done, list):
        raw_done = []
    # Only real ints count: a stray "8" string must not look like the done step 8.
    done_steps = [n for n in raw_done if isinstance(n, int) and not isinstance(n, bool)]
    if SETUP_DONE_STEP in done_steps:
        return ""
    last = max(done_steps) if done_steps else None
    waiting_on = setup.get("waiting_on")
    if not isinstance(waiting_on, list) or not waiting_on:
        waiting = ""
    else:
        waiting = "; waiting on: " + ", ".join(str(w) for w in waiting_on)
    return SETUP_NUDGE.format(last=last if last is not None else "none", waiting=waiting)


def build_message(facts, source, stray=None, setup=None):
    msg = REORIENT
    if source == "compact":
        msg += AFTER_COMPACT
    if not facts["is_repo"]:
        return msg + NOT_A_REPO
    if facts["is_worktree"]:
        msg += WORKTREE
    elif facts["branch"] and facts["branch"] != "main":
        msg += BRANCH.format(branch=facts["branch"])
    if stray:
        msg += format_stray(stray)
    msg += setup_nudge(setup)
    return msg


def main(stdin_text):
    try:
        data = json.loads(stdin_text)
    except ValueError:
        data = {}
    cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    source = data.get("source", "startup")
    facts = git_facts(cwd)
    stray = None
    if (facts["is_repo"] and not facts["is_worktree"] and facts["branch"] == "main"
            and source in SYNC_SOURCES):
        stray = sync_and_find_stray(cwd)
    state = read_state(cwd)
    setup = state.get("setup") if isinstance(state, dict) else None
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": build_message(facts, source, stray=stray, setup=setup),
    }})


if __name__ == "__main__":
    try:
        print(main(sys.stdin.read()))
    except Exception:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": REORIENT}}))
    sys.exit(0)
