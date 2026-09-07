# 프로그램 구조 점검 및 복구 보고서 — v1.23.1

## 점검 범위

- FastAPI 애플리케이션과 API 라우터
- SQLite 저장소, 업로드 및 교재 내보내기 경로
- Ollama·LM Studio 및 하이브리드 RAG 연동
- 정적 HTML·CSS·JavaScript
- Windows 실행기, BAT, PyInstaller 산출물
- 전체 Python 컴파일 및 회귀 테스트

## 발견 및 수정

1. **HIGH — 소스와 실행 파일 버전 불일치**
   - 소스는 v1.23.0이지만 루트 EXE와 PyInstaller 설정은 v1.20.2였습니다.
   - v1.23.1 빌드 설정과 실행 파일로 갱신합니다.
2. **HIGH — EXE의 Python 탐색 경로 제한**
   - 기존 EXE는 `python.exe`만 호출해 `py.exe`만 등록된 Windows에서 실패할 수 있었습니다.
   - `py -3`, `python`, `python3` 순서의 안전한 탐색과 누락 오류 안내를 적용했습니다.
3. **MEDIUM — 하이브리드 상태 UI 상시 폴링**
   - 300ms 타이머가 화면 수명 동안 계속 실행됐습니다.
   - DOM 변경 및 모드 변경 이벤트로 갱신하도록 변경했습니다.
4. **LOW — 테스트 도구 경고**
   - Starlette TestClient의 httpx 호환 deprecation warning이 있습니다.
   - 현재 기능 실패는 아니므로 의존성 생태계가 안정된 뒤 별도 갱신합니다.

## 유지된 구조

- SQLite `data/studio.db`와 기존 사용자 데이터
- `127.0.0.1:8765` 로컬 바인딩 및 로그인 구조
- Ollama·LM Studio Provider와 선택형 웹 보강 구조
- Docker, PostgreSQL, MongoDB 및 Tailscale의 선택적·독립적 운영 구조

## 실행

- 일반 실행: `run_windows.bat`
- 호환 실행: `DTS_Book_12_Auotexe.bat`
- 진단: `run_windows_debug.bat`
- EXE 실행: `AI_Course_Studio_v1_23_1.exe`

## 검증 결과

- Python 전체 컴파일: PASS
- JavaScript 문법 검사: PASS
- Pytest 회귀 테스트: **40 passed, 1 deprecation warning**
- 런처 진단: PASS
- v1.23.1 EXE 빌드 및 `--diagnose`: PASS
- 실제 서버 헬스 체크: `ok=true`, `version=1.23.1`, `last_updated=2026-08-29`
- 정적 파일 캐시 방지 헤더: PASS
- EXE SHA-256: `90735C19AAEAC1F33EE01D894AF9A037FA643F7931DA88A073CD4336F0948496`

## 남은 제한 사항

- 외부 웹 검색은 공급자 API 키·인터넷 상태·대상 사이트 정책에 영향을 받으며, 실패 시 로컬 생성으로 안전하게 대체됩니다.
- Starlette TestClient 관련 deprecation warning 1건이 있으나 현재 실행 기능에는 영향을 주지 않습니다.
- EXE는 프로젝트용 실행기이므로 `launcher.py` 및 프로젝트 폴더와 함께 사용해야 합니다. 단독 이동용 완전 번들 애플리케이션은 아닙니다.

## 복구

- 수정 전 백업: `backups/full_check_pre_v1_23_1_20260829.zip`
- 기존 EXE는 삭제하지 않았습니다.
- 복구 시 서버를 종료한 뒤 백업 ZIP의 파일만 원래 위치로 복사합니다.
