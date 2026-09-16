# Hermes Agent 2026 최신 학습 가이드
**기준일: 2026-09-13 · 조사 범위: 2026년 7월 이후 최신 자료 중심**

> 이 문서의 “Hermes”는 **Nous Research의 오픈소스 개인 AI 에이전트 `Hermes Agent`**를 의미합니다.  
> 공식 문서, Nous Research GitHub 릴리스, 프로젝트 문서를 우선하여 정리했습니다.

---

## 0. 30초 요약

**Hermes Agent**는 단순한 챗봇이 아니라, 사용자의 컴퓨터·브라우저·파일·메시징 서비스 등과 연결하여 **도구를 사용하고, 작업을 위임하고, 기억하고, 반복 업무를 자동화하는 개인 AI 에이전트**입니다.

핵심을 한 문장으로 표현하면:

> **“대화만 하는 AI”에서 “기억하고, 도구를 쓰고, 다른 에이전트와 협업하며, 반복 업무까지 실행하는 AI 작업자”로 확장된 오픈소스 에이전트**

2026년 7월 이후에는 특히 다음 변화가 중요합니다.

- **v0.19 (2026-07-20, Quicksilver)**: 속도와 지속성 개선, 보안 승인 기본 강화, 비밀정보 관리 개선
- **v0.20 (2026-08-03, Herald)**: 실시간 음성, A2A v1.0, 서명 웹훅, 출처 인용 기반 리서치, Desktop 확장
- **v0.21 (2026-08-31, Pantheon)**: Bot Mode, 에이전트 팀/그룹채팅, 크론 메모리, 실시간 하위 에이전트 제어, Desktop 브라우저 제어
- **v0.21.1 (2026-09-07)**: MCP 권한, 크론, 위임, 파일 처리, 세션 제어 안정화
- **v0.21.2 (2026-09-11)**: `state.db` 신뢰성 문제 집중 보완

---

# 1. Hermes Agent란 무엇인가?

## 1-1. 아주 쉽게 설명하면

ChatGPT 같은 일반 AI는 보통 **질문 → 답변** 중심입니다.

Hermes Agent는 여기에 다음 능력을 더합니다.

1. **기억하기** — 이전 대화와 사용자의 환경·선호를 기억
2. **도구 사용하기** — 파일, 터미널, 브라우저, 웹 검색 등 사용
3. **기술 배우기** — 반복되는 작업 방법을 Skill로 저장
4. **작업 나누기** — 복잡한 일을 하위 에이전트에게 분담
5. **예약 실행하기** — Cron을 통해 반복 업무 예약
6. **다른 에이전트와 협업하기** — Bot Mode·A2A
7. **여러 환경에서 사용하기** — CLI, Desktop, 메시징 플랫폼 등

### 핵심 비유

| 일반 챗봇 | Hermes Agent |
|---|---|
| 질문에 답하는 상담원 | 일을 처리하는 디지털 작업자 |
| 대화 중심 | 대화 + 도구 + 실행 |
| 세션이 끝나면 맥락이 약해질 수 있음 | 지속 메모리 사용 가능 |
| 하나의 AI 중심 | 하위 에이전트·Bot 팀 구성 가능 |
| 사람이 계속 지시 | 예약·자동화 가능 |
| 앱 안에서 주로 동작 | 컴퓨터·브라우저·메시징·MCP와 연결 |

---

# 2. Hermes의 전체 구조

```text
사용자
  │
  ├─ Hermes Desktop
  ├─ CLI / TUI
  └─ Telegram / Discord / Slack / WhatsApp 등
          │
          ▼
┌──────────────────────────────┐
│        Hermes Agent Core     │
│ 대화 · 계획 · 추론 · 도구선택 │
└──────────────────────────────┘
   │        │        │
   │        │        ├─ Memory
   │        │        ├─ Skills
   │        │        └─ Session / Context
   │        │
   │        ├─ Subagents / Bot Mode
   │        └─ Cron / Automation
   │
   ├─ Browser
   ├─ Terminal
   ├─ File Tools
   ├─ Web Search
   ├─ MCP
   ├─ Messaging
   ├─ Image / Vision / TTS
   └─ External APIs / Webhooks
```

