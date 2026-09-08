import test from 'node:test';
import assert from 'node:assert/strict';
import { getPublicConfig, inspectPublicUrl } from '../lib/config-policy.mjs';

test('empty public settings are normal and never enable publishing', () => {
  const config = getPublicConfig({});
  assert.equal(config.domain.state, 'not-configured');
  assert.equal(config.publisherReady, false);
});
test('invalid, local, credential-bearing and example URLs are rejected', () => {
  for (const url of ['x', 'https://', 'http://learn.school.org', 'https://127.0.0.1', 'https://localhost', 'https://example.com', 'https://a:b@learn.school.org', 'https://learn.school.org/path']) {
    assert.equal(inspectPublicUrl(url).state, 'invalid');
  }
});
test('well formed HTTPS is still unverified', () => {
  assert.equal(inspectPublicUrl('https://learn.school.org').state, 'unverified');
});
test('preview is preserved and unknown environments fail explicitly', () => {
  assert.equal(getPublicConfig({ PUBLISHER_APP_ENV: 'preview' }).environment, 'preview');
  assert.throws(() => getPublicConfig({ PUBLISHER_APP_ENV: 'prodution' }));
});
