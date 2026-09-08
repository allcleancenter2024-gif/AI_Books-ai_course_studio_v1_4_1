import { readPublicConfig } from './public-config';

export type ReadinessItem = { label: string; state: string; detail: string };

export const stateLabels: Record<string, string> = {
  'not-configured': '미구성', invalid: '설정 확인 필요', unverified: '미검증',
  prepared: '초안 준비', waiting: '대기', available: '사용 가능',
};
export function getReadinessItems(): ReadinessItem[] {
  const config = readPublicConfig();
  return [
    { label: '실행 환경', state: 'available', detail: config.environment },
    { label: '공개 도메인', ...config.domain },
    { label: '공개 API 주소', ...config.api },
    { label: 'DNS 및 TLS 인증서', state: 'unverified', detail: '네트워크 검증을 실행하지 않았습니다. 주소 입력만으로 준비 완료가 되지 않습니다.' },
    { label: '개인정보 처리방침·이용약관', state: 'prepared', detail: '페이지 구조만 준비했습니다. 운영 주체·문의처·실제 처리 항목 검토가 필요합니다.' },
    { label: '콘텐츠·접근성 검사', state: 'unverified', detail: '현재 화면은 실시간 검사 결과가 아닙니다. 릴리스의 검증 기록을 확인하세요.' },
    { label: 'Publisher 공개 승인', state: 'waiting', detail: 'PUBLISHER_READY=false · 자동 공개는 수행하지 않습니다.' },
  ];
}
