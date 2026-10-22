import concurrent.futures
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from server import TrackerServer, validate_tasks


class StateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'state.json'
        self.server = TrackerServer(('127.0.0.1', 0), self.path, data_dir=self.temp.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def request(self, body=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        request = Request(self.base + '/api/state', data=json.dumps(body).encode() if body is not None else None, headers=headers)
        try:
            with urlopen(request) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            with error:
                return error.code, json.load(error)

    def test_independent_clients_and_restart(self):
        self.assertEqual(self.request({'id': 'example-review', 'status': 'done'})[0], 200)
        self.assertEqual(self.request()[1]['statuses']['example-review'], 'done')
        other = TrackerServer(('127.0.0.1', 0), self.path, data_dir=self.temp.name)
        try:
            self.assertEqual(other.read_state()['statuses']['example-review'], 'done')
        finally:
            other.server_close()
        self.assertEqual(self.request({'id': 'example-review', 'status': 'todo'})[1]['statuses']['example-review'], 'todo')

    def test_concurrent_edits_keep_both_tasks(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.request, [{'id': 'example-review', 'status': 'done'}, {'id': 'example-request', 'status': 'done'}]))
        self.assertTrue(all(status == 200 for status, _ in results))
        self.assertEqual(self.request()[1]['statuses'], {'example-review': 'done', 'example-request': 'done'})

    def test_reject_invalid_and_cross_origin(self):
        for value in [{'id': 'missing', 'status': 'done'}, {'id': 'example-review', 'status': 'deleted'}, {'id': 'example-share', 'status': 'done'}, {'id': ['example-review'], 'status': 'done'}]:
            self.assertEqual(self.request(value)[0], 400)
        self.assertEqual(self.request({'id': 'example-review', 'status': 'done'}, 'https://example.com')[0], 403)
        self.assertEqual(self.request()[1]['statuses'], {})

    def test_network_view_is_read_only(self):
        self.server.local_hosts.clear()
        self.assertFalse(self.request()[1]['canEdit'])
        self.assertEqual(self.request({'id': 'example-review', 'status': 'done'})[0], 403)
        self.assertFalse(self.path.exists())

    def test_only_site_assets_are_shared(self):
        for path in ['/server.py', '/authored-page1.json', '/README.md', '/assets/../tasks.json/../server.py']:
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base + path)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
        with urlopen(self.base + '/assets/montage-icons.svg') as response:
            self.assertEqual(response.status, 200)

    def test_personal_files_replace_examples(self):
        self.assertEqual(len(self.server.read_tasks()), 4)
        self.assertTrue(self.server.read_profile()['isExample'])
        (Path(self.temp.name) / 'tasks.json').write_text('[]', encoding='utf-8')
        (Path(self.temp.name) / 'profile.json').write_text(json.dumps({'name': '테스트 사용자', 'role': '개인 업무', 'avatar': ''}), encoding='utf-8')
        self.assertEqual(self.server.read_tasks(), [])
        self.assertFalse(self.server.read_profile()['isExample'])
        self.assertEqual(self.server.read_profile()['name'], '테스트 사용자')

    def test_projects_stay_separate(self):
        rows = self.server.read_tasks()[:2]
        rows[0]['project'] = '아폴로'
        rows[1]['project'] = '종목필터 상품화'
        (Path(self.temp.name) / 'tasks.json').write_text(json.dumps(rows), encoding='utf-8')
        self.assertEqual({task['project'] for task in self.server.read_tasks()}, {'아폴로', '종목필터 상품화'})

    def test_reject_unsafe_or_duplicate_data(self):
        rows = self.server.read_tasks()
        invalid = dict(rows[0], id='bad" onclick="oops')
        with self.assertRaises(ValueError):
            validate_tasks([invalid])
        with self.assertRaises(ValueError):
            validate_tasks([rows[0], rows[0]])
        with self.assertRaises(ValueError):
            validate_tasks([dict(rows[0], url='javascript:alert(1)')])
        with self.assertRaises(ValueError):
            validate_tasks([dict(rows[0], category='shared')])

    def test_corrupt_file_is_not_overwritten(self):
        self.path.write_text('broken')
        self.assertEqual(self.request()[0], 503)
        self.assertEqual(self.request({'id': 'example-review', 'status': 'done'})[0], 503)
        self.assertEqual(self.path.read_text(), 'broken')


if __name__ == '__main__':
    unittest.main()
