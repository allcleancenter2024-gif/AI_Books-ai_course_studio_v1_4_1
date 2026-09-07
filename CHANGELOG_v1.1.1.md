# v1.1.1 변경사항

- LM Studio/Ollama 로컬 모델의 120초 timeout 문제 수정
- 로컬 모델 read timeout 최대 900초(15분)
- connect timeout 8초로 분리
- ReadTimeout 1회 자동 재시도
- 연결 실패/생성 지연 오류 메시지 세분화
- 로컬 생성 출력량을 줄이는 경량 모드 추가
- 웹 화면에 로컬 생성 지연 안내 추가
- 포트 8765 유지