### 구조를 이해하는 가장 쉬운 순서

**입력 → 판단 → 도구 → 기억 → 재사용 → 자동화 → 협업**

---

# 3. 핵심 구성 요소

## 3-1. Agent Core

Hermes의 중심입니다.

사용자가 “이 자료를 조사하고 정리해서 보고서로 만들어줘”라고 요청하면 Hermes는 단순 답변만 만드는 것이 아니라, 필요에 따라 다음을 판단할 수 있습니다.

- 웹 검색이 필요한가?
- 파일을 읽어야 하는가?
- 터미널 명령을 사용해야 하는가?
- 하위 에이전트에게 나누어 맡길 것인가?
- 결과를 기억해야 하는가?
- 다음에 재사용할 Skill로 저장할 가치가 있는가?

---

## 3-2. Memory — 지속 기억

Hermes는 세션을 넘어 기억을 유지하는 구조를 제공합니다.

대표적으로 다음 정보가 유지될 수 있습니다.

- 사용자 선호
- 프로젝트 환경
- 자주 쓰는 작업 방식
- 이전 작업에서 얻은 교훈
- 반복되는 설정

공식 프로젝트 구조에서는 `~/.hermes/memories/`, `state.db`, 세션 데이터 등이 중요한 역할을 합니다.

### 기억의 장점

- 매번 같은 설명을 반복할 필요가 줄어듦
- 장기 프로젝트에 유리
- 개인 작업 방식에 맞추기 쉬움

### 주의

기억은 편리하지만 **민감정보를 무조건 저장하는 것이 좋은 것은 아닙니다.**
API Key, 비밀번호, 개인정보 등은 별도의 비밀정보 관리 방식을 사용해야 합니다.

---

# 4. Skills — Hermes가 “일하는 방법”을 배우는 구조

Skill은 단순 지식이 아니라 **작업 절차를 재사용하는 설명서**에 가깝습니다.

예:

```text
“매주 AI 최신 자료 조사”
→ 자료 출처 확인
→ 공식 자료 우선
→ 날짜 검증
→ 핵심 변화 요약
→ 강의 반영 포인트 작성
→ 출처 기록
```

이 절차를 Skill로 저장하면 다음에 비슷한 일을 할 때 다시 활용할 수 있습니다.

### Tool과 Skill의 차이

| 구분 | Skill | Tool |
|---|---|---|
| 역할 | 일을 하는 방법 | 실제 기능 실행 |
| 예 | 논문 조사 절차 | 브라우저 검색 |
| 형태 | 지침·워크플로 | 프로그램 기능 |
| 장점 | 쉽게 추가·수정 | 정확한 기능 실행 |
| 추천 | 반복되는 업무 절차 | 인증·실시간·복잡한 처리 |

2026년 공식 프로젝트 가이드는 가능하면 많은 확장을 **Tool보다 Skill로 구현**하도록 권장하는 방향을 보여 줍니다.

---

# 5. Subagents — 일을 나누는 하위 에이전트

복잡한 작업을 하나의 AI가 순서대로 처리하지 않고 여러 작업으로 나누어 병렬화할 수 있습니다.

예:

```text
메인 Hermes
 ├─ 조사 담당
 ├─ 코드 검토 담당
 ├─ 문서 작성 담당
 └─ 검증 담당
```

장점:

- 복잡한 업무 분리
- 병렬 처리
- 전문 역할 부여
- 긴 작업의 구조화

2026년 8월 이후에는 하위 에이전트가 작업 중일 때 **중간에 방향을 수정(steering)**하는 기능도 강화되었습니다.

---

# 6. Bot Mode — 여러 AI를 “팀”처럼 운영

**v0.21 Pantheon**의 대표 기능입니다.

Bot Mode에서는 각 Bot이 다음을 독립적으로 가질 수 있습니다.

