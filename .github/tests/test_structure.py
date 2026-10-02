import json
import pathlib
import re
import unittest


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "INDEX.md",
    "README.md",
    "me/about-me.md",
    "me/voice.md",
    "me/methods.md",
    "me/processes/README.md",
    "me/add-ons/README.md",
    "reference/people.md",
    "reference/glossary.md",
    "reference/links.md",
    "reference/company/README.md",
    "projects/general/STATE.md",
    "projects/general/notes/README.md",
    "decisions/README.md",
    "decisions/_template.md",
    "private/README.md",
    ".claude/skills/save/SKILL.md",
    ".claude/skills/catch-up/SKILL.md",
    ".claude/skills/get-set-up/SKILL.md",
    ".claude/skills/start/SKILL.md",
    ".claude/state.json",
    "BRIEFING.md",
]

SKILLS = {
    "save": ["save what we learned", "wrap up"],
    "catch-up": ["catch me up", "what's new"],
    "get-set-up": ["set me up"],
    "start": ["let's work on", "catch me up on"],
}
CONFIRM_PHRASES = ["ask the user to confirm", "wait for approval", "wait for the user to confirm", "needs your call"]
SOURCE_KEYS = ["email", "calendar", "transcripts", "teams", "slack", "drive", "jira", "confluence",
               "github", "figma", "lucid", "monday", "usertesting"]


class TestStructure(unittest.TestCase):
    def test_required_files_exist(self):
        missing = [p for p in REQUIRED_FILES if not (repo_root() / p).is_file()]
        self.assertEqual(missing, [], f"missing: {missing}")

    def test_claude_md_under_200_lines(self):
        lines = (repo_root() / "CLAUDE.md").read_text().splitlines()
        self.assertLess(len(lines), 200)

    def test_index_lists_every_top_level_content_path(self):
        index = (repo_root() / "INDEX.md").read_text()
        for name in ["me/", "reference/", "projects/", "decisions/", "private/", "BRIEFING.md"]:
            self.assertIn(f"`{name}", index, f"INDEX.md does not mention {name}")

    def test_readme_has_no_worktree_or_empty_folder_guidance(self):
        readme = (repo_root() / "README.md").read_text().lower()
        self.assertNotIn("worktree", readme)
        self.assertNotIn("empty folder", readme)
        self.assertIn("no folder", readme)

    def test_setup_clones_into_home_folder(self):
        skill = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("~/<repo-name>", skill)
        self.assertNotIn(".git .", skill)

    def test_readme_mentions_60_days(self):
        readme = (repo_root() / "README.md").read_text()
        self.assertIn("60 days", readme)

    def test_readme_prompt_lets_user_name_it(self):
        readme = (repo_root() / "README.md").read_text()
        self.assertIn("and call it my-2nd-brain", readme)


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.settings = json.loads((repo_root() / ".claude/settings.json").read_text())

    def test_hooks_point_at_existing_scripts(self):
        hooks = self.settings["hooks"]
        self.assertIn("SessionStart", hooks)
        self.assertIn("PostToolUse", hooks)
        self.assertIn("PreCompact", hooks)
        for event in hooks.values():
            for group in event:
                for h in group["hooks"]:
                    script = h["command"].split("/.claude/hooks/")[1].split('"')[0]
                    self.assertTrue((repo_root() / ".claude/hooks" / script).is_file(), script)

    def test_hooks_never_error_when_project_dir_is_elsewhere(self):
        # A setup session keeps its temp folder as the project dir after moving into the brain folder.
        for event in self.settings["hooks"].values():
            for group in event:
                for h in group["hooks"]:
                    self.assertIn('[ -f "$f" ] || f="$PWD/.claude/hooks/', h["command"])
                    self.assertTrue(h["command"].endswith("|| true"))

    def test_git_and_edits_preapproved(self):
        allow = self.settings["permissions"]["allow"]
        for needed in ["Bash(git commit:*)", "Edit", "Write"]:
            self.assertIn(needed, allow)

    def test_broad_git_and_gh_repo_not_allowlisted(self):
        # These were replaced by a specific allow list (finding I3): anything not on it prompts the user.
        allow = self.settings["permissions"]["allow"]
        self.assertNotIn("Bash(git:*)", allow)
        self.assertNotIn("Bash(gh repo:*)", allow)

    def test_gh_repo_edit_prompts_rather_than_denied(self):
        # get-set-up step 2 needs `gh repo edit --visibility private` to make a public copy private.
        # `deny` blocks outright with no prompt, so a visibility change must be neither allowed
        # (it's a real, if rare, mutation) nor denied (that would make the step impossible) --
        # left off both lists, it prompts the user instead.
        allow = self.settings["permissions"]["allow"]
        deny = self.settings["permissions"]["deny"]
        self.assertNotIn("Bash(gh repo edit:*)", allow)
        self.assertNotIn("Bash(gh repo edit:*)", deny)

    def test_destructive_commands_denied(self):
        deny = self.settings["permissions"]["deny"]
        for destructive in [
            "Bash(git push --force:*)",
            "Bash(git push -f:*)",
            "Bash(git push --force-with-lease:*)",
            "Bash(git reset --hard:*)",
            "Bash(git clean:*)",
            "Bash(git branch -D:*)",
            "Bash(git checkout -- :*)",
            "Bash(gh repo delete:*)",
            "Bash(gh repo rename:*)",
            "Bash(gh repo archive:*)",
            "Bash(git remote add:*)",
            "Bash(git remote set-url:*)",
            "Bash(git push --delete:*)",
            "Bash(git push origin --delete:*)",
            "Bash(git push origin --force:*)",
            "Bash(git push origin -f:*)",
            "Bash(git stash clear:*)",
        ]:
            self.assertIn(destructive, deny)


