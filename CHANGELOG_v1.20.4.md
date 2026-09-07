# AI Course Studio v1.20.4

- Ollama 생성 경로를 네이티브 `/api/chat`으로 분리해 thinking을 확실히 끕니다.
- 출력 토큰이 내부 추론에 소진되어 본문이 비는 `finish_reason=length` 오류를 해결했습니다.
- lesson·prompts·exercises 동안 모델을 10분간 메모리에 유지해 반복 로딩을 제거했습니다.
- lesson과 exercises의 출력 예산을 실제 JSON 스키마 크기에 맞게 조정했습니다.
- 자동 연결은 약 3GiB 범용 모델을 우선 선택해 3단계 교재 생성 시간을 단축합니다.
- 실제 qwen3.5:2b 전체 통합 생성에서 프롬프트 3개, 실습 7개, 경고 0개를 확인했습니다.
