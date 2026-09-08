import Link from 'next/link';

export default function NotFound() {
  return <main className="empty-state"><h1>교재를 찾지 못했습니다.</h1><p>주소가 맞는지 확인하거나 교재 목록으로 돌아가세요.</p><Link href="/">교재 목록으로 돌아가기</Link></main>;
}
