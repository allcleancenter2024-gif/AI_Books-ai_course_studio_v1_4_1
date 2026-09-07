# AI 강의 활용 Studio v1.7.0 [2026-08-25]

- 새 참고자료·과정·교재의 기본 기록을 SQLite에서 MongoDB·PostgreSQL로 전환했습니다.
- 참고자료 ID는 PostgreSQL 서비스 레코드에서 발급하고, 원문과 벡터 청크는 MongoDB에 저장합니다.
- 참고자료 삭제 시 MongoDB 원문·벡터와 PostgreSQL 서비스 매핑을 함께 삭제합니다.
- SQLite 파일은 기존 데이터의 읽기 전용 복구·폴백 용도로만 보존합니다.
