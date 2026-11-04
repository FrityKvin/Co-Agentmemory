import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import onboard


class OnboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.vault = self.root / "Vault"
        index = self.vault / "Agent_Comemory/00_Index/README.md"
        index.parent.mkdir(parents=True)
        index.write_text("# Test\n", encoding="utf-8")
        self.profile = self.root / "profiles" / "actor.json"
        self.env = patch.dict(os.environ, {"CO_MEMORY_PROFILE": str(self.profile)}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_onboard(self, *options):
        args = ["--runtime", "hermes", "--bot", "sara", "--environment", "test-machine",
                "--vault", str(self.vault), "--agentmemory-url", "https://memory.example.invalid",
                *options]
        with patch.object(sys.stdin, "isatty", return_value=False), patch.object(onboard, "check_agentmemory", return_value="reachable"), contextlib.redirect_stdout(io.StringIO()):
            return onboard.main(args)

    def test_creates_distinct_actor_profile_without_secret(self):
        self.assertEqual(self.run_onboard(), 0)
        data = json.loads(self.profile.read_text(encoding="utf-8"))
        self.assertEqual(data["actor_id"], "hermes.sara")
        self.assertEqual(data["runtime_id"], "hermes")
        self.assertEqual(data["vault_root"], str(self.vault.resolve()))
        self.assertNotIn("AGENTMEMORY_SECRET", data)
        self.assertEqual(self.profile.stat().st_mode & 0o777, 0o600)

    def test_existing_profile_needs_explicit_reconfigure(self):
        self.profile.parent.mkdir(parents=True)
        self.profile.write_text('{"unchanged": true}', encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_onboard()
        self.assertEqual(self.profile.read_text(encoding="utf-8"), '{"unchanged": true}')

    def test_missing_vault_does_not_create_profile(self):
        self.vault.rename(self.root / "moved")
        with self.assertRaises(SystemExit):
            self.run_onboard()
        self.assertFalse(self.profile.exists())

    def test_single_identity_runtime_has_no_bot_suffix(self):
        with patch.object(sys.stdin, "isatty", return_value=False), patch.object(onboard, "check_agentmemory", return_value="reachable"), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(onboard.main(["--runtime", "codex", "--environment", "test-machine", "--vault", str(self.vault), "--agentmemory-url", "https://memory.example.invalid"]), 0)
        self.assertEqual(json.loads(self.profile.read_text(encoding="utf-8"))["actor_id"], "codex")


if __name__ == "__main__":
    unittest.main()
