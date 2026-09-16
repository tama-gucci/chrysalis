"""Context handoff checks using disposable synthetic repositories."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "Development/scripts/agent_context.py"
spec = importlib.util.spec_from_file_location("agent_context", SCRIPT)
context = importlib.util.module_from_spec(spec)
spec.loader.exec_module(context)


class AgentContextTests(unittest.TestCase):
    def test_hooks_never_inject_payload_or_transcripts(self):
        payload = {"invocationNum": 0, "transcriptPath": "PRIVATE-SECRET", "prompt": "UNTRUSTED"}
        for mode in ("antigravity", "codex"):
            result = json.dumps(context.hook(mode, payload))
            self.assertIn("Development/HANDOFF.md", result)
            self.assertNotIn("PRIVATE-SECRET", result)
            self.assertNotIn("UNTRUSTED", result)

    def test_antigravity_only_first_invocation(self):
        for payload in ({}, {"invocationNum": 1}, {"invocationNum": "0"}, None):
            self.assertEqual(context.hook("antigravity", payload), {})

    def test_malformed_hook_input_is_nonblocking(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "codex"], input="bad json", text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout), {})

    def test_subdirectory_resolves_git_root_and_reports_dirty_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            (root / "Development").mkdir()
            (root / "Development/AGENT-WORKFLOW.md").write_text("Synthetic workflow", encoding="utf-8")
            note = root / "Development/HANDOFF.md"
            note.write_text("Synthetic handoff", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=user@example.com", "commit", "-m", "Synthetic baseline"], check=True, capture_output=True)
            note.write_text("Synthetic updated handoff", encoding="utf-8")
            output = context.show(root / "Development")
            self.assertIn("HEAD: ", output)
            self.assertIn("Synthetic updated handoff", output)
            self.assertIn("M Development/HANDOFF.md", output)


if __name__ == "__main__":
    unittest.main()
