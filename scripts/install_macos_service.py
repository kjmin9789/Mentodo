"""Install an opt-in login service for a Mentodo checkout outside protected folders."""
import argparse
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LABEL = 'com.mentodo.server'


def service_config(root, python, home, path, share=False, port=4317):
    support = home / 'Library/Application Support/Mentodo'
    command = [str(python), '-u', str(root / 'server.py'), '--port', str(port)]
    if share:
        command.append('--share')
    return {
        'Label': LABEL,
        'ProgramArguments': command,
        'WorkingDirectory': str(root),
        'RunAtLoad': True,
        'KeepAlive': True,
        'ThrottleInterval': 10,
        'StandardOutPath': str(support / 'server.log'),
        'StandardErrorPath': str(support / 'server-error.log'),
        'EnvironmentVariables': {'PATH': path, 'PYTHONUNBUFFERED': '1'},
    }


def main():
    parser = argparse.ArgumentParser(description='Mentodo macOS 로그인 시 자동 시작 설정')
    parser.add_argument('--share', action='store_true', help='같은 네트워크에 조회용으로 공유')
    parser.add_argument('--port', type=int, default=4317)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('macOS에서만 사용할 수 있습니다.')
    if not 1 <= args.port <= 65535:
        parser.error('포트는 1~65535 사이여야 합니다.')
    home = Path.home()
    if any(ROOT.is_relative_to(home / folder) for folder in ('Documents', 'Desktop', 'Downloads')):
        parser.error('Mentodo 폴더를 ~/Applications/Mentodo 등 문서·데스크탑·다운로드 밖으로 옮긴 뒤 실행해 주세요.')
    domain = f'gui/{os.getuid()}'
    installed = subprocess.run(['launchctl', 'print', f'{domain}/{LABEL}'], capture_output=True).returncode == 0
    if not installed:
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', args.port)) == 0:
                parser.error('같은 포트의 서버가 실행 중입니다. 기존 서버를 종료하거나 --port를 지정해 주세요.')
    agent = home / f'Library/LaunchAgents/{LABEL}.plist'
    agent.parent.mkdir(parents=True, exist_ok=True)
    (home / 'Library/Application Support/Mentodo').mkdir(parents=True, exist_ok=True)
    if installed:
        subprocess.run(['launchctl', 'bootout', f'{domain}/{LABEL}'], check=True)
    config = service_config(ROOT, sys.executable, home, os.environ.get('PATH', '/usr/bin:/bin'), args.share, args.port)
    agent.write_bytes(plistlib.dumps(config))
    agent.chmod(0o600)
    subprocess.run(['launchctl', 'bootstrap', domain, str(agent)], check=True)
    print(f'로그인 시 자동 시작 및 종료 후 재시작을 등록했습니다: http://localhost:{args.port}')
    print(f'실행 상태: launchctl print {domain}/{LABEL}')


if __name__ == '__main__':
    main()
