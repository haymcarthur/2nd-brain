import importlib.util
import unittest

from test_structure import repo_root


def load():
    path = repo_root() / ".github/scripts/branch_cleanup.py"
    spec = importlib.util.spec_from_file_location("branch_cleanup", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestBranchCleanup(unittest.TestCase):
    def setUp(self):
        self.bc = load()

    def test_never_deletes_default(self):
        self.assertFalse(self.bc.should_delete("main", "main", True, True))

    def test_merged_by_ancestry_deleted(self):
        self.assertTrue(self.bc.should_delete("claude/a", "main", True, False))

    def test_merged_pr_at_tip_deleted(self):
        # has_merged_pr is true only when a merged PR's head sha matches the branch's current tip
        self.assertTrue(self.bc.should_delete("claude/b", "main", False, True))

    def test_unmerged_closed_pr_kept(self):
        # a closed-but-unmerged PR reports has_merged_pr=False
        self.assertFalse(self.bc.should_delete("claude/c", "main", False, False))

    def test_merged_pr_matches_tip(self):
        prs = [{"merged_at": "2026-01-01T00:00:00Z", "head": {"sha": "abc123"}}]
        self.assertTrue(self.bc.merged_pr_matches_tip(prs, "abc123"))

    def test_merged_pr_different_head_sha(self):
        prs = [{"merged_at": "2026-01-01T00:00:00Z", "head": {"sha": "old-sha"}}]
        self.assertFalse(self.bc.merged_pr_matches_tip(prs, "abc123"))

    def test_unmerged_pr_matching_sha(self):
        prs = [{"merged_at": None, "head": {"sha": "abc123"}}]
        self.assertFalse(self.bc.merged_pr_matches_tip(prs, "abc123"))

    def test_merged_pr_matches_tip_empty(self):
        self.assertFalse(self.bc.merged_pr_matches_tip([], "abc123"))

    def test_plan_filters(self):
        branches = [
            {"name": "main", "is_ancestor": True, "has_merged_pr": False},
            {"name": "claude/done", "is_ancestor": True, "has_merged_pr": False},
            {"name": "claude/wip", "is_ancestor": False, "has_merged_pr": False},
        ]
        self.assertEqual(self.bc.plan(branches, "main"), ["claude/done"])

    def test_parse_slurped_empty(self):
        self.assertEqual(self.bc.parse_slurped(""), [])

    def test_parse_slurped_invalid_json(self):
        self.assertEqual(self.bc.parse_slurped("not json"), [])

    def test_parse_slurped_two_page(self):
        # Two pages as a slurped list of lists
        slurped = '[[{"name": "a"}, {"name": "b"}], [{"name": "c"}]]'
        expected = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        self.assertEqual(self.bc.parse_slurped(slurped), expected)

    def test_workflow_fork_pr_protection(self):
        # Read workflow file and verify fork PR protection is present
        workflow_path = repo_root() / ".github/workflows/branch-cleanup.yml"
        workflow_text = workflow_path.read_text()
        self.assertIn("head.repo.full_name == github.repository", workflow_text)


if __name__ == "__main__":
    unittest.main()
