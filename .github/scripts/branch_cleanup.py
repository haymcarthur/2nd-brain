#!/usr/bin/env python3
"""Delete branches whose work is already in the default branch. Never touches unmerged work.

Run by .github/workflows/branch-cleanup.yml, with GITHUB_TOKEN (contents: write, pull-requests: read).
"""
import argparse
import json
import os
import subprocess
import sys


def should_delete(branch, default, is_ancestor, has_merged_pr):
    if branch == default:
        return False
    return is_ancestor or has_merged_pr


def plan(branches, default):
    return [b["name"] for b in branches
            if should_delete(b["name"], default, b["is_ancestor"], b["has_merged_pr"])]


def _run(*args):
    return subprocess.run(list(args), capture_output=True, text=True)


def parse_slurped(stdout):
    """Parse gh api --slurped output: returns [] for empty or invalid JSON, flattens nested lists."""
    if not stdout.strip():
        return []
    try:
        data = json.loads(stdout)
        # Slurp returns a list of pages; flatten if pages are lists
        result = []
        if isinstance(data, list):
            for page in data:
                if isinstance(page, list):
                    result.extend(page)
                else:
                    result.append(page)
        return result
    except (json.JSONDecodeError, ValueError):
        return []


def _gh_list(path):
    """Run gh api --paginate --slurp and return a flat list. Returns [] on error."""
    r = _run("gh", "api", "--paginate", "--slurp", path)
    if r.returncode != 0:
        return []
    return parse_slurped(r.stdout)


def _gh_obj(path):
    """Run gh api (no paginate) and return a dict. Returns {} on error."""
    r = _run("gh", "api", path)
    if r.returncode != 0 or not r.stdout.strip():
        return {}
    try:
        return json.loads(r.stdout)
    except (json.JSONDecodeError, ValueError):
        return {}


def merged_pr_matches_tip(prs: list, tip: str) -> bool:
    """True only if a merged PR's head sha equals the branch's current tip.

    A squash/rebase merge leaves the branch un-mergeable into the default branch by ancestry, so a
    merged-PR match is the other proof of "already landed" -- but only if the PR's recorded head sha is
    still the branch's tip. If the branch moved past that merge (new commits pushed after merging), the
    match no longer holds and the branch must not be deleted.
    """
    return any(pr.get("merged_at") and pr.get("head", {}).get("sha") == tip for pr in prs)


def facts_for(repo, name, default):
    is_ancestor = _run("git", "merge-base", "--is-ancestor", f"origin/{name}", f"origin/{default}").returncode == 0
    tip = _run("git", "rev-parse", f"origin/{name}").stdout.strip()
    owner = repo.split("/")[0]
    prs = _gh_list(f"repos/{repo}/pulls?state=closed&head={owner}:{name}")
    has_merged_pr = merged_pr_matches_tip(prs, tip)
    return {"name": name, "is_ancestor": is_ancestor, "has_merged_pr": has_merged_pr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch")
    args = ap.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    default = _gh_obj(f"repos/{repo}").get("default_branch", "main")
    _run("git", "fetch", "--prune", "origin")
    names = [args.branch] if args.branch else [b["name"] for b in _gh_list(f"repos/{repo}/branches")]
    branches = [facts_for(repo, n, default) for n in names]
    for name in plan(branches, default):
        r = _run("gh", "api", "-X", "DELETE", f"repos/{repo}/git/refs/heads/{name}")
        print(f"{'deleted' if r.returncode == 0 else 'could not delete'}: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