- 이름
- 역할
- 모델
- 지침
- 메모리
- Skills
- Tools
- Credentials
- 대화 기록

예:

```text
AI 강의 제작팀
 ├─ Research Bot
 ├─ Curriculum Bot
 ├─ PPT Bot
 ├─ Fact Check Bot
 └─ Publishing Bot
```

### Subagent와 Bot Mode의 차이

| Subagent | Bot Mode |
|---|---|
| 특정 작업을 위한 임시 작업자에 가까움 | 지속적으로 유지되는 전문 AI 구성원 |
| 메인 에이전트가 위임 | Bot끼리 협업 가능 |
| 단기 병렬 처리 | 장기 팀 운영에 적합 |

---

# 7. Cron — 반복 업무 자동화

Hermes는 예약 작업을 수행할 수 있습니다.

예:

- 매일 오전 뉴스 정리
- 매주 금요일 AI 교육 업데이트 조사
- 서버 상태 점검
- 파일 백업 확인
- 특정 자료 갱신 확인

2026년 8월 이후 Cron은 단순 예약을 넘어 **작업별 메모리와 연속성**이 강화되었습니다.

즉,

```text
1주차 조사 결과
   ↓ 기억
2주차 조사 시 이전 결과와 비교
   ↓
변화만 추려서 보고
```

같은 방식이 가능해졌습니다.

---

# 8. MCP — 외부 도구 연결 표준

MCP(Model Context Protocol)는 AI가 외부 서비스나 도구를 연결해서 사용할 수 있도록 해주는 표준 방식입니다.

Hermes는 MCP 서버를 추가해 기능을 확장할 수 있습니다.

예:

```text
Hermes
  │
  └─ MCP
      ├─ 파일 시스템
      ├─ 데이터베이스
      ├─ 개발 도구
      ├─ 사내 시스템
      └─ 외부 서비스
```

2026년 9월 패치에서 **MCP 권한과 관리 기능**이 계속 개선되고 있습니다.

---

# 9. A2A — 에이전트와 에이전트의 통신

v0.20에서 **A2A v1.0** 지원이 중요한 변화로 소개되었습니다.

A2A는 서로 다른 에이전트가 작업을 주고받고 협력할 수 있게 하는 방향입니다.

쉽게 말하면:

> “AI 한 명이 모든 것을 하는 구조” → “여러 AI 시스템이 서로 업무를 주고받는 구조”

Bot Mode가 Hermes 내부의 팀 운영에 가깝다면, A2A는 더 넓은 **에이전트 간 상호운용성**에 초점을 둔다고 이해하면 쉽습니다.

---

# 10. Desktop — GUI 기반 작업 환경

Hermes는 CLI뿐 아니라 Desktop 애플리케이션을 제공합니다.

2026년 8월 이후 Desktop은 단순 채팅창이 아니라 점점 **AI 작업 운영 환경**으로 확장되었습니다.

주요 방향:

- 다중 창
- Artifact 미리보기
- Plugin SDK
- Bot Mode
- 파일 첨부
- Desktop 브라우저
- 브라우저 직접 제어
- 세션 관리
- 모델 선택
- 음성 상호작용

---

# 11. Browser — 웹 탐색과 조작

v0.21에서는 Hermes가 Desktop 내부 브라우저를 직접 제어하는 방향이 강화되었습니다.

가능한 작업 유형:

- 웹페이지 탐색
- 링크 열기
- 정보 읽기
- 개발 문서 확인
- 웹 앱 테스트 지원

### 매우 중요한 원칙

브라우저 자동화는 편리하지만 다음 작업은 반드시 사람이 최종 확인하는 것이 좋습니다.

- 결제
- 삭제
- 계정 변경
- 외부 게시
- 민감정보 입력
- 법적·재정적 영향이 있는 작업

---

# 12. Voice — 음성 기반 Agent

v0.20 Herald의 대표 기능 중 하나입니다.

포함된 방향:

