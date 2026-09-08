export type UrlCheck = { state: 'not-configured' | 'invalid' | 'unverified'; detail: string };
export function inspectPublicUrl(value?: string): UrlCheck;
export function getPublicConfig(env: Record<string, string | undefined>): {
  environment: string; domain: UrlCheck; api: UrlCheck; publisherReady: false;
};
