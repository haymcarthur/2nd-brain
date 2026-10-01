import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from test_structure import repo_root


def load():
    path = repo_root() / ".claude/hooks/session_start.py"
    spec = importlib.util.spec_from_file_location("session_start", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True)


def make_repo():
    d = tempfile.mkdtemp()
    git(d, "init", "-q", "-b", "main")
    git(d, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
    return d


def write_state(d, state):
    claude_dir = pathlib.Path(d) / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "state.json").write_text(json.dumps(state))


def make_repo_with_remote():
    """A local repo on main, pushed to a local bare 'remote'."""
    remote = tempfile.mkdtemp()
    git(remote, "init", "-q", "--bare", "-b", "main")
    local = tempfile.mkdtemp()
    git(local, "init", "-q", "-b", "main")
    git(local, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
    git(local, "remote", "add", "origin", remote)
    git(local, "push", "-q", "-u", "origin", "main")
    return local, remote


def commit(cwd, msg):
    git(cwd, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", msg)


def clone_dir(remote):
    """A real `git clone` (not init+remote add), so origin/HEAD exists like it does for real users."""
    d = tempfile.mkdtemp()
    git(d, "clone", "-q", remote, ".")
    return d


class TestSessionStart(unittest.TestCase):
    def setUp(self):
        self.ss = load()

    def context(self, out):
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    def test_on_main_just_reorients(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertIn("INDEX.md", msg)
        self.assertNotIn("WARNING", msg)

    def test_non_main_branch_detected(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        git(d, "checkout", "-q", "-b", "claude/xyz")
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertIn("claude/xyz", msg)
        self.assertIn("main", msg)

    def test_worktree_detected(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        wt_parent = tempfile.mkdtemp()
        wt = wt_parent + "/wt"
        git(d, "worktree", "add", "-q", "-b", "wt-branch", wt)
        self.addCleanup(shutil.rmtree, wt_parent, ignore_errors=True)
        self.addCleanup(subprocess.run, ["git", "-C", d, "worktree", "remove", "--force", wt],
                         capture_output=True)
        facts = self.ss.git_facts(wt)
        self.assertTrue(facts["is_worktree"])
        self.assertIn("worktree", self.ss.build_message(facts, "startup").lower())

    def test_not_a_git_repo(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertIn("get-set-up", msg)

    def test_after_compact_mentions_state(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "compact"})))
        self.assertIn("STATE.md", msg)

    def test_garbage_stdin_still_reorients(self):
        # No "cwd" in the payload means main() falls back to CLAUDE_PROJECT_DIR / os.getcwd(). Point
        # that at an isolated temp dir so this never touches the real repo (or its real network remote).
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        old = os.environ.get("CLAUDE_PROJECT_DIR")

        def restore():
            if old is None:
                os.environ.pop("CLAUDE_PROJECT_DIR", None)
            else:
                os.environ["CLAUDE_PROJECT_DIR"] = old

        self.addCleanup(restore)
        os.environ["CLAUDE_PROJECT_DIR"] = d
        self.assertIn("INDEX.md", self.context(self.ss.main("not json")))

    def test_setup_incomplete_nudges_with_last_step_and_waiting(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        write_state(d, {"setup": {"done_steps": [1, 2, 5], "waiting_on": ["seeding"]}})
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertIn("Setup isn't finished", msg)
        self.assertIn("last completed step: 5", msg)
        self.assertIn("waiting on: seeding", msg)
        self.assertIn("keep setting me up", msg)

    def test_setup_incomplete_no_steps_yet(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        write_state(d, {"setup": {"done_steps": [], "waiting_on": []}})
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertIn("Setup isn't finished", msg)
        self.assertIn("last completed step: none", msg)
        self.assertNotIn("waiting on:", msg)

    def test_setup_complete_no_nudge(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        write_state(d, {"setup": {"done_steps": [1, 2, 3, 4, 5, 6, 7, 8], "waiting_on": []}})
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertNotIn("Setup isn't finished", msg)

    def test_missing_state_json_no_nudge_no_error(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertNotIn("Setup isn't finished", msg)

    def test_garbage_state_json_no_nudge_no_error(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        claude_dir = pathlib.Path(d) / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "state.json").write_text("not json{{{")
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertNotIn("Setup isn't finished", msg)

    def test_state_json_missing_setup_key_no_nudge(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        write_state(d, {"last_pulled": {}, "connectors": {}, "catch_up_schedule": None})
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertNotIn("Setup isn't finished", msg)

    def test_setup_nudge_ignores_non_int_done_steps(self):
        # A stray string "9" (or "2") must not satisfy completion or count toward "last completed".
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        write_state(d, {"setup": {"done_steps": [1, "2", 5, "8"], "waiting_on": []}})
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertIn("Setup isn't finished", msg)
        self.assertIn("last completed step: 5", msg)


class TestSessionStartSync(unittest.TestCase):
    def setUp(self):
        self.ss = load()

    def context(self, out):
        return json.loads(out)["hookSpecificOutput"]["additionalContext"]

    def test_stray_branch_reported(self):
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        git(local, "checkout", "-q", "-b", "feature")
        commit(local, "feature work")
        git(local, "push", "-q", "-u", "origin", "feature")
        git(local, "checkout", "-q", "main")
        msg = self.context(self.ss.main(json.dumps({"cwd": local, "source": "startup"})))
        self.assertIn("origin/feature", msg)
        self.assertIn("unmerged work", msg)
        self.assertIn("catch-up skill's step 1", msg)

    def test_merged_branch_not_reported(self):
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        git(local, "checkout", "-q", "-b", "feature")
        commit(local, "feature work")
        git(local, "checkout", "-q", "main")
        git(local, "merge", "-q", "--no-edit", "feature")
        git(local, "push", "-q", "origin", "main")
        git(local, "push", "-q", "-u", "origin", "feature")
        msg = self.context(self.ss.main(json.dumps({"cwd": local, "source": "startup"})))
        self.assertNotIn("unmerged work", msg)

    def test_remote_main_fast_forwarded(self):
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        local2 = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, local2, ignore_errors=True)
        git(local2, "clone", "-q", remote, ".")
        commit(local2, "from local2")
        git(local2, "push", "-q", "origin", "main")
        remote_head = git_capture(local2, "rev-parse", "HEAD")
        self.ss.main(json.dumps({"cwd": local, "source": "startup"}))
        local_head = git_capture(local, "rev-parse", "HEAD")
        self.assertEqual(local_head, remote_head)

    def test_no_remote_no_error(self):
        d = make_repo()
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertNotIn("unmerged work", msg)
        self.assertIn("INDEX.md", msg)

    def test_stray_branches_pure(self):
        self.assertEqual(
            sorted(self.ss.stray_branches({"origin/a": 0, "origin/b": 2, "origin/c": 1})),
            ["origin/b", "origin/c"],
        )

    def test_build_message_caps_stray_list_at_five(self):
        branches = [f"origin/b{i}" for i in range(7)]
        facts = {"is_repo": True, "branch": "main", "is_worktree": False}
        msg = self.ss.build_message(facts, "startup", stray=branches)
        for b in branches[:5]:
            self.assertIn(b, msg)
        self.assertNotIn("b6", msg)
        self.assertIn("and 2 more", msg)

    def test_clean_clone_with_origin_head_reports_nothing(self):
        # A real clone sets up the refs/remotes/origin/HEAD symbolic ref. %(refname:short) shortens
        # that to plain "origin", which must not surface as a fake stray branch.
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        d = clone_dir(remote)
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        msg = self.context(self.ss.main(json.dumps({"cwd": d, "source": "startup"})))
        self.assertNotIn("unmerged work", msg)

    def test_diverged_main_not_reported_and_untouched(self):
        # local has an unpushed commit; the remote's main also moved. ff-only can't merge, so local
        # main must be left exactly as it was (no merge commit), and the origin/HEAD alias for the
        # now-ahead origin/main must not be reported as a spurious stray branch.
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        other = clone_dir(remote)
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        commit(other, "remote-side commit")
        git(other, "push", "-q", "origin", "main")
        commit(local, "local-side commit")
        head_before = git_capture(local, "rev-parse", "HEAD")
        msg = self.context(self.ss.main(json.dumps({"cwd": local, "source": "startup"})))
        self.assertNotIn("unmerged work", msg)
        self.assertEqual(git_capture(local, "rev-parse", "HEAD"), head_before)

    def test_compact_source_does_not_sync(self):
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        other = clone_dir(remote)
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        commit(other, "newer remote commit")
        git(other, "push", "-q", "origin", "main")
        head_before = git_capture(local, "rev-parse", "HEAD")
        self.ss.main(json.dumps({"cwd": local, "source": "compact"}))
        self.assertEqual(git_capture(local, "rev-parse", "HEAD"), head_before)

    def test_no_sync_in_worktree(self):
        local, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        wt_parent = tempfile.mkdtemp()
        wt = wt_parent + "/wt"
        git(local, "worktree", "add", "-q", "-b", "wt-branch", wt)
        self.addCleanup(shutil.rmtree, wt_parent, ignore_errors=True)
        self.addCleanup(subprocess.run, ["git", "-C", local, "worktree", "remove", "--force", wt],
                         capture_output=True)
        other = clone_dir(remote)
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        commit(other, "newer remote commit")
        git(other, "push", "-q", "origin", "main")
        head_before = git_capture(local, "rev-parse", "HEAD")
        self.ss.main(json.dumps({"cwd": wt, "source": "startup"}))
        self.assertEqual(git_capture(local, "rev-parse", "HEAD"), head_before)

    def test_no_sync_when_not_on_main(self):
        # Checked out on a non-main branch (not a worktree): sync must be skipped entirely, so
        # local `main` can't move even though the remote's main is ahead.
        seed, remote = make_repo_with_remote()
        self.addCleanup(shutil.rmtree, seed, ignore_errors=True)
        self.addCleanup(shutil.rmtree, remote, ignore_errors=True)
        local = clone_dir(remote)
        self.addCleanup(shutil.rmtree, local, ignore_errors=True)
        git(local, "checkout", "-q", "-b", "claude/x")
        other = clone_dir(remote)
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        commit(other, "newer remote commit")
        git(other, "push", "-q", "origin", "main")
        main_before = git_capture(local, "rev-parse", "main")
        msg = self.context(self.ss.main(json.dumps({"cwd": local, "source": "startup"})))
        self.assertEqual(git_capture(local, "rev-parse", "main"), main_before)
        self.assertIn("claude/x", msg)
        self.assertIn("main", msg)


def git_capture(cwd, *args):
    r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)
    return r.stdout.strip()


if __name__ == "__main__":
    unittest.main()
