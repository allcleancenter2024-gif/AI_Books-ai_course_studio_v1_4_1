# v1.1 변경 사항

- OpenAI / Gemini / Claude / LM Studio / Ollama 통합 Provider 엔진 추가
- OpenAI 기본 모델: gpt-5.6-terra
- Gemini 기본 모델: gemini-3.6-flash
- Claude 기본 모델: claude-sonnet-5
- LM Studio 기본 URL: http://127.0.0.1:12345/v1
- Ollama 기본 URL: http://127.0.0.1:11434/v1
- Studio 웹 서버: http://127.0.0.1:8765
- API 키 런타임 메모리 보관 방식 적용(DB 저장 안 함)
- Provider 연결 테스트 기능
- LM Studio/Ollama 모델 검색 기능
- AI 기반 주차별 학생용·강사용 교재 생성
- 매 주 예시 프롬프트 10개 및 실습 10개 강제 검증
- 각 예시/실습: 이유, 방법/단계, 예상결과, 검증방법 포함
- 12주/15주 전체 또는 구간 교재 생성
- 생성 교재 SQLite 메타데이터 기록
- Markdown 자동 출력
- 오류 메시지 및 API 응답 검증 강화
