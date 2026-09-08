# AI Course Studio Publisher

기존 AI Course Studio가 생성한 검증된 Markdown을 읽어 독립적인 웹 교재로 발행하는 Next.js 프로젝트입니다.

## 안전 경계

- Studio의 Python 코드, SQLite 데이터베이스, Docker Compose, 인증, API를 호출하거나 수정하지 않습니다.
- `content/courses/`에 복사한 공개 가능 Markdown만 정적 사이트로 발행합니다.
- API 키, 내부 URL, 개인 정보, 업로드 원본은 발행 Markdown에 포함하지 않습니다.

## 실행

```powershell
npm.cmd install
npm.cmd run check
npm.cmd run dev
```

브라우저에서 `http://localhost:3000`을 열어 확인합니다.

## 공개 도메인 전 준비

`.env.example`을 참고하되, 실제 도메인을 확보하기 전에는 `PUBLISHER_PUBLIC_BASE_URL`과 `PUBLISHER_API_PUBLIC_URL`을 빈 값으로 유지합니다. 이 값이 비어 있어도 로컬 Preview와 콘텐츠 검사는 정상 동작합니다. 실제 도메인, DNS, 유효한 HTTPS 인증서가 준비된 다음에만 해당 값을 설정하고 다시 빌드합니다.

## 발행 순서

1. Studio에서 Markdown을 내보냅니다.
2. `content/courses/<course-id>/<lesson-id>.md`에 공개 검토본을 복사합니다.
3. front matter와 본문 구조를 확인합니다.
4. `npm.cmd run check`를 통과시킵니다.
5. Preview 환경에 배포하고 브라우저 검증 후 운영에 승격합니다.

## 원고 규약

모든 파일은 YAML front matter에서 `course_id`, `lesson_id`, `title`, `audience`, `learning_objectives`, `estimated_minutes`, `published`를 제공해야 합니다. 본문에는 `## 학습 목표`, `## 핵심 내용`, `## 단계별 실습`, `## 핵심 요약` 제목이 각각 한 번 이상 있어야 합니다.
