# v1.26.0 — 2026-09-09

- 주차별 `VisualAsset`와 `ImagePrompt`를 기존 Lesson Unit과 분리한 additive SQLite 모델로 추가했습니다.
- 이미지 바이너리는 Local AssetStorage에만 저장하고, SQLite에는 경로·ALT·크기·체크섬·저작권·승인 메타데이터만 보관합니다.
- JPG/JPEG, PNG, WEBP의 실제 포맷·MIME·확장자·용량·픽셀 수를 교차 검증합니다.
- 한글/영문 이미지 Prompt 초안과 검토 승인을 추가했으며, AI 이미지 자동 생성·자동 출판은 포함하지 않습니다.
- 학생/강사용 및 PC/Tablet/Mobile 검토 미리보기, 지연 이미지 로딩, ALT·저작권·Prompt 체크리스트를 Studio에 추가했습니다.
- Publisher에서 교재 ID를 기본 입력하지 않고 현재 교재를 목록에서 선택하며, 주차·이전/다음·URL 상태를 자동 연결합니다. 기존 `course_id` 입력은 고급 설정 fallback으로 유지합니다.
- 품질 검사와 강사 승인, 이미지 검증을 모두 통과한 경우에만 Publication Snapshot을 생성하도록 출판 게이트를 유지했습니다.

SQLite, 기존 Lesson Unit, Docker, Tailscale, 공개 네트워크, Publisher의 Studio DB 직접 접근 방식은 변경하지 않았습니다.
