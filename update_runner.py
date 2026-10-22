"""Run a locally configured collector without accepting commands from the browser."""
import json
import os
from pathlib import Path
import subprocess
import threading
from datetime import datetime, timezone


class UpdateRunner:
    def __init__(self, root, data_dir):
        self.root = Path(root)
        self.data_dir = Path(data_dir)
        self.lock = threading.Lock()
        self.state = {'status': 'idle'}

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def start(self):
        with self.lock:
            if self.state['status'] == 'running':
                return dict(self.state)
            config = json.loads((self.data_dir / 'collector.json').read_text(encoding='utf-8'))
            command = config.get('command')
            if not isinstance(command, list) or not command or any(not isinstance(arg, str) or not arg for arg in command):
                raise ValueError('collector.json의 command 배열을 확인해 주세요.')
            self.data_dir.mkdir(parents=True, exist_ok=True)
            marker = self.data_dir / 'collection.lock'
            try:
                fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                raise ValueError('다른 수집이 진행 중입니다. 완료 후 다시 시도해 주세요.')
            with os.fdopen(fd, 'w') as output:
                output.write(str(os.getpid()))
            self.state = {'status': 'running', 'startedAt': datetime.now(timezone.utc).isoformat()}
            threading.Thread(target=self.run, args=(command, marker), daemon=True).start()
            return dict(self.state)

    def run(self, command, marker):
        try:
            checkpoint = self.data_dir / 'collection.json'
            before = json.loads(checkpoint.read_text()).get('lastSuccessfulRunAt') if checkpoint.exists() else None
            with (self.data_dir / 'collector.log').open('w', encoding='utf-8') as log:
                result = subprocess.run(command, cwd=self.root, stdout=log, stderr=subprocess.STDOUT, timeout=1800, check=False)
            after = json.loads(checkpoint.read_text()).get('lastSuccessfulRunAt') if checkpoint.exists() else None
            if result.returncode != 0 or not after or after == before:
                raise ValueError('수집을 완료하지 못했습니다. 로그인과 수집 로그를 확인해 주세요.')
            state = {'status': 'done', 'finishedAt': datetime.now(timezone.utc).isoformat()}
        except (OSError, ValueError, subprocess.SubprocessError):
            state = {'status': 'error', 'error': '수집을 완료하지 못했습니다. 로그인과 collector.log를 확인해 주세요.'}
        finally:
            marker.unlink(missing_ok=True)
        with self.lock:
            self.state = {**self.state, **state}
