# macOS에서 로그인 시 서버 자동 시작

macOS 로그인 시 Mentodo 서버를 시작하고, 실행 중 종료되면 다시 켜도록 등록할 수 있습니다. 선택 기능이며 설치만으로 등록되지는 않습니다. Windows·Linux의 자동 시작 설정은 이 가이드에 포함하지 않습니다.

전원 종료·로그아웃·잠자기 동안에는 접속할 수 없습니다. 수집 예약은 서버 자동 시작과 별도로 [정기 갱신 설정](UPDATE.md)을 따릅니다.

## 1. 실행할 폴더 준비

문서·데스크탑·다운로드 폴더는 macOS가 백그라운드 접근을 제한할 수 있습니다. Mentodo 폴더 전체를 `~/Applications/Mentodo`처럼 해당 폴더 밖으로 옮깁니다. 기존 `local/`도 함께 옮겨야 개인 데이터와 완료 상태가 유지됩니다. 같은 이름의 대상 폴더가 이미 있으면 덮어쓰지 말고 먼저 확인합니다.

Finder에서 이동해도 됩니다. 다음은 다운로드 ZIP을 푼 뒤의 예시입니다. 실제 원본 폴더 이름이 다르면 수정합니다.

```sh
mkdir -p ~/Applications
mv ~/Downloads/Mentodo-main ~/Applications/Mentodo
cd ~/Applications/Mentodo
python3 server.py --check
```

기존 터미널에서 서버를 실행 중이라면 `Ctrl+C`로 종료합니다. 경로를 바꾸었으므로 Codex 수집 예약의 프로젝트 경로와 `local/collector.json`의 작업 경로도 새 위치로 수정합니다. 수동 수집 설정을 아직 하지 않았다면 이동한 폴더에서 설정합니다.

## 2. 자동 시작 등록

자기 컴퓨터에서만 이용할 때:

```sh
python3 scripts/install_macos_service.py
```

같은 네트워크에 조회용으로 공유하려면 대신 다음 명령을 사용합니다.

```sh
python3 scripts/install_macos_service.py --share
```

포트를 바꾸려면 `--port 4318`처럼 지정합니다. 공유 모드의 접근 범위는 [공유 가이드](SETUP.md#같은-네트워크에-공유)를 확인합니다. 등록하면 즉시 서버를 시작하고 다음 로그인에도 자동 시작합니다. 별도 터미널 창을 켜둘 필요는 없습니다. 이후 이 프로젝트 폴더를 삭제하거나 옮기면 시작할 수 없으므로 경로 변경 후 다시 등록합니다.

## 3. 실행 확인과 로그

```sh
launchctl print gui/$(id -u)/com.mentodo.server
```

출력의 `state = running`을 확인하고 [localhost:4317](http://localhost:4317/)을 엽니다. 포트를 바꿨으면 해당 포트로 접속합니다. 같은 네트워크의 사람에게는 `localhost` 대신 서버 로그에 표시된 내부 IP 주소를 전달합니다.

- 일반 로그: `~/Library/Application Support/Mentodo/server.log`
- 오류 로그: `~/Library/Application Support/Mentodo/server-error.log`
- 등록 파일: `~/Library/LaunchAgents/com.mentodo.server.plist`

Python 경로가 업그레이드 등으로 바뀌면 새 Python으로 등록 명령을 다시 실행합니다. 코드 갱신 후 서버를 다시 시작하려면 다음 명령을 사용합니다. 수집이 진행 중이라면 먼저 완료될 때까지 기다립니다.

```sh
launchctl kickstart -k gui/$(id -u)/com.mentodo.server
```

## 자동 시작 해제

```sh
launchctl bootout gui/$(id -u)/com.mentodo.server
rm ~/Library/LaunchAgents/com.mentodo.server.plist
```

서버가 종료되고 다음 로그인부터 자동 시작하지 않습니다. `local/`의 개인 데이터는 유지됩니다. 다시 사용할 때 등록 명령을 실행하거나 `python3 server.py`로 직접 시작합니다.
