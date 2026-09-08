/** A configured URL is not proof of domain ownership, DNS or TLS. */
export function inspectPublicUrl(value) {
  const text = (value || '').trim();
  if (!text) return { state: 'not-configured', detail: '공개 주소가 비어 있습니다.' };
  try {
    const url = new URL(text);
    const host = url.hostname.toLowerCase();
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash ||
        url.pathname !== '/' || !host.includes('.') || /^[\d.]+$/.test(host) || host.includes(':') ||
        /(^|\.)(localhost|local|test|invalid|example)$/.test(host) ||
        /(^|\.)example\.(com|net|org)$/.test(host)) {
      return { state: 'invalid', detail: '실제 공개 도메인의 HTTPS 기본 주소가 필요합니다.' };
    }
    return { state: 'unverified', detail: '주소 형식만 확인했습니다. 도메인 소유·DNS·TLS는 검증하지 않았습니다.' };
  } catch {
    return { state: 'invalid', detail: '주소 형식이 올바르지 않습니다.' };
  }
}

export function getPublicConfig(env) {
  const environment = env.PUBLISHER_APP_ENV || 'development';
  if (!['development', 'preview', 'production'].includes(environment)) throw new Error('Invalid PUBLISHER_APP_ENV');
  return { environment, domain: inspectPublicUrl(env.PUBLISHER_PUBLIC_BASE_URL),
    api: inspectPublicUrl(env.PUBLISHER_API_PUBLIC_URL), publisherReady: false };
}
