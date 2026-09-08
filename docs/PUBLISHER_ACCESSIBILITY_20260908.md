# Publisher 접근성 점검 — 2026-09-08

## 후속 읽기 접근성 점검

`publisher/scripts/audit-reading.mjs`를 추가해 운영 Preview 6개 페이지를 별도 headless Chrome에서 검사했다. 실행: `node scripts/audit-reading.mjs` (publisher 폴더, 선택형 playwright 필요).

- 1280 CSS px 폭에서 모든 요소의 계산된 font-size를 먼저 저장한 뒤 각각 2배로 적용했다. 부모·자식 중복 배율을 방지했다.
- 6개 페이지 모두 innerText 보존, 문서 가로 넘침 없음. 이 검사는 텍스트 확대 스트레스 테스트이며 브라우저 자체 200% 확대의 대체 인증이 아니다. 텍스트 문자열 보존만으로 모든 글자의 시각적 잘림 부재를 보장하지 않는다.
- Chrome Accessibility.getFullAXTree 결과, 모든 페이지에서 main 역할 1개, 한국어 lang, 이름 없는 링크 0개 확인. 제목 수는 홈 3, 대표 교재 7, 준비 상태 8, 나머지 3개씩이다.
- 실제 NVDA 명령은 현재 PATH에서 확인되지 않았다. 프로세스 확인에서도 실행 중인 NVDA/Narrator를 확인하지 못했다. 이것만으로 설치되지 않았다고 단정하지 않는다.
- 실제 음성 낭독·발음·가상 커서 이동·브라우저 자체 확대는 미검증이다. 이 환경에서 지원하지 않는 네이티브 제어를 우회하거나 낭독기를 임의 설치·실행하지 않았다.
- 애플리케이션 결함은 이번 검사에서 추가 발견되지 않아 운영 코드와 서버 프로세스는 변경하지 않았다. 검사 스크립트와 문서만 추가·갱신했다.


## 결과와 범위

대상: 홈, 대표 교재, 공개 준비 상태, 개인정보 초안, 이용약관 초안, 도움말.
Chrome headless + axe-core로 320/375/768/1280 CSS px 화면 폭에서 총 24개 조합을 검사했다.
WCAG 2 A/AA 및 2.1 AA 태그 자동 검사 위반 0건, 문서 가로 넘침 0건, 페이지 JavaScript 예외 0건.
이는 WCAG 전체 준수 인증이나 실제 모바일·스크린리더 검사 완료를 뜻하지 않는다.

## 발견 및 수정

LOW: 상단 브랜드 링크와 하단 도움말 링크가 자체 시니어 클릭 영역 기준 44×44px보다 작았다.
브랜드에 inline-flex/최소 높이·너비, 푸터 링크에 최소 너비를 적용했다.
수정 후 24개 조합에서 검사 대상 링크의 작은 클릭 영역 0건.
44px 기준은 WCAG 2.1의 2.5.5 AAA 기준을 참고한 추가 설계 목표이며 AA 위반으로 분류하지 않았다.

## 키보드와 구조

연결된 Chrome에서 Tab으로 본문 바로가기 포커스와 파란 테두리를 시각 확인했다.
Enter와 Tab으로 교재 시작 링크를 선택하고 Enter로 실제 교재 화면이 열림을 확인했다.
자동 검사에서는 첫 포커스가 '본문으로 이동', Enter 후 활성 요소 ID가 publisher-content임을 확인했다.
lang=ko, 제목 구조와 링크 이름은 소스/접근성 트리로 확인했다. NVDA 음성 낭독 실험은 하지 않았다.

## 색상 대비 계산

토큰의 paper/mint/sky/lavender/peach 배경에 대해 상대 휘도 식으로 계산했다.

| 요소 | 전경 | 배경별 최소 대비 | 판정 |
|---|---|---|---|
| 본문 | #19324a | 11.01:1 | 일반 글자 4.5:1 이상 |
| 보조 글자 | #4d6375 | 5.23:1 | 일반 글자 4.5:1 이상 |
| 포커스 | #005fcc | 5.01:1 | 확인한 배경 대비 충분 |

근거: [W3C 글자 대비](https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html), [W3C 클릭 영역 2.5.5 AAA](https://www.w3.org/WAI/WCAG21/Understanding/target-size.html).

## 재현 및 배포

`publisher/scripts/audit-accessibility.mjs` 추가. 로컬 주소만 허용하고 검사 결과를 출력한다.
선택형 점검 도구로 현재 Node 환경의 playwright와 axe-core를 사용한다. 신규 환경은 해당 도구 준비가 필요하며 기본 npm check에 포함하지 않았다.
`node scripts/audit-accessibility.mjs`로 기본 3010 Preview를 검사한다. 다른 로컬 포트는 PUBLISHER_AUDIT_URL로 지정한다.
검사 대상은 링크 표본이며 본문 속 모든 향후 Markdown 링크를 전수 검사하는 것은 아니다.

보완본 npm check(단위 테스트 6개, 콘텐츠·상대 링크·ESLint·TypeScript·빌드) 통과.
분리 빌드 `.next-a11y`, 릴리스 `publisher/releases/v1.25.0-a11y-20260908` 사용.
기존 릴리스는 보존하고, 3013에서 재검사 후 3010으로 전환했다. Studio·DB·방화벽 변경 없음.

## 미실시

- 실제 NVDA/VoiceOver 사용 및 모바일 기기 터치 검사.
- 브라우저 확대율이 실제 200%인지 검증하는 확대 검사. 단축키 시도는 확인되지 않아 성공으로 집계하지 않았다.
- 전체 콘솔 메시지 및 네트워크 요청 오류의 전수 수집(pageerror만 집계).
- 향후 원고의 표·이미지·긴 URL·복잡한 인터랙션 검사.

결론: 현재 표본에 대한 자동·키보드 점검과 클릭 영역 보완 완료. 미실시 항목은 별도 검증 필요.
