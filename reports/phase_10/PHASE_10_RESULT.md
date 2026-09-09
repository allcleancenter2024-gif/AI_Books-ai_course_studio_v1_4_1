# Phase 10 결과 — Lesson Unit · Publisher Handoff

## 상태

**PASS WITH CONDITIONS**

## 적용 내용

- 저장된 `lesson_units`를 주차 단위로 독립 조회하는 `GET /api/books/{book_id}/lessons/{week}` 엔드포인트를 추가했습니다.
- `edition=student|teacher|combined`에 따라 학생용·강사용 콘텐츠를 분리해 반환합니다.
- 프로필, 품질 검사 결과, 승인 상태, 출처 ID를 함께 반환하는 `publisher_handoff` 메타데이터를 추가했습니다.
- 잘못된 edition, 존재하지 않는 교재·주차에 대해 명확한 400/404 응답을 제공합니다.
- 기존 Markdown/PPTX/PDF/HWPX export와 기존 품질·승인 API는 변경하지 않았습니다.

## 검증

- 교육 데이터 모델 및 회귀 테스트 통과
- 주차 독립 저장·복원 테스트 추가 및 통과
- JavaScript 구문 검사 통과
- `git diff --check` 공백 오류 없음

## 조건 및 잔여 확인

- 실제 Publisher 프로그램이 이 API를 직접 호출하는 통합 테스트는 아직 없습니다.
- 승인되지 않은 차시는 `requires_instructor_approval=true`로 표시되며, 외부 Publisher도 이 상태를 반드시 차단해야 합니다.
- 기존 테스트 실행 시 pytest 캐시 ACL 및 Starlette/httpx deprecation 경고가 남아 있습니다.

## 다음 권장 단계

Phase 11에서 최종 운영 readiness를 점검합니다. Tailscale Host-only 원칙, 외부 서비스 독립성, 공개·비공개 경계, 롤백 가능성을 종합 보고하고 실제 네트워크 설정은 변경하지 않습니다.
