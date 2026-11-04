import io
import contextlib
import json
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import dual_write
import write_log
import write_handoff


class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class DualWriteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'CO_MEMORY_VAULT_ROOT': self.temp.name, 'AGENTMEMORY_SECRET': 'test', 'AGENTMEMORY_URL': 'http://localhost:1'}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_payload_scope(self):
        log = write_log.build_payload('codex', 'test-project', 'a', 'info', '', '', 'now')
        handoff = write_handoff.build_payload('codex', 'hermes', 'test-project', 'a', '', 'None', '', 'now')
        for item in (log, handoff):
            self.assertEqual((item['project'], item['agentId']), ('test-project', 'codex'))

    def test_configuration_has_no_personal_defaults(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(dual_write.Path, 'home', return_value=Path(self.temp.name)):
            with self.assertRaises(ValueError):
                dual_write.vault_root()
            with self.assertRaises(ValueError):
                dual_write.agentmemory_url()

    def test_workspace_directory_cannot_escape_vault(self):
        with patch.dict(os.environ, {'CO_MEMORY_AGENT_COMEMORY_DIR': '../outside'}):
            with self.assertRaises(ValueError):
                dual_write.agent_comemory_root()

    def test_log_and_handoff_use_configured_vault(self):
        root = Path(self.temp.name) / 'Agent_Comemory'
        index = root / '00_Index' / 'README.md'
        index.parent.mkdir(parents=True)
        index.write_text('# Index\n')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(write_log.main(['--actor', 'example.agent', '--project', 'demo', '--action', 'completed', '--skip-agentmemory']), 0)
            self.assertEqual(write_handoff.main(['--from', 'example.agent', '--to', 'next.agent', '--project', 'demo', '--summary', 'ready', '--skip-agentmemory']), 0)
        self.assertEqual(len(list((root / '03_Logs').rglob('*.md'))), 1)
        self.assertEqual(len(list((root / '05_Handoffs').rglob('*.md'))), 1)

    def test_legacy_payload_and_response_validation(self):
        captured = []
        def send(request, timeout):
            captured.append(json.loads(request.data))
            return Response(b'{"success":true,"memory":{"id":"mem-test"}}')
        with patch('urllib.request.urlopen', side_effect=send):
            self.assertEqual(dual_write.post_remember({'content':'a','metadata':{'project':'test-project','actor_id':'codex'}}), (True, 'ok'))
        self.assertEqual((captured[0]['project'], captured[0]['agentId']), ('test-project', 'codex'))
        with patch('urllib.request.urlopen', return_value=Response(b'{"success":false}')):
            self.assertEqual(dual_write.post_remember({'content':'a'})[0], False)

    def test_concurrent_append_during_flush_is_preserved(self):
        path = dual_write.outbox_path()
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'payload': {'content':'first'}})+'\n')
        started, release = threading.Event(), threading.Event()
        def send(payload):
            if payload['content'] == 'first':
                started.set()
                self.assertTrue(release.wait(5))
                return True, 'ok'
            return False, 'offline'
        with patch.object(dual_write, 'post_remember', side_effect=send):
            flush = threading.Thread(target=dual_write.flush_outbox)
            flush.start()
            self.assertTrue(started.wait(5))
            writer = threading.Thread(target=dual_write.deliver_or_queue, args=({'content':'second'}, 'log'))
            writer.start()
            release.set()
            flush.join(5)
            writer.join(5)
        self.assertFalse(flush.is_alive() or writer.is_alive())
        self.assertEqual(json.loads(path.read_text())['payload']['content'], 'second')


if __name__ == '__main__': unittest.main()
