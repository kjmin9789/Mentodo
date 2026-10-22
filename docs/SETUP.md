# 설치·개인 설정·화면 공유

## 준비

- [Python 공식 다운로드](https://www.python.org/downloads/)에서 3.10 이상을 설치합니다. Windows 설치 시 Python 실행 명령을 사용할 수 있게 설정합니다.
- [Git 공식 다운로드](https://git-scm.com/downloads)에서 Git을 설치합니다. Git이 없다면 GitHub 저장소의 **Code → Download ZIP**으로 내려받아 압축을 풀어도 됩니다.
- 비공개 저장소는 GitHub 계정에 저장소 접근 권한이 있어야 내려받을 수 있습니다. 이 앱에 GitHub 비밀번호나 토큰을 입력할 필요는 없습니다.

## 1. 내려받고 실행

macOS / Linux 터미널:

```sh
git clone https://github.com/kjmin9789/Mentodo.git
cd Mentodo
python3 --version
python3 server.py
```

Windows PowerShell:

```powershell
git clone https://github.com/kjmin9789/Mentodo.git
cd Mentodo
py -3 --version
py -3 server.py
```

### Git 없이 ZIP으로 받은 경우

GitHub 저장소의 **Code → Download ZIP**을 누르고 압축을 풉니다. 터미널에서 압축을 푼 폴더로 이동한 뒤 실행합니다. 아래 경로는 예시이므로 실제 다운로드 위치와 폴더 이름으로 바꿉니다.

macOS / Linux:

```sh
cd ~/Downloads/Mentodo-main
python3 server.py
```

Windows PowerShell:

```powershell
cd "$HOME/Downloads/Mentodo-main"
py -3 server.py
```

이후 개인 설정과 정기 수집 등록은 Git으로 받은 경우와 같습니다. ZIP 설치본의 코드를 업데이트할 때는 `local/`을 백업한 뒤 새 ZIP을 풀고, 백업한 `local/`을 새 폴더에 복사합니다. Codex 자동화에 등록한 프로젝트 경로가 달라졌다면 그 경로도 수정합니다.

Python 버전이 3.10 이상인지 확인합니다. `http://localhost:4317`을 열면 예시 데이터가 표시됩니다. 서버를 실행한 터미널은 켜둡니다.

기본 모드는 자신의 컴퓨터에서만 접속할 수 있습니다. 서버가 업무 원문을 직접 수집하거나 Discord 로그인을 대신하지 않습니다.

## 2. 개인 프로필 설정

macOS / Linux:

```sh
mkdir -p local
cp examples/profile.json local/profile.json
```

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force local
Copy-Item examples/profile.json local/profile.json
```

`local/profile.json`을 UTF-8로 저장합니다.

```json
{
  "name": "내 이름",
  "role": "내 역할",
  "avatar": ""
}
```

사진을 쓸 때는 PNG, JPG, JPEG 또는 WebP 파일을 `local/avatar.png`처럼 저장하고 `avatar`를 같은 경로로 바꿉니다. 예: `"avatar": "local/avatar.png"`. 사진을 지정하지 않으면 기본 이미지가 표시됩니다.

Discord 사진을 쓰고 싶다면 본인의 프로필 사진을 저장하거나, 로그인된 브라우저에서 Codex에게 프로필 사진을 가져와 `local/avatar.webp`에 저장하도록 요청할 수 있습니다. 이미지를 직접 저장하므로 앱을 열 때 Discord에 이미지 요청을 보내지 않습니다.

## 3. 내 프로젝트를 정하고 업무 데이터 추가

먼저 자신의 프로젝트 목록을 정합니다. 공통으로 정해진 목록이나 다른 사용자의 통합 설정은 없습니다. 예시 이름은 본인 업무에 맞게 교체합니다. 프로젝트가 다르면 별도 이름으로 두며, 아폴로와 종목필터 상품화도 각각 분리할 수 있습니다. 사용자가 직접 합치기로 정한 경우에만 같은 `project` 이름을 사용합니다.


[대화 수집 가이드](COLLECT.md)에 따라 `local/tasks.json`을 생성합니다. 직접 작성하려면 [필드 설명과 예시](DATA.md)를 사용합니다.

아직 수집할 데이터가 없으면 아래 내용으로 저장해 빈 목록부터 시작할 수 있습니다.

```json
[]
```

검사 후 브라우저를 새로고침합니다.

```sh
python3 server.py --check
```

Windows에서는 `py -3 server.py --check`를 사용합니다. 데이터가 잘못되면 필드나 형식을 확인하라는 오류가 표시됩니다. 파일을 고친 뒤 다시 검사합니다. `local/tasks.json`이 없을 때만 예시 데이터를 보여줍니다.

## 4. 정기 수집 설정

[정기 갱신 가이드](UPDATE.md)를 열어 본인의 계정, 서버·채널, 시작일, 시간대를 정하고 복사용 프롬프트로 Codex 자동화를 등록합니다. 권장 예시는 매일 한국 시간 09:00·12:00·17:00입니다. 설치만으로 예약이 등록되지는 않습니다.

처음 지정한 범위를 수집한 뒤에는 마지막 성공 지점 이후 새 대화와 기존 미완료 항목의 후속 내용을 확인합니다. 각자 자신의 로그인된 브라우저를 사용하며 다른 사용자의 계정·프로젝트·수집 기록은 가져오지 않습니다.

## 5. 종료·다시 실행·백업

- 종료: 터미널에서 `Ctrl+C`.
- 재실행: 프로젝트 폴더에서 `python3 server.py` 또는 `py -3 server.py`.
- 백업: `local/` 폴더 전체를 안전한 개인 위치에 복사합니다.
- 다른 컴퓨터로 이동: 소스 코드를 내려받고 본인의 `local/` 백업을 복사합니다. 다른 사람의 `local/` 폴더를 가져오면 그 사람의 데이터가 표시됩니다.
- 코드 업데이트: Git으로 받았다면 `git pull --ff-only`. 개인 파일은 Git에서 제외되어 유지됩니다. 원본 코드를 직접 고쳤다면 먼저 수정 내용을 보관합니다.

완료 상태는 브라우저가 아니라 `local/state.json`에 저장합니다. 업무 ID를 유지하면 새로 수집해도 수동 완료 상태가 유지됩니다. 같은 ID의 요청을 의도적으로 다시 열려면 화면에서 **할 일로 되돌리기**를 사용합니다. 파일을 통째로 삭제하면 수동 처리 기록이 사라집니다.

## macOS 자동 시작

컴퓨터에 로그인했을 때 서버를 자동으로 켜려면 [자동 시작 가이드](AUTOSTART.md)를 따릅니다. 실행 폴더 이동, 등록, 확인, 해제 방법을 안내합니다. 디스코드 정기 수집 예약은 별도로 유지합니다.

## 같은 네트워크에 공유

macOS / Linux:

```sh
python3 server.py --share
```

Windows:

```powershell
py -3 server.py --share
```

1. 터미널에 표시된 `네트워크 공유(조회 전용)` 주소를 전달합니다.
2. 상대방도 같은 와이파이 또는 사내망에서 접속합니다.
3. 공유가 끝나면 `Ctrl+C`로 종료합니다. 다음 실행에서 `--share`를 빼면 자기 컴퓨터에서만 열립니다.

다른 컴퓨터에서는 완료·되돌리기 버튼을 표시하지 않으며 서버도 변경 요청을 거부합니다. 상대방이 이 앱을 자기 업무용으로 쓰려면 본인 컴퓨터에 별도로 설치하고 본인 데이터를 설정해야 합니다.

공유 모드에는 로그인 기능이 없습니다. 업무 요약·대화 발췌·원문 링크·프로필 사진이 표시되므로 공유해도 되는 내용인지 확인합니다. 프로필·업무·상태의 원본 JSON 파일이나 서버 코드는 파일 주소로 내려받을 수 없도록 제한했습니다. 다만 화면을 그리는 업무 데이터는 접속자가 읽을 수 있습니다.

컴퓨터가 잠들거나 서버를 끄면 접속할 수 없습니다. 내부 IP가 바뀌면 서버를 다시 실행하고 새 주소를 전달합니다. 회사·게스트 네트워크의 기기 간 통신 차단이나 방화벽 때문에 접속이 안 될 수 있습니다. 이 저장소는 방화벽이나 라우터 설정을 자동 변경하지 않습니다.

## 문제 해결

| 상황 | 확인할 내용과 조치 |
| --- | --- |
| `python3` 또는 `py` 명령을 찾지 못함 | Python을 설치하고 터미널을 새로 엽니다. 설치 환경에 따라 `python --version`도 확인합니다. |
| 포트가 이미 사용 중 | 이전 서버를 종료하거나 `python3 server.py --port 4318`로 실행하고 `http://localhost:4318`을 엽니다. |
| 설정 파일 오류 | UTF-8 JSON인지 확인하고 `python3 server.py --check`를 실행합니다. 주석이나 마지막 항목 뒤 쉼표는 JSON에 넣지 않습니다. |
| 사진이 안 나옴 | 파일이 실제로 `local/avatar.png` 등에 있는지, profile.json의 확장자와 경로가 같은지 확인합니다. |
| 다른 브라우저와 상태가 다름 | 같은 컴퓨터의 같은 포트로 접속했는지 확인하고 해당 화면으로 돌아옵니다. 보이는 화면은 약 5초마다 상태를 확인합니다. |
| 새 대화가 안 보임 | 정기 수집을 별도로 등록했는지, 최근 실행이 성공했는지 확인합니다. `local/tasks.json`을 갱신한 뒤 화면으로 돌아오거나 1분 기다립니다. |
| 다른 사람에게 localhost 링크를 줬는데 안 열림 | `--share`로 실행하고 터미널의 내부 IP 주소를 전달합니다. |
| 저장 실패 | 디스크 여유 공간과 `local/` 폴더 쓰기 권한을 확인합니다. 실패 시 기존 파일을 지우거나 초기화하지 않습니다. |