- 실시간 대화형 음성
- Streaming TTS
- 말 끊기(barge-in)
- Wake word
- Hands-free 제어

즉 Hermes를 키보드 중심 도구가 아니라 **음성으로도 조작하는 개인 AI**로 확장하려는 흐름입니다.

---

# 13. Grounded Research — 출처를 확인하는 조사

v0.20에서는 **출처 인용과 사실 확인을 포함한 조사 기능**이 강조되었습니다.

AI 조사에서 가장 중요한 문제는 “그럴듯하지만 틀린 답”입니다.

따라서 좋은 연구 흐름은:

```text
질문
→ 웹 검색
→ 공식/1차 자료 확인
→ 여러 출처 비교
→ 날짜 확인
→ 주장과 근거 연결
→ 출처 표시
→ 사람이 최종 검토
```

입니다.

---

# 14. Webhooks — 외부 시스템에 이벤트 전달

Hermes는 작업 결과나 이벤트를 외부 시스템으로 전달할 수 있습니다.

v0.20에서는 **서명된 outbound webhook**이 핵심 변화로 포함되었습니다.

활용 예:

- 자동화 서버 호출
- CI/CD 연결
- 업무 시스템 알림
- 사내 서비스 트리거

서명 기능은 “정말 Hermes가 보낸 요청인지” 확인하는 데 도움을 줍니다.

---

# 15. 지원 모델·Provider 구조

Hermes의 큰 장점 중 하나는 **특정 한 회사의 모델에 고정되지 않는 구조**입니다.

공식 프로젝트 문서에는 다음과 같은 여러 Provider 경로가 소개됩니다.

- Nous Portal
- OpenRouter
- Anthropic
- OpenAI 계열
- Google Gemini
- DeepSeek
- xAI 계열
- GitHub Copilot
- 기타 Provider
- 사용자 지정 Endpoint

### 의미

Hermes 자체가 “언어모델”인 것이 아니라,

```text
Hermes Agent = 작업 실행 프레임워크
LLM = Hermes의 사고 엔진
```

으로 보는 것이 정확합니다.

---

# 16. Hermes와 Hermes 모델을 구분하자

“Nous Hermes”라는 이름은 과거부터 여러 언어모델 계열에도 사용되어 왔습니다.

하지만 이 문서의 중심은 **Hermes Agent**입니다.

구분:

| 이름 | 의미 |
|---|---|
| Hermes Agent | AI 에이전트 실행·자동화 프레임워크 |
| Hermes 모델 계열 | Nous Research가 공개한 언어모델 계열 |
| Nous Portal | Hermes가 연결할 수 있는 서비스·인증 경로 중 하나 |

혼동하지 않는 것이 중요합니다.

---

# 17. 2026년 7월 이후 릴리스 타임라인

## 2026-07-20 — v0.19.0 Quicksilver

핵심 방향:

- 첫 응답 속도 개선
- Desktop/TUI Streaming 개선
- 구독 관리
- Smart command approvals 기본화
- Bitwarden / 1Password 비밀정보 소스
- Subagent와 메시지 전달 지속성 개선

### 의미

“기능 추가”보다 **실제로 오래 돌려도 안정적인 Agent**에 가까워지는 단계입니다.

---

## 2026-08-03 — v0.20.0 Herald

대표 변화:

- 실시간 대화형 Voice
- Wake word
- A2A v1.0
- 서명 outbound webhooks
- 인용 기반 Grounded Research
- Desktop Artifacts
- Plugin SDK
- CLI 고급 명령
- Tool 실패 복구 개선

### 의미

Hermes가 “개인 AI 도구”에서 **다른 AI·외부 시스템과 연결되는 허브**로 확장됩니다.

---

## 2026-08-31 — v0.21.0 Pantheon

대표 변화:

- Bot Mode
- Bot 그룹채팅
- Peer messaging
- Cron memory
- Continuity
- Subagent live steering
- MCP 관리 강화
- Desktop browser control
- 보안 강화

### 의미