class TestSkills(unittest.TestCase):
    def check_skill(self, name):
        path = repo_root() / f".claude/skills/{name}/SKILL.md"
        text = path.read_text()
        self.assertTrue(text.startswith("---\n"), "frontmatter missing")
        front = text.split("---\n")[1]
        self.assertIn(f"name: {name}", front)
        self.assertIn("description:", front)
        for phrase in SKILLS[name]:
            self.assertIn(phrase, front.lower(), f"trigger phrase '{phrase}' not in description")
        for bad in CONFIRM_PHRASES:
            self.assertNotIn(bad, text.lower(), f"{name} contains a confirmation step: {bad}")

    def test_save(self):
        self.check_skill("save")

    def test_catch_up(self):
        self.check_skill("catch-up")

    def test_start(self):
        self.check_skill("start")

    def test_get_set_up(self):
        self.check_skill("get-set-up")
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        for must in ["--private", "--template", "backfill", "schedule", "How it works"]:
            self.assertIn(must, text)

    def test_setup_asks_one_question_only(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertNotIn("Interview", text)
        self.assertNotIn("one at a time", text)
        self.assertNotIn("Ask the user no questions", text)
        self.assertIn("Ask the user exactly one thing", text)
        self.assertNotIn("multiSelect", text)
        self.assertIn("don't** want", text)
        self.assertIn('"off"', text)
        # The question comes before any connector check, and only kept sources get checked.
        self.assertLess(text.index("Ask the user exactly one thing, and ask it first"),
                        text.index("check only the sources they kept"))
        self.assertIn("I'll hook it in", text)
        self.assertIn("Walk them through connecting the missing ones", text)

    def test_setup_explains_every_step(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("Explain as you go", text)
        self.assertGreaterEqual(text.count("**Explain"), 8)
        for must in ["two synced places", "Catch-up only **reads**",
                     "every weekday at 7am, even when your computer is off", "marked **guessed**"]:
            self.assertIn(must, text)

    def test_projects_are_efforts_not_umbrellas(self):
        catch = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertIn("**Project size:**", catch)
        self.assertIn("When in doubt, split", catch)
        setup = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn('"Project size" rule', setup)

    def test_todos_checked_and_dated_from_source(self):
        claude = (repo_root() / "CLAUDE.md").read_text()
        self.assertIn("**Before adding any to-do, from anywhere", claude)
        self.assertIn("merged, closed or done", claude)
        self.assertIn("**Date it when it arose**", claude)
        for skill in ["catch-up", "save"]:
            text = (repo_root() / f".claude/skills/{skill}/SKILL.md").read_text()
            self.assertIn('"Before adding any to-do" checks', text, skill)

    def test_pulls_are_paged_and_watermarks_honest(self):
        catch = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        for must in ["one week at a time, oldest week first", "**Follow every page**",
                     "assigned, reported and watched", "read **completely**",
                     "end of the last week that was read\nin full"]:
            self.assertIn(must, catch)
        setup = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("**Skip `github`.**", setup)
        self.assertIn("**GitHub, from this main session:**", setup)

    def test_routine_attaches_only_verified_connectors(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        for url in ["https://microsoft365.mcp.claude.com/mcp", "https://mcp.slack.com/mcp",
                    "https://mcp.atlassian.com/v1/mcp", "https://mcp.figma.com/mcp",
                    "https://mcp.lucid.app/mcp", "https://ai.usertesting.com/mcp",
                    "https://mcp.monday.com/mcp"]:
            self.assertIn(url, text)
        self.assertIn("**desktop-only**", text)
        catch = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertIn("**Desktop-only sources**", catch)

    def test_setup_verifies_routine_connectors(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("most capable model", text)
        self.assertIn("Read the routine back", text)

    def test_setup_sources_and_window(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        for must in ["60 days", "background", "cloud routine"]:
            self.assertIn(must, text)
        for key in SOURCE_KEYS:
            self.assertIn(f"`{key}`", text)

    def test_catch_up_has_no_missing_nag(self):
        text = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertNotIn("last_missing_note", text)
        self.assertNotIn("Missing connectors", text)
        for key in SOURCE_KEYS:
            self.assertIn(f"`{key}`", text)

    def test_catch_up_reports_skipped_sources(self):
        text = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertIn("`skipped`", text)
        self.assertNotIn("don't mention the gap", text)

    def test_catch_up_writes_briefing_and_recommends_start(self):
        text = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertIn("BRIEFING.md", text)
        self.assertIn("Start here", text)
        self.assertIn("last_catch_up", text)

    def test_catch_up_never_skips_by_choice_and_reports_what_ran(self):
        text = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertIn("**Never skip a live source by choice.**", text)
        self.assertIn("an add-on is never optional", text)
        self.assertIn("- **Ran:**", text)
        self.assertIn("**Times come from the clock.**", text)

    def test_catch_up_leaves_named_project_to_start(self):
        front = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text().split("---\n")[1].lower()
        self.assertNotIn("names a project", front)
        self.assertNotIn("catch me up on", front)

    def test_start_catches_up_when_stale(self):
        text = (repo_root() / ".claude/skills/start/SKILL.md").read_text()
        self.assertIn("last_catch_up", text)
        self.assertIn("3 days", text)
        self.assertIn("catch-up", text)

    def test_off_sources_never_auto_upgrade(self):
        text = (repo_root() / ".claude/skills/catch-up/SKILL.md").read_text()
        self.assertIn('"off"', text)

    def test_claude_md_explains_adding_a_source(self):
        text = (repo_root() / "CLAUDE.md").read_text()
        self.assertIn("## Adding a source", text)
        self.assertIn("sources_added", text)

    def test_save_stages_briefing(self):
        text = (repo_root() / ".claude/skills/save/SKILL.md").read_text()
        self.assertIn("BRIEFING.md", text)

    def test_setup_uses_chosen_name(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("call it", text)
        self.assertIn("my-2nd-brain", text)

    def test_setup_removes_itself(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("`## Contributing`", text)
        self.assertIn("git rm -r .claude/skills/get-set-up", text)
        self.assertIn("Setup complete: removed the setup files", text)

    def test_no_inbox_by_default_downloads_instead(self):
        self.assertFalse((repo_root() / "inbox").exists())
        claude = (repo_root() / "CLAUDE.md").read_text()
        self.assertIn("**Downloads**", claude)
        self.assertIn("**move** it, never copy it", claude)
        save = (repo_root() / ".claude/skills/save/SKILL.md").read_text()
        self.assertNotIn("git add -A projects/ inbox/", save)

    def test_setup_explains_concept_not_tips(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        section = text[text.index("## 6. How it works"):text.index("## 7. Tour")]
        self.assertNotIn("Tips:", section)
        self.assertIn("never have to hunt down", section)

    def test_setup_has_no_drive_inbox_step(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertNotIn("2nd Brain Inbox", text)

    def test_setup_seeding_skips_inbox(self):
        text = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        self.assertIn("skips `inbox/` processing entirely", text)

    def test_setup_how_it_works_matches_readme(self):
        def normalize_text(text):
            """Collapse all whitespace runs to single spaces."""
            return re.sub(r'\s+', ' ', text).strip()

        def extract_bullets(section_text):
            """Parse bullets: start with '- ' and include indented continuation lines."""
            bullets = []
            lines = section_text.split("\n")
            current_bullet = None
            for line in lines:
                if line.startswith("- "):
                    if current_bullet is not None:
                        bullets.append(current_bullet)
                    current_bullet = line
                elif current_bullet is not None and line.startswith("  "):
                    # Continuation line (indented)
                    current_bullet += " " + line.strip()
            if current_bullet is not None:
                bullets.append(current_bullet)
            return bullets

        readme = (repo_root() / "README.md").read_text()
        skill = (repo_root() / ".claude/skills/get-set-up/SKILL.md").read_text()
        skill_normalized = normalize_text(skill)

        # Extract "How it works" section
        how_it_works_start = readme.find("## How it works")
        how_it_works_end = readme.find("\n\nThe idea is", how_it_works_start)
        how_it_works_section = readme[how_it_works_start:how_it_works_end].strip()
        how_it_works_bullets = extract_bullets(how_it_works_section)

        # Assert at least 5 bullets in each section (so test can't pass vacuously)
        self.assertGreaterEqual(len(how_it_works_bullets), 5,
            f"Expected at least 5 'How it works' bullets, got {len(how_it_works_bullets)}")

        # Assert each bullet appears in skill (normalized)
        for bullet in how_it_works_bullets:
            normalized_bullet = normalize_text(bullet)
            self.assertIn(normalized_bullet, skill_normalized,
                f"README 'How it works' bullet not found in skill:\n{bullet}")


    def test_add_ons_run_inside_skills(self):
        readme = (repo_root() / "me/add-ons/README.md").read_text()
        for must in ["runs-in:", "status: active", "retired", "ends:"]:
            self.assertIn(must, readme)
        for skill in ["catch-up", "save"]:
            text = (repo_root() / f".claude/skills/{skill}/SKILL.md").read_text()
            self.assertIn("me/add-ons/", text, skill)
            self.assertIn("runs-in", text, skill)
        self.assertIn("`me/add-ons/", (repo_root() / "INDEX.md").read_text())
        self.assertIn("me/add-ons/", (repo_root() / "CLAUDE.md").read_text())

    def test_multi_session_guards(self):
        save = (repo_root() / ".claude/skills/save/SKILL.md").read_text()
        self.assertIn("index.lock", save)
        self.assertIn("re-read", save.lower())
        self.assertIn("never discard or revert", save)
        self.assertIn("Other sessions may be open", (repo_root() / "CLAUDE.md").read_text())

    def test_close_on_evidence_consolidated(self):
        claude = (repo_root() / "CLAUDE.md").read_text()
        self.assertIn("**Close on evidence, from anywhere.**", claude)
        self.assertIn("superseded", claude)
        for skill in ["catch-up", "save"]:
            text = (repo_root() / f".claude/skills/{skill}/SKILL.md").read_text()
            self.assertIn('"Close on evidence, from anywhere"', text, skill)

    def test_state_json_schema(self):
        state = json.loads((repo_root() / ".claude/state.json").read_text())
        self.assertEqual(set(state), {"last_pulled", "connectors", "setup", "drive_inbox",
                                       "drive_inbox_filed", "catch_up_schedule", "last_catch_up",
                                       "skipped", "sources_added"})
        self.assertEqual(set(state["setup"]), {"done_steps", "waiting_on"})
        self.assertEqual(state["setup"]["done_steps"], [])
        self.assertEqual(state["setup"]["waiting_on"], [])
        self.assertIsNone(state["drive_inbox"])
        self.assertEqual(state["drive_inbox_filed"], [])
        self.assertIsNone(state["catch_up_schedule"])
        self.assertIsNone(state["last_catch_up"])
        self.assertEqual(state["skipped"], {})
        self.assertEqual(state["sources_added"], {})


if __name__ == "__main__":
    unittest.main()
