'use client';

export default function Error({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="empty-state"><h1>교재를 열지 못했습니다.</h1><p>잠시 후 다시 시도해 주세요.</p><button onClick={() => reset()}>다시 시도하기</button></main>;
}
