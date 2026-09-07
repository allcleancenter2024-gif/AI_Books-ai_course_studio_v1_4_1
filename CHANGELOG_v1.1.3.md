# v1.1.3

- 로컬 LLM의 malformed JSON 때문에 서버가 500으로 종료되는 구조 제거
- JSON mode 힌트 + 미지원 서버 자동 fallback
- 다층 JSON 복구 파이프라인 추가
- 복구 실패 시 단계별 deterministic fallback 추가
- 원시 malformed output 로그 저장
- 전체 교재 생성도 3단계 resilient pipeline으로 통일
- UI에 복구 경고 표시
- health/version 1.1.3
