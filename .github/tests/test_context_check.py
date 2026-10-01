import importlib.util
import json
import pathlib
import shutil
import tempfile
import unittest

from test_structure import repo_root


def load():
    path = repo_root() / ".claude/hooks/context_check.py"
    spec = importlib.util.spec_from_file_location("context_check", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_transcript(dirpath, entries):
    p = pathlib.Path(dirpath) / "t.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return str(p)


def assistant(tokens, model="claude-sonnet-5"):
    return {"message": {"model": model, "usage": {
        "input_tokens": tokens, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}


class TestContextCheck(unittest.TestCase):
    def setUp(self):
        self.cc = load()
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_window_for_known_and_unknown(self):
        self.assertEqual(self.cc.window_for("claude-opus-5-5[1m]"), 1_000_000)
        self.assertEqual(self.cc.window_for("some-future-model"), 200_000)
        self.assertEqual(self.cc.window_for(None), 200_000)

    def test_current_tokens_uses_last_real_entry(self):
        t = write_transcript(self.tmp, [assistant(1000), assistant(5000),
                                        {"message": {"model": "<synthetic>", "usage": {"input_tokens": 9}}}])
        self.assertEqual(self.cc.current_tokens(t), (5000, "claude-sonnet-5"))

    def test_decide(self):
        self.assertEqual(self.cc.decide(69_000, 100_000, True), (False, True))
        self.assertEqual(self.cc.decide(70_000, 100_000, True), (True, False))
        self.assertEqual(self.cc.decide(80_000, 100_000, False), (False, False))
        self.assertEqual(self.cc.decide(30_000, 100_000, False), (False, True))  # re-arm after compaction

    def test_nudges_once_then_rearms_after_drop(self):
        t = write_transcript(self.tmp, [assistant(150_000, "unknown-model")])  # 75% of 200k
        stdin = json.dumps({"session_id": "s1", "transcript_path": t})
        first = self.cc.main(stdin, self.tmp)
        self.assertIn("save", json.loads(first)["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.cc.main(stdin, self.tmp), "")
        t2 = write_transcript(self.tmp, [assistant(20_000, "unknown-model")])
        self.cc.main(json.dumps({"session_id": "s1", "transcript_path": t2}), self.tmp)
        t3 = write_transcript(self.tmp, [assistant(150_000, "unknown-model")])
        self.assertNotEqual(self.cc.main(json.dumps({"session_id": "s1", "transcript_path": t3}), self.tmp), "")

    def test_missing_transcript_silent(self):
        stdin = json.dumps({"session_id": "s2", "transcript_path": "/nope/missing.jsonl"})
        self.assertEqual(self.cc.main(stdin, self.tmp), "")

    def test_synthetic_only_silent(self):
        t = write_transcript(self.tmp, [{"message": {"model": "<synthetic>", "usage": {"input_tokens": 999_999}}}])
        self.assertEqual(self.cc.main(json.dumps({"session_id": "s3", "transcript_path": t}), self.tmp), "")

    def test_garbage_stdin_silent(self):
        self.assertEqual(self.cc.main("not json", self.tmp), "")

    def test_tail_read_large_transcript(self):
        # Test that tail reader efficiently handles large transcripts
        # Write 5000 filler lines followed by the real assistant entry
        filler = [{"dummy": i} for i in range(5000)]
        entries = filler + [assistant(42_000, "claude-opus-5")]
        t = write_transcript(self.tmp, entries)
        # Should find the correct token count despite many preceding lines
        self.assertEqual(self.cc.current_tokens(t), (42_000, "claude-opus-5"))

    def test_tail_read_with_trailing_garbage(self):
        # Test that tail reader skips non-JSON lines after the last real entry
        entries = [assistant(33_000, "claude-fable-5"), "not json\n", "garbage line"]
        p = pathlib.Path(self.tmp) / "t.jsonl"
        p.write_text(json.dumps(entries[0]) + "\n" + entries[1] + entries[2])
        # Should still find the real entry, skipping the garbage
        self.assertEqual(self.cc.current_tokens(str(p)), (33_000, "claude-fable-5"))


if __name__ == "__main__":
    unittest.main()
