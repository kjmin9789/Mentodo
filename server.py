"""Run the local tracker: python3 server.py"""
import argparse
import ipaddress
import json
from update_runner import UpdateRunner
import re
import os
import socket
import subprocess
from pathlib import Path
import tempfile
import threading
from datetime import date, datetime, timedelta, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
def validate_tasks(tasks):
    if not isinstance(tasks, list):
        raise ValueError('업무 파일은 JSON 배열이어야 합니다.')
    ids = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError('각 업무는 JSON 객체여야 합니다.')
        required = ('id', 'title', 'category', 'kind', 'type', 'project', 'initial', 'date', 'time', 'channel', 'sender', 'author', 'quote', 'note', 'caption', 'url')
        for field in required:
            if not isinstance(task.get(field), str) or len(task[field]) > 20000:
                raise ValueError(f'업무의 {field} 필드를 확인해 주세요.')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', task['id']) or task['id'] in ids:
            raise ValueError('업무 ID는 중복되지 않는 영문·숫자·밑줄·하이픈이어야 합니다.')
        ids.add(task['id'])
        if task['category'] not in ('mine', 'requested', 'question', 'shared') or task['type'] not in ('design', 'planning', 'review', 'marketing') or task['kind'] not in ('review', 'question', 'reference') or task['initial'] not in ('todo', 'done', 'reference'):
            raise ValueError('업무 분류·종류·상태를 확인해 주세요.')
        if (task['category'] == 'shared') != (task['initial'] == 'reference'):
            raise ValueError('공유 항목은 category=shared, initial=reference로 지정해 주세요.')
        if not task['title'].strip() or not task['project'].strip():
            raise ValueError('제목과 프로젝트를 입력해 주세요.')
        date.fromisoformat(task['date'])
        if not re.fullmatch(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]', task['time']):
            raise ValueError('시간은 HH:MM 형식이어야 합니다.')
        links = [task['url']]
        if 'pr' in task:
            links.append(task['pr'])
        evidence = task.get('evidence', [])
        if not isinstance(evidence, list):
            raise ValueError('후속 근거는 배열이어야 합니다.')
        for entry in evidence:
            if not isinstance(entry, dict) or not isinstance(entry.get('label'), str):
                raise ValueError('후속 근거에 label과 url을 입력해 주세요.')
            links.append(entry.get('url'))
        for link in links:
            if not isinstance(link, str) or urlsplit(link).scheme not in ('http', 'https') or not urlsplit(link).hostname:
                raise ValueError('원문과 후속 링크는 http 또는 https 주소여야 합니다.')
    return tasks