Hermes가 하나의 Agent에서 **다중 Agent 운영 플랫폼**으로 발전하는 분기점입니다.

---

## 2026-09-07 — v0.21.1

주요 안정화:

- 코드베이스 모듈화
- 파일 작업 성능
- Startup 성능
- Provider/Model 업데이트
- Desktop 세션 제어
- Browser annotation
- MCP authorization
- Cron 수정
- Delegation 안정성

---

## 2026-09-11 — v0.21.2

**현재 조사 기준 최신 안정 릴리스**

핵심 초점:

- `state.db` 신뢰성
- 다중 writer 관련 문제
- DB lock 취소 문제
- 정상 DB를 손상으로 오판하는 문제
- 잘못된 단일 행 때문에 세션 목록 전체가 실패하는 문제

### 의미

v0.21에서 크게 확장된 기능을 실제 운영 환경에서 안정적으로 사용할 수 있도록 데이터 저장 계층을 보강하는 패치입니다.

---

# 18. 보안 구조

Hermes는 실제 컴퓨터와 도구를 사용할 수 있기 때문에 일반 챗봇보다 **권한 관리가 훨씬 중요**합니다.

## 중요한 보호 원칙

1. 위험 명령은 승인 절차 사용
2. Agent 지침 파일 변경은 승인 요구
3. Secret/API Key를 일반 대화에 노출하지 않기
4. `.env` 및 인증정보 취급 주의
5. 외부 Skill 설치 전 검사
6. MCP 서버 권한 확인
7. Browser 자동화의 민감 작업은 사람 확인
8. `--yolo`와 같은 승인 우회 기능은 테스트 환경 외 사용 주의

### 2026년 8월 이후 보안 강화 사례

- 지침 파일 쓰기 승인
- Secret redaction 강화
- Windows 파괴적 명령 승인 확대
- Skill 설치 보안 검사
- MCP authorization 개선

---

# 19. 장점과 단점

## 장점

### ① 오픈소스
MIT License 기반으로 소스 확인·수정·확장 가능.

### ② Provider 독립성
여러 LLM을 선택할 수 있어 특정 업체 종속을 줄일 수 있음.

### ③ 지속 메모리
장기 프로젝트에 유리.

### ④ Skill 학습
반복 업무를 재사용 가능한 절차로 만들 수 있음.

### ⑤ 강력한 자동화
Cron, Browser, Terminal, MCP, Webhook 등과 결합 가능.

### ⑥ 다중 Agent
Subagent와 Bot Mode를 이용해 역할 기반 협업 가능.

### ⑦ 다양한 인터페이스
Desktop, CLI, 메시징 플랫폼 등.

---

## 단점·주의점

### ① 초보자에게 설정이 복잡할 수 있음
모델, Provider, API Key, Tool, MCP, 권한 등 많은 개념이 존재.

### ② 권한이 강한 만큼 위험도 큼
터미널·파일·브라우저를 사용할 수 있어 잘못된 명령의 영향이 큼.

### ③ 업데이트 속도가 매우 빠름
2026년에는 수천 개 커밋이 짧은 기간에 통합되는 경우가 있어 버전별 차이가 큼.

### ④ 안정성 검증 필요
v0.21.2의 `state.db` 패치 사례처럼 큰 업데이트 뒤에는 운영 이슈가 생길 수 있음.

### ⑤ 모델 비용은 별도
오픈소스 Agent라도 연결하는 LLM/API에 따라 비용이 발생할 수 있음.

---

# 20. Hermes가 잘 맞는 사용자

추천도가 높은 경우:

- 개발자
- AI 에이전트 연구자
- 개인 업무 자동화 사용자
- 서버/시스템 관리자
- 반복 리서치 업무가 많은 사람
- 장기 프로젝트를 AI와 함께 진행하는 사람
- 여러 모델을 비교·교체하며 쓰고 싶은 사람
- MCP·웹훅·자동화 도구를 연결하고 싶은 사람

초보자라면 처음부터 모든 기능을 쓰기보다 아래 순서를 권장합니다.

