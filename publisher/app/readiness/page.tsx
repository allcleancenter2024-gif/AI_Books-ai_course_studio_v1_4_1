import type { Metadata } from 'next';
import Link from 'next/link';
import { getReadinessItems, stateLabels } from '../../lib/readiness';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = { title: '공개 준비 상태', description: 'Publisher 공개 전 준비 상태를 확인합니다.' };

export default function ReadinessPage() {
  const readinessItems = getReadinessItems();
  return <main className="lesson-shell"><header className="site-header"><Link href="/" className="brand">느린 배움 교재</Link><Link href="/" className="back-link">교재 목록</Link></header><article className="lesson"><p className="kicker">배포 준비 확인</p><h1>공개 준비 상태</h1><p className="lead">공개 도메인과 HTTPS가 아직 없어도 로컬 교재 제작과 검증은 계속할 수 있습니다.</p><section className="readiness-list" aria-label="공개 준비 상태 목록">{readinessItems.map((item) => <div className="readiness-row" key={item.label}><span className={`status-dot ${item.state}`} aria-hidden="true" /><div><h2>{item.label}</h2><p>{item.detail}</p></div><strong>{stateLabels[item.state] || item.state}</strong></div>)}</section><p>“미구성”은 오류가 아닙니다. 실제 도메인을 확보한 뒤 별도 승인 절차에서 DNS와 HTTPS를 설정합니다.</p></article></main>;
}
