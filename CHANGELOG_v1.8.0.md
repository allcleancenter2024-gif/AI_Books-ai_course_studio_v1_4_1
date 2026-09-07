# AI 강의 활용 Studio v1.8.0 [2026-08-25]

- 운영용 SQLite 데이터베이스를 실행 경로에서 분리하고, 검증 가능한 레거시 백업으로 보관하도록 변경했습니다.
- MongoDB·PostgreSQL이 프로그램의 유일한 운영 DB가 되었습니다.
- 레거시 SQLite는 `data/legacy_archive`의 읽기 전용 복구용 파일로만 유지합니다.
