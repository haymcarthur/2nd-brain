import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from test_structure import repo_root
from test_session_start import git, make_repo_with_remote, write_state


def load():
    path = repo_root() / ".claude/hooks/pre_compact.py"
    spec = importlib.util.spec_from_file_location("pre_compact", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def identify(d):
    git(d, "config", "user.name", "t")
    git(d, "config", "user.email", "t@t")


def write(d, rel, text="x"):
    p = pathlib.Path(d) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def remote_log(remote):
    r = subprocess.run(["git", "-C", remote, "log", "--format=%s", "main"], capture_output=True, text=True)
    return r.stdout


def committed_files(d):
    r = subprocess.run(["git", "-C", d, "show", "--name-only", "--format=", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.split()


class TestPreCompact(unittest.TestCase):
    def setUp(self):
        self.mod = load()

    def test_commits_and_pushes_on_main(self):
        local, remote = make_repo_with_remote()
        identify(local)
        write(local, "projects/launch/STATE.md")
        self.assertEqual(self.mod.backup(local), "saved")
        self.assertIn(self.mod.COMMIT_MESSAGE, remote_log(remote))

    def test_never_stages_private(self):
        local, _ = make_repo_with_remote()
        identify(local)
        write(local, "private/secret.md")
        write(local, "me/about-me.md")
        self.assertEqual(self.mod.backup(local), "saved")
        files = committed_files(local)
        self.assertIn("me/about-me.md", files)
        self.assertNotIn("private/secret.md", files)

    def test_clean_tree_makes_no_commit(self):
        local, remote = make_repo_with_remote()
        identify(local)
        self.assertEqual(self.mod.backup(local), "clean")
        self.assertNotIn(self.mod.COMMIT_MESSAGE, remote_log(remote))

    def test_not_a_repo_is_silent(self):
        self.assertEqual(self.mod.backup(tempfile.mkdtemp()), "skip")

    def test_skips_during_seeding(self):
        local, remote = make_repo_with_remote()
        identify(local)
        write_state(local, {"setup": {"done_steps": [1, 2, 3, 4], "waiting_on": ["seeding"]}})
        write(local, "projects/launch/STATE.md")
        self.assertEqual(self.mod.backup(local), "skip")
        self.assertNotIn(self.mod.COMMIT_MESSAGE, remote_log(remote))

    def test_branch_session_pushes_its_branch(self):
        local, remote = make_repo_with_remote()
        identify(local)
        git(local, "checkout", "-q", "-b", "phone-session")
        write(local, "projects/launch/STATE.md")
        self.assertEqual(self.mod.backup(local), "saved")
        r = subprocess.run(["git", "-C", remote, "log", "--format=%s", "phone-session"],
                           capture_output=True, text=True)
        self.assertIn(self.mod.COMMIT_MESSAGE, r.stdout)

    def test_main_never_raises_and_exits_zero(self):
        # Pin every fallback to a non-repo so this test can never commit to a real checkout.
        empty = tempfile.mkdtemp()
        env = {"CLAUDE_PROJECT_DIR": empty}
        for stdin in ["", "not json", json.dumps({"cwd": "/nonexistent/path"})]:
            with mock.patch("sys.stdin", io.StringIO(stdin)), mock.patch("sys.stdout", io.StringIO()), \
                    mock.patch.dict("os.environ", env), mock.patch("os.getcwd", return_value=empty):
                with self.assertRaises(SystemExit) as cm:
                    self.mod.main()
                self.assertEqual(cm.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
