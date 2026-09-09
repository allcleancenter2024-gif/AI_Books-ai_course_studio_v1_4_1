# Phase 09 결과 — Learner Profile · Device-aware UI

## 상태

**PASS WITH CONDITIONS**

## 적용 내용

- 학습자 프로필에 주요 대상, 실제 디지털 경험, 사용 기기를 명시적으로 입력하도록 UI를 보완했습니다.
- 대상 선택은 기존 1주/전체 교재 생성 대상 선택과 동기화됩니다. 기존 API 요청 형식과 백엔드 계약은 변경하지 않았습니다.
- 선택 기기별 조작 안내 미리보기와 기기 미선택 시 `pc_web` 기본 경로 fallback을 추가했습니다.
- 기기 입력을 `fieldset`/`legend`로 묶고 상태 영역에 `aria-live`를 적용했습니다.
- 44px 터치 목표, 320px 수준의 좁은 화면에서 단일 열 전환, 기존 `prefers-reduced-motion` 규칙과 호환되는 CSS를 추가했습니다.
- 기존 색상·간격·카드 언어를 유지해 전체 화면 재설계 없이 프로필 영역만 확장했습니다.

## 검증

- `.venv\Scripts\python.exe -m pytest -q tests\test_learner_ui.py tests\test_quality_gate.py tests\test_education_data_model.py` → **6 passed**
- 전체 회귀: `.venv\Scripts\python.exe -m pytest -q` → **72 passed**
- `node --check static\js\app.js` → **PASS**
- `git diff --check` → 공백 오류 없음 (기존 CRLF 경고만 확인)
- 기본 Python에서 pytest/compileall을 시도했으나 시스템 Python의 pytest 미설치 및 기존 `__pycache__` ACL로 캐시 생성 경고가 발생했습니다. 프로젝트 `.venv` 검증은 통과했습니다.

## 조건 및 잔여 확인

- 실제 브라우저별 시각 회귀, 키보드 순회, 스크린리더 검증은 자동화하지 않았습니다.
- 프로필 값은 현재 화면 세션에서 생성 옵션과 동기화되며 영구 프로필 저장소는 아직 도입하지 않았습니다.
- 운영 환경에서는 Publisher가 동일한 학습자/기기 메타데이터를 표시할지 별도 확인이 필요합니다.

## 다음 권장 단계

Phase 10에서 실제 생성 결과의 주차별 독립 로딩, 학생용/강사용 분리, Publisher handoff 메타데이터를 점검합니다. Tailscale·Docker·DB·방화벽 구성은 계속 변경하지 않습니다.
