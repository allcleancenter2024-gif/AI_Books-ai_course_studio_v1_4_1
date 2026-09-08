import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: { default: '느린 배움 교재', template: '%s | 느린 배움 교재' },
  description: '큰 글씨와 단계별 실습으로 배우는 시니어 친화형 디지털 교재',
};

export const viewport: Viewport = { width: 'device-width', initialScale: 1, themeColor: '#fffdf8' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body><a className="skip-link" href="#publisher-content">본문으로 이동</a><div id="publisher-content" tabIndex={-1}>{children}</div><footer className="site-footer"><nav aria-label="안내"><a href="/readiness">공개 준비 상태</a><a href="/legal/privacy">개인정보 처리방침</a><a href="/legal/terms">이용약관</a><a href="/support">도움말</a></nav><p>느린 배움 교재</p></footer></body></html>;
}
