import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import TrackerServer
from update_runner import UpdateRunner


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runner = UpdateRunner(self.root, self.root)

    def tearDown(self):
        self.temp.cleanup()

    def configure(self, code):
        (self.root / 'collector.json').write_text(json.dumps({'command': [sys.executable, '-c', code]}))

    def test_success_requires_new_collection_checkpoint(self):
        marker = self.root / 'collection.lock'
        marker.touch()
        self.runner.state = {'status': 'running'}
        self.runner.run([sys.executable, '-c', "from pathlib import Path; Path('collection.json').write_text('{\"lastSuccessfulRunAt\":\"new\"}')"], marker)
        self.assertEqual(self.runner.snapshot()['status'], 'done')
        self.assertFalse(marker.exists())

    def test_zero_exit_without_collection_is_failure(self):
        marker = self.root / 'collection.lock'
        marker.touch()
        self.runner.run([sys.executable, '-c', 'pass'], marker)
        self.assertEqual(self.runner.snapshot()['status'], 'error')
        self.assertFalse(marker.exists())

    def test_browser_connection_failure_shows_cause_without_raw_log(self):
        marker = self.root / 'collection.lock'
        marker.touch()
        self.runner.run([sys.executable, '-c', "print('Connection invalid\\nFailed to start ego lite.\\nprivate-log-content')"], marker)
        state = self.runner.snapshot()
        self.assertEqual(state['status'], 'error')
        self.assertIn('이고라이트', state['error'])
        self.assertNotIn('private-log-content', state['error'])
        self.assertFalse(marker.exists())

    def test_running_and_scheduled_lock_prevent_duplicate(self):
        self.configure('pass')
        self.runner.state = {'status': 'running'}
        self.assertEqual(self.runner.start()['status'], 'running')
        self.runner.state = {'status': 'idle'}
        (self.root / 'collection.lock').touch()
        with self.assertRaises(ValueError):
            self.runner.start()

    def test_timeout_releases_lock(self):
        marker = self.root / 'collection.lock'
        marker.touch()
        with patch('update_runner.subprocess.run', side_effect=subprocess.TimeoutExpired('collector', 1800)):
            self.runner.run(['collector'], marker)
        self.assertEqual(self.runner.snapshot()['status'], 'error')
        self.assertFalse(marker.exists())

    def test_update_endpoint_rejects_remote_origin_and_browser_commands(self):
        server = TrackerServer(('127.0.0.1', 0), self.root / 'state.json', data_dir=self.root)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}/api/update'
        try:
            for body, origin, expected in [({}, 'https://outside.example', 403), ({'command': ['anything']}, None, 409), ({}, None, 503)]:
                headers = {'Content-Type': 'application/json'}
                if origin:
                    headers['Origin'] = origin
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(url, data=json.dumps(body).encode(), headers=headers))
                self.assertEqual(caught.exception.code, expected)
                caught.exception.close()
            with patch.object(server.updater, 'start', return_value={'status': 'running'}) as start:
                with urlopen(Request(url, data=b'{}', headers={'Content-Type': 'application/json'})) as response:
                    self.assertEqual(response.status, 202)
                    self.assertEqual(json.load(response)['status'], 'running')
                start.assert_called_once()
        finally:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
