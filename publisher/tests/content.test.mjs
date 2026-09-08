import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { parseMarkdown } from '../lib/markdown-contract.mjs';
const sample = await readFile(new URL('../content/courses/smartphone-basics/week-01.md', import.meta.url), 'utf8');
test('sample produces typed metadata', () => {
  const lesson = parseMarkdown(sample);
  assert.equal(lesson.estimatedMinutes, 40);
  assert.equal(lesson.published, true);
  assert.equal(lesson.lessonId, 'week-01');
});
test('rejects malformed publishing metadata and missing content', () => {
  for (const [before, after] of [['published: true', 'published: yes'], ['estimated_minutes: 40', 'estimated_minutes: 0'], ['lesson_id: week-01', 'lesson_id: ../private'], ['## 핵심 요약', '핵심 요약'], ['audience: senior_beginner', 'audience: senior_beginner\naudience: another']]) {
    assert.throws(() => parseMarkdown(sample.replace(before, after)));
  }
});