```text
1단계: Desktop/기본 Chat
2단계: Memory
3단계: Skills
4단계: Browser/File
5단계: Subagents
6단계: Cron
7단계: MCP
8단계: Bot Mode
9단계: A2A / Webhook
```

---

# 21. 학습용 권장 실습 순서

## 초급

### 실습 1 — 기본 대화
목표: Hermes UI에 익숙해지기

### 실습 2 — 모델 바꾸기
목표: Agent와 LLM을 구분해서 이해하기

### 실습 3 — 파일 읽기
목표: Tool 사용 개념 이해

### 실습 4 — Memory
목표: 세션을 넘어 기억이 유지되는 구조 이해

---

## 중급

### 실습 5 — Skill 만들기
반복 업무를 하나의 Skill로 정의

### 실습 6 — Web Research
검색 → 출처 확인 → 요약 → 검증

### 실습 7 — Subagent
조사/작성/검증 역할 분리

### 실습 8 — Cron
주간 업데이트 자동화

---

## 고급

### 실습 9 — MCP 연결
외부 도구 연결

### 실습 10 — Bot Mode
전문 Bot 팀 구성

### 실습 11 — Webhook
외부 시스템 연결

### 실습 12 — A2A
다른 Agent 시스템과 협력

---

# 22. 1인 개발자·교육자 관점 활용 예

## AI 강의자료 자동 제작

```text
Research Bot
→ 최신 AI 공식 자료 조사

Curriculum Bot
→ 학습자 수준에 맞게 재구성

Fact Check Bot
→ 발표일·버전·출처 확인

Visual Bot
→ 이미지 프롬프트 작성

Publisher Bot
→ Markdown / HTML / PPT 구조화
```

## 웹 개발

```text
요구사항
→ 코드베이스 분석
→ Subagent 병렬 검토
→ 수정
→ 브라우저 테스트
→ 오류 확인
→ 문서 작성
```

## 주간 정보 업데이트

```text
Cron
→ 공식 사이트 검색
→ 지난주 Memory와 비교
→ 새 내용만 추출
→ 요약
→ 지정 채널에 전달
```

---

# 23. Hermes와 다른 AI 도구의 차이

| 항목 | 일반 Chat AI | 코딩 Agent | Hermes Agent |
|---|---|---|---|
| 대화 | 매우 강함 | 강함 | 강함 |
| 파일 작업 | 일부 | 강함 | 강함 |
| 터미널 | 제한적 | 강함 | 강함 |
| 지속 메모리 | 제품별 차이 | 제품별 차이 | 핵심 구조 |
| Skill 학습 | 제한적 | 일부 | 핵심 기능 |
| Cron | 제한적 | 일부 | 내장 |
| 메시징 Gateway | 드묾 | 드묾 | 폭넓음 |
| Multi-agent | 일부 | 일부 | Subagent + Bot Mode |
| MCP | 증가 추세 | 증가 추세 | 적극 지원 |
| A2A | 제한적 | 제한적 | v1.0 지원 |
| 오픈소스 | 제품별 차이 | 제품별 차이 | MIT |

---

# 24. 설치·운영 전 체크리스트

- [ ] 공식 GitHub와 공식 문서 확인
- [ ] 최신 릴리스 버전 확인
- [ ] 운영 전에 테스트 환경에서 검증
- [ ] 사용할 LLM Provider 결정
- [ ] API Key 저장 위치 확인
- [ ] 위험 명령 승인 설정 확인
- [ ] Memory에 저장할 정보 범위 결정
- [ ] 설치 Skill 출처 확인
- [ ] MCP 서버 권한 확인
- [ ] Cron 자동 실행 범위 확인
- [ ] 외부 발송·삭제·게시 작업은 승인 단계 추가
- [ ] 업데이트 전 백업
- [ ] `state.db` 및 세션 데이터 관리 정책 마련

---

# 25. 핵심 용어 사전

