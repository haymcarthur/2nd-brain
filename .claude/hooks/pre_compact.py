#!/usr/bin/env python3
"""PreCompact hook: commit and push whatever is already written, right before the session compacts.

The safety net under context_check.py. That nudge asks Claude to run `save` at 70% (which updates
STATE.md and the rest); this one runs no matter what, so a compaction can never lose work that's on disk.
It stages the same paths as the `save` skill (never `private/`), skips during setup's background
seeding, and never blocks or errors out.
"""
import json
import os
import subprocess
import sys

COMMIT_MESSAGE = "save: automatic backup before compacting"
SAVE_PATHS = ["projects", "inbox", "me", "reference", "decisions", "INDEX.md", "BRIEFING.md",
              ".claude/state.json", ".claude/skills"]
TIMEOUT = 20


def _git_env():
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"
    return env


def _git(cwd, *args):
    """Run git; return (ok, stdout). Never raises."""
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=TIMEOUT,
                           stdin=subprocess.DEVNULL, env=_git_env())
        return r.returncode == 0, r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return False, ""


def _seeding(cwd):
    try:
        with open(os.path.join(cwd, ".claude", "state.json"), encoding="utf-8") as f:
            state = json.load(f)
        return "seeding" in (state.get("setup") or {}).get("waiting_on", [])
    except (OSError, ValueError, AttributeError, TypeError):
        return False


def backup(cwd):
    """Returns "skip", "clean", "saved", or "failed"."""
    ok, inside = _git(cwd, "rev-parse", "--is-inside-work-tree")
    if not ok or inside != "true" or _seeding(cwd):
        return "skip"
    paths = [p for p in SAVE_PATHS if os.path.exists(os.path.join(cwd, p))]
    if paths:
        _git(cwd, "add", "-A", "--", *paths)
    staged, _ = _git(cwd, "diff", "--cached", "--quiet")
    if staged:  # exit 0 means nothing staged
        return "clean"
    ok, _ = _git(cwd, "commit", "-q", "-m", COMMIT_MESSAGE)
    if not ok:
        return "failed"
    has_remote, _ = _git(cwd, "remote", "get-url", "origin")
    if not has_remote:
        return "saved"
    _, branch = _git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "main":
        if not _git(cwd, "pull", "-q", "--rebase", "--autostash")[0]:
            _git(cwd, "rebase", "--abort")
        _git(cwd, "push", "-q")
    else:
        _git(cwd, "push", "-q", "-u", "origin", branch)
    # A failed push still leaves a local commit; the next save or catch-up pushes it.
    return "saved"


def main():
    try:
        data = json.loads(sys.stdin.read() or "{}")
        cwd = data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if backup(cwd) == "saved":
            print(json.dumps({"systemMessage": "Backed up your brain before compacting."}))
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
