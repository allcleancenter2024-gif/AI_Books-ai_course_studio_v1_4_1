// Deliberately limited front matter grammar: scalar keys and two-space lists.
// Unsupported YAML must fail rather than silently change the published content.
export function parseMarkdown(raw, source = 'Markdown') {
  const fail = message => { throw new Error(`${source}: ${message}`); };
  const match = raw.replace(/^\uFEFF/, '').match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (!match) fail('front matter가 필요합니다.');
  const data = Object.create(null);
  let list;
  for (const line of match[1].split(/\r?\n/)) {
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const item = line.match(/^  - (.+)$/);
    if (item && list) { data[list].push(item[1].trim()); continue; }
    const entry = line.match(/^([a-z_]+):\s*(.*)$/);
    if (!entry) fail('지원하지 않는 front matter 문법입니다.');
    const [, key, value] = entry;
    if (Object.hasOwn(data, key)) fail(`중복 필드: ${key}`);
    list = value ? undefined : key;
    data[key] = value ? value.replace(/^(["'])(.*)\1$/, '$2') : [];
  }
  for (const key of ['course_id', 'lesson_id', 'title', 'audience']) {
    if (typeof data[key] !== 'string' || !data[key].trim()) fail(`${key} 값이 필요합니다.`);
  }
  for (const key of ['course_id', 'lesson_id']) if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(data[key])) fail(`${key}는 영문 소문자·숫자·하이픈을 사용합니다.`);
  if (!['true', 'false'].includes(data.published)) fail('published는 true 또는 false여야 합니다.');
  if (!/^\d+$/.test(data.estimated_minutes) || Number(data.estimated_minutes) < 1 || Number(data.estimated_minutes) > 1440) fail('estimated_minutes는 1~1440 정수여야 합니다.');
  if (!Array.isArray(data.learning_objectives) || !data.learning_objectives.length) fail('학습 목표가 필요합니다.');
  const body = match[2].trim();
  const prose = body.replace(/^```[^\n]*\n[\s\S]*?^```\s*$/gm, '');
  for (const heading of ['학습 목표', '핵심 내용', '단계별 실습', '핵심 요약']) {
    if (!prose.split(/\r?\n/).some(line => line.trimEnd() === `## ${heading}`)) fail(`${heading} 제목이 필요합니다.`);
  }
  return { courseId: data.course_id, lessonId: data.lesson_id, title: data.title,
    audience: data.audience, learningObjectives: data.learning_objectives,
    estimatedMinutes: Number(data.estimated_minutes), published: data.published === 'true',
    description: typeof data.description === 'string' ? data.description : '', body };
}