| 용어 | 쉬운 뜻 |
|---|---|
| Agent | 스스로 여러 단계를 수행하는 AI 작업자 |
| LLM | Agent의 언어·추론을 담당하는 AI 모델 |
| Tool | AI가 실제 작업을 수행할 때 쓰는 기능 |
| Skill | 반복 업무를 수행하는 방법을 적은 작업 설명서 |
| Memory | 이전 정보를 기억하는 구조 |
| Subagent | 일부 업무를 맡는 하위 AI |
| Bot Mode | 여러 전문 AI를 팀처럼 운영하는 방식 |
| Cron | 예약·반복 실행 기능 |
| MCP | AI와 외부 도구를 연결하는 표준 |
| A2A | Agent와 Agent 사이의 통신 방식 |
| Webhook | 이벤트가 발생했을 때 외부 시스템으로 알림/요청 전송 |
| Gateway | 여러 메시징 플랫폼과 Hermes를 연결하는 중간 통로 |
| Provider | 실제 LLM을 제공하는 서비스 |
| Profile | 설정·기억·Skill 등을 분리한 독립 Hermes 환경 |
| Grounding | 답변을 실제 자료와 연결해 근거를 확인하는 방식 |

---

# 26. 최종 평가

## 한 줄 평가

**Hermes Agent는 2026년 하반기 기준 “개인 AI 비서”보다 “개인 AI 운영 플랫폼”에 가까워지고 있습니다.**

### 가장 중요한 변화 3가지

1. **기억 + Skill → 사용하면서 계속 축적되는 Agent**
2. **Subagent + Bot Mode + A2A → 여러 AI가 협력하는 구조**
3. **Cron + Browser + MCP + Webhook → 실제 업무 자동화 플랫폼**

### 교육 관점에서 반드시 강조할 점

Hermes를 가르칠 때는 기능보다 먼저 다음 구조를 이해시키는 것이 좋습니다.

> **LLM이 생각하고 → Agent가 계획하고 → Tool이 실행하고 → Memory가 기억하고 → Skill이 재사용하고 → Cron이 반복하고 → 다른 Agent와 협업한다.**

---

# 27. 공식 자료 및 참고자료

## 1차·공식 자료

1. **Hermes Agent 공식 문서**  
   https://hermes-agent.nousresearch.com/docs/

2. **NousResearch / hermes-agent GitHub**  
   https://github.com/NousResearch/hermes-agent

3. **GitHub Releases**  
   https://github.com/NousResearch/hermes-agent/releases

4. **Hermes Agent 개발 가이드 / AGENTS.md**  
   https://github.com/NousResearch/hermes-agent/blob/main/AGENTS.md

5. **CONTRIBUTING.md**  
   https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md

## 본 문서에서 중점 확인한 릴리스

- v2026.7.20 — Hermes Agent v0.19.0 Quicksilver
- v2026.8.3 — Hermes Agent v0.20.0 Herald
- v2026.8.31 — Hermes Agent v0.21.0 Pantheon
- v2026.9.7 — Hermes Agent v0.21.1
- v2026.9.11 — Hermes Agent v0.21.2

---

## 학습 마무리 질문

다음 질문에 답할 수 있으면 Hermes의 핵심 구조를 이해한 것입니다.

1. Hermes Agent와 LLM은 무엇이 다른가?
2. Tool과 Skill은 무엇이 다른가?
3. Memory는 왜 필요한가?
4. Subagent와 Bot Mode는 어떻게 다른가?
5. Cron은 단순 예약과 무엇이 달라졌는가?
6. MCP는 왜 중요한가?
7. A2A는 어떤 미래 구조를 의미하는가?
8. Agent에게 강한 컴퓨터 권한을 줄 때 왜 승인이 필요한가?
9. v0.20과 v0.21의 가장 큰 차이는 무엇인가?
10. 실제 업무에서 Hermes를 어디까지 자동화하고 어디에서 사람이 승인해야 하는가?

---

**작성 기준일: 2026-09-13**  
**권장: 실제 설치 전 공식 릴리스 페이지에서 최신 태그를 다시 확인하세요.**