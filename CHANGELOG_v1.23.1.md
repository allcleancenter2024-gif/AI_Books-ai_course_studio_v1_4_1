# AI Course Studio v1.23.1 [2026-08-29]

## 변경 내용

- 현재 소스와 Windows 실행 파일의 버전을 v1.23.1로 일치시켰습니다.
- EXE 실행기가 `py.exe -3`, `python.exe`, `python3.exe` 순서로 Python을 안전하게 찾도록 수정했습니다.
- EXE 옆에 `launcher.py`가 없을 때 원인을 명확히 표시하고 종료 코드 21을 반환합니다.
- 하이브리드 RAG 작업 상황 UI의 300ms 상시 폴링을 제거하고 DOM 변경 이벤트 방식으로 전환했습니다.
- `run_windows.bat`, `DTS_Book_12_Auotexe.bat`, 안내 문서의 표시 버전을 갱신했습니다.

## 호환성

- 기본 SQLite 데이터와 업로드·내보내기 파일은 변경하지 않습니다.
- Docker와 Tailscale은 여전히 선택 기능이며 Studio 실행 조건이 아닙니다.
- 서버는 기존과 동일하게 `127.0.0.1:8765`를 사용합니다.