class TrackerServer(ThreadingHTTPServer):
    def __init__(self, address, state_file=None, lan_hosts=(), data_dir=None):
        self.data_dir = Path(data_dir) if data_dir is not None else ROOT / 'local'
        self.state_file = Path(state_file) if state_file is not None else self.data_dir / 'state.json'
        self.state_lock = threading.Lock()
        self.updater = UpdateRunner(ROOT, self.data_dir)
        self.local_hosts = {'127.0.0.1', *lan_hosts}
        self.allowed_hosts = {'localhost', *self.local_hosts}
        super().__init__(address, partial(Handler, directory=str(ROOT)))

    def read_tasks(self):
        own = self.data_dir / 'tasks.json'
        source = own if own.exists() else ROOT / 'examples/tasks.json'
        content = source.read_text(encoding='utf-8')
        if not own.exists():
            content = content.replace('{{today}}', date.today().isoformat()).replace('{{yesterday}}', (date.today() - timedelta(days=1)).isoformat())
        return validate_tasks(json.loads(content))

    def read_profile(self):
        source = self.data_dir / 'profile.json'
        if not source.exists():
            source = ROOT / 'examples/profile.json'
        profile = json.loads(source.read_text(encoding='utf-8'))
        if not isinstance(profile, dict) or not isinstance(profile.get('name'), str) or not profile['name'].strip():
            raise ValueError('프로필 name을 입력해 주세요.')
        for field in ('role', 'avatar'):
            if not isinstance(profile.get(field, ''), str):
                raise ValueError(f'프로필 {field}를 확인해 주세요.')
        avatar = profile.get('avatar', '')
        if avatar and not re.fullmatch(r'local/avatar\.(png|jpg|jpeg|webp)', avatar):
            raise ValueError('프로필 사진은 local/avatar.png 또는 jpg, jpeg, webp 파일을 지정해 주세요.')
        return {'name': profile['name'], 'role': profile.get('role', ''), 'avatar': avatar or 'assets/avatar-default.svg', 'isExample': not (self.data_dir / 'tasks.json').exists()}

    def read_state(self):
        if not self.state_file.exists():
            return {'statuses': {}, 'revision': 0}
        state = json.loads(self.state_file.read_text())
        if not isinstance(state, dict) or not isinstance(state.get('statuses'), dict):
            raise ValueError('Invalid state file')
        if any(value not in ('todo', 'done') for value in state['statuses'].values()):
            raise ValueError('Invalid saved status')
        if type(state.get('revision')) is not int:
            raise ValueError('Invalid revision')
        return state

    def update_status(self, task_id, status):
        with self.state_lock:
            state = self.read_state()
            if state['statuses'].get(task_id) == status:
                return state
            state['statuses'][task_id] = status
            state['revision'] += 1
            state['updatedAt'] = datetime.now(timezone.utc).isoformat()
            self.state_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.state_file.parent, delete=False) as output:
                    temp_path = Path(output.name)
                    json.dump(state, output, ensure_ascii=False, indent=2)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temp_path, self.state_file)
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink()
            return state


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        super().end_headers()

    def json_response(self, status, value):
        data = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def local_request(self):
        origins = {f'http://{host}:{self.server.server_port}' for host in self.server.allowed_hosts}
        if f'http://{self.headers.get("Host", "")}' not in origins:
            self.json_response(403, {'error': '허용하지 않는 서버 주소입니다.'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in origins:
            self.json_response(403, {'error': '허용하지 않는 연결입니다.'})
            return False
        return True

    def can_edit(self):
        return self.client_address[0] in self.server.local_hosts

    def send_head(self):
        path = unquote(urlsplit(self.path).path)
        if re.fullmatch(r'/local/avatar\.(png|jpg|jpeg|webp)', path):
            target = self.server.data_dir / Path(path).name
            if not target.is_file():
                self.send_error(404)
                return None
            self.send_response(200)
            self.send_header('Content-Type', self.guess_type(str(target)))
            self.send_header('Content-Length', str(target.stat().st_size))
            self.end_headers()
            return target.open('rb')
        target = (ROOT / path.lstrip('/')).resolve()
        assets = (ROOT / 'assets').resolve()
        if path not in ('/', '/index.html', '/app.js', '/style.css') and not (target.is_relative_to(assets) and target.is_file()):
            self.send_error(404)
            return None
        return super().send_head()

    def do_HEAD(self):
        if self.local_request():
            super().do_HEAD()

    def do_GET(self):
        if not self.local_request():
            return
        if urlsplit(self.path).path == '/api/update':
            self.json_response(200, self.server.updater.snapshot() if self.can_edit() else {'status': 'idle'})
            return
        path = urlsplit(self.path).path
        if path in ('/tasks.json', '/api/profile'):
            try:
                self.json_response(200, self.server.read_tasks() if path == '/tasks.json' else self.server.read_profile())
            except (OSError, ValueError, TypeError) as error:
                self.json_response(503, {'error': f'개인 설정 파일을 확인해 주세요: {error}'})
        elif path == '/api/state':
            try:
                with self.server.state_lock:
                    state = self.server.read_state()
                self.json_response(200, {**state, 'canEdit': self.can_edit()})
            except (OSError, ValueError, TypeError):
                self.json_response(503, {'error': '저장 상태를 읽지 못했습니다. 기존 파일을 확인해 주세요.'})
        else:
            super().do_GET()

    def do_POST(self):
        if not self.local_request():
            return
        if not self.can_edit():
            self.json_response(403, {'error': '공유 화면에서는 조회만 가능합니다.'})
            return
        if urlsplit(self.path).path == '/api/update':
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                self.json_response(415, {'error': 'JSON 요청만 지원합니다.'})
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 32 or json.loads(self.rfile.read(length)) != {}:
                    raise ValueError('잘못된 요청입니다.')
                self.json_response(202, self.server.updater.start())
            except FileNotFoundError:
                self.json_response(503, {'error': '수집 실행 설정이 없습니다. 정기 갱신 가이드의 수동 업데이트 설정을 확인해 주세요.'})
            except (OSError, ValueError, TypeError) as error:
                self.json_response(409, {'error': str(error)})
            return
        if urlsplit(self.path).path != '/api/state':
            self.json_response(404, {'error': '잘못된 요청 경로입니다.'})
            return
        if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
            self.json_response(415, {'error': 'JSON 요청만 지원합니다.'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('Invalid length')
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or set(body) != {'id', 'status'}:
                raise ValueError('Invalid request')
            task_id, status = body['id'], body['status']
            if not isinstance(task_id, str) or not isinstance(status, str):
                raise ValueError('Invalid values')
            tasks = self.server.read_tasks()
            if status not in ('todo', 'done') or not any(task['id'] == task_id and task['initial'] != 'reference' for task in tasks):
                raise ValueError('Invalid task or status')
        except (ValueError, TypeError):
            self.json_response(400, {'error': '유효한 항목과 상태를 지정해 주세요.'})
            return
        except OSError:
            self.json_response(503, {'error': '업무 데이터를 읽지 못했습니다.'})
            return
        try:
            self.json_response(200, self.server.update_status(task_id, status))
        except (OSError, ValueError, TypeError):
            self.json_response(503, {'error': '저장하지 못했습니다. 기존 상태는 유지됩니다.'})


def lan_addresses():
    hosts = set()
    if os.name != 'nt' and Path('/usr/sbin/ipconfig').exists():
        for _, interface in socket.if_nameindex():
            if interface.startswith('en'):
                result = subprocess.run(['/usr/sbin/ipconfig', 'getifaddr', interface], capture_output=True, text=True)
                if result.returncode == 0:
                    hosts.add(result.stdout.strip())
    try:
        hosts.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    # UDP connect는 패킷을 보내지 않고 기본 경로의 로컬 주소를 확인합니다.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.connect(('192.0.2.1', 9))
            hosts.add(connection.getsockname()[0])
    except OSError:
        pass
    return {host for host in hosts if host and not ipaddress.ip_address(host).is_loopback and not ipaddress.ip_address(host).is_unspecified}


def main():
    parser = argparse.ArgumentParser(description='Mentodo — 개인 업무 트래커')
    parser.add_argument('--share', action='store_true', help='같은 네트워크에 조회용으로 공유')
    parser.add_argument('--port', type=int, default=4317, help='서버 포트 (기본 4317)')
    parser.add_argument('--check', action='store_true', help='개인 데이터 형식만 검사하고 종료')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('포트는 1~65535 사이여야 합니다.')
    hosts = lan_addresses() if args.share else set()
    try:
        server = TrackerServer(('0.0.0.0' if args.share else '127.0.0.1', 0 if args.check else args.port), lan_hosts=hosts)
        tasks = server.read_tasks()
        profile = server.read_profile()
        server.read_state()
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f'실행하지 못했습니다: {error}\n')
    if args.check:
        print(f'검사 완료: {len(tasks)}개 항목, ' + ('예시 데이터' if profile['isExample'] else '개인 데이터'))
        server.server_close()
        return
    print(f'내 컴퓨터: http://localhost:{args.port}', flush=True)
    for host in sorted(hosts):
        print(f'네트워크 공유(조회 전용): http://{host}:{args.port}', flush=True)
    if profile['isExample']:
        print('예시 데이터로 실행 중입니다. docs/SETUP.md에 따라 개인 데이터를 설정하세요.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
