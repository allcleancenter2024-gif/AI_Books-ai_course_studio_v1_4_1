# AI 강의 활용 Studio v1.3.0 변경사항

## 핵심 목표
자료 수집과 교재 생성을 분리하여, 여러 파일·웹·영상 자료를 안전하게 모으고 필요한 자료만 선택해 학생용/강사용 교재에 반영하도록 구조를 확장했습니다.

## 새 기능
- 참고자료 라이브러리 추가
- 업로드: `.md`, `.markdown`, `.txt`, `.html`, `.htm`, `.pdf`, `.pptx`, `.png`, `.jpg`, `.jpeg`, `.webp`
- 웹 URL 본문 추출 및 저장
- YouTube/영상 URL 저장; 선택적 자막 모듈이 있으면 텍스트 추출, 없어도 링크 기능은 정상 동작
- OpenAI(ChatGPT), Gemini, Claude, LM Studio, Ollama 중 선택하여 참고자료 요약
- 이미지 자료는 선택 AI의 Vision 기능으로 요약 가능(모델이 이미지 입력을 지원할 때)
- 체크한 자료만 1주/전체 교재 생성에 참고문맥으로 전달
- Gemini Notebook용 ZIP 자료팩 생성
- Gemini 앱 열기 버튼
- Gemini Notebook Enterprise API: Notebook 생성, 웹/YouTube/파일/텍스트 소스 동기화
- 상단 상태바에 선택 참고자료 개수 표시

## 안정성
- 외부 URL은 http/https만 허용
- localhost, 사설 IP, link-local 등 차단
- 리디렉션도 매 단계 주소를 다시 검사
- 업로드 파일은 80MB 상한
- 추출 텍스트 길이 상한 및 교재 주입 문맥 길이 상한 적용
- Gemini Notebook Enterprise 인증은 API 키를 저장하지 않고 `gcloud auth print-access-token` 사용

## 참고
일반 Gemini Notebook에는 공개적인 개인용 자동 생성 API를 가정하지 않습니다. 일반 사용자는 자료팩 + Gemini 앱 방식, Google Cloud의 Gemini Notebook Enterprise 사용자는 공식 API 직접 연동 방식을 사용합니다.
