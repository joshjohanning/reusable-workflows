import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest


ACTION = Path(__file__).resolve().parents[1] / "gh-aw-upgrade/action.yml"
OLD_SHA = "1" * 40
NEW_SHA = "2" * 40


def step_script(name):
    text = ACTION.read_text()
    match = re.search(
        rf"^    - name: {re.escape(name)}\n(.*?)(?=^    - name: |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    run = match.group(1).split("      run: |\n", 1)[1]
    return textwrap.dedent(run)


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / "output"
        self.env = dict(
            os.environ,
            GITHUB_OUTPUT=str(self.output),
            GITHUB_RUN_ID="123",
            GITHUB_RUN_ATTEMPT="2",
            VERSION="v1.2.2",
            NEW_SHA=NEW_SHA,
            BASE="main",
        )
        gsed = shutil.which("gsed")
        if gsed:
            tools = self.root / "tools"
            tools.mkdir()
            (tools / "sed").symlink_to(gsed)
            self.env["PATH"] = f"{tools}:{self.env['PATH']}"
        self.bash = (
            "/opt/homebrew/bin/bash"
            if Path("/opt/homebrew/bin/bash").exists()
            else shutil.which("bash")
        )

    def run_step(self, name, prelude="", **env):
        return subprocess.run(
            [self.bash, "-c", prelude + "\n" + step_script(name)],
            cwd=self.root,
            env={**self.env, **env},
            capture_output=True,
            text=True,
        )

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True, stderr=subprocess.STDOUT
        ).strip()

    def test_version_resolution_normalizes_versions_and_peels_tags(self):
        prelude = """
gh() { printf 'v1.2.2\\n'; }
git() {
  printf '%s\\trefs/tags/v1.2.2\\n' "$OLD_SHA"
  printf '%s\\trefs/tags/v1.2.2^{}\\n' "$NEW_SHA"
}
"""
        for requested in ("latest", "1.2.2", "v1.2.2"):
            with self.subTest(requested=requested):
                self.output.write_text("")
                result = self.run_step(
                    "Resolve target gh-aw version",
                    prelude,
                    REQUESTED=requested,
                    OLD_SHA=OLD_SHA,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"setup-cli-sha={NEW_SHA}", self.output.read_text())
                self.assertIn("branch=gh-aw-upgrade/v1.2.2-123-2", self.output.read_text())
        for requested in ("v1.2.2\nneeded=false", "v1.2.2-preview", "missing"):
            result = self.run_step(
                "Resolve target gh-aw version", prelude, REQUESTED=requested
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("::error::", result.stdout)

    def test_pin_sync_preserves_other_actions_and_lock_files(self):
        workflows = self.root / ".github/workflows"
        workflows.mkdir(parents=True)
        path = workflows / "validate.yml"
        path.write_text(
            textwrap.dedent(
                f"""\
                jobs:
                  validate:
                    steps:
                      - uses: github/gh-aw-actions/setup-cli@{OLD_SHA} # v1.0.1
                        with:
                          version: 'v1.0.1' # compiler
                      - name: Compile
                        run: gh aw compile --action-tag "{OLD_SHA}"
                      - uses: other/action@{OLD_SHA}
                        with:
                          version: v1.0.1
                """
            )
        )
        lock = workflows / "agent.lock.yml"
        original_lock = f"uses: github/gh-aw-actions/setup-cli@{OLD_SHA}\n"
        lock.write_text(original_lock)
        result = self.run_step("Sync remaining gh-aw setup-cli pins", "git() { :; }")
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = path.read_text()
        self.assertIn(f"setup-cli@{NEW_SHA} # v1.2.2", updated)
        self.assertIn("version: v1.2.2 # compiler", updated)
        self.assertIn(f'--action-tag "{NEW_SHA}"', updated)
        self.assertIn(f"other/action@{OLD_SHA}", updated)
        self.assertIn("version: v1.0.1", updated)
        self.assertEqual(lock.read_text(), original_lock)
        result = self.run_step("Sync remaining gh-aw setup-cli pins", "git() { :; }")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(path.read_text(), updated)

    def test_upgrade_guard_keeps_current_locks_eligible_for_pin_updates(self):
        workflows = self.root / ".github/workflows"
        workflows.mkdir(parents=True)
        (workflows / "agent.lock.yml").write_text(
            '# gh-aw-metadata: {"compiler_version":"v1.2.2"}\n'
        )
        result = self.run_step("Check whether an upgrade is needed", "gh() { :; }")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("needed=true", self.output.read_text())
        self.output.write_text("")
        result = self.run_step(
            "Check whether an upgrade is needed",
            "gh() { printf 'https://github.com/example/repo/pull/1\\n'; }",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("needed=false", self.output.read_text())
        (workflows / "agent.lock.yml").unlink()
        result = self.run_step("Check whether an upgrade is needed", "gh() { :; }")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("::error::No compiled", result.stdout)

    def test_pr_creation_can_retry_without_overwriting_a_closed_pr_branch(self):
        remote = self.root / "remote.git"
        self.git("init", "--bare", str(remote))
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("remote", "add", "origin", str(remote))
        workflows = self.root / ".github/workflows"
        workflows.mkdir(parents=True)
        path = workflows / "agent.md"
        path.write_text("baseline\n")
        self.git("add", str(path))
        self.git("commit", "-m", "baseline")
        self.git("push", "origin", "main")
        body = self.root / "body"
        prelude = """
gh() {
  if [ "$1" = pr ] && [ "$2" = create ]; then
    cat > "$BODY_FILE"
    printf 'https://github.com/example/repo/pull/1\\n'
  else
    return 1
  fi
}
"""
        first_commit = None
        for attempt in ("1", "2"):
            self.git("switch", "main")
            path.write_text("upgraded\n")
            branch = f"gh-aw-upgrade/v1.2.2-123-{attempt}"
            result = self.run_step(
                "Open pull request",
                prelude,
                BRANCH=branch,
                GIT_NAME="Test",
                GIT_EMAIL="test@example.invalid",
                BODY_FILE=str(body),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Review the diff", body.read_text())
            self.assertIn("\n\n", body.read_text())
            self.assertNotIn("Co-authored-by", self.git("log", "-1", "--format=%B"))
            if first_commit is None:
                first_commit = self.git("rev-parse", branch)
        self.assertEqual(self.git("rev-parse", "gh-aw-upgrade/v1.2.2-123-1"), first_commit)


if __name__ == "__main__":
    unittest.main()
