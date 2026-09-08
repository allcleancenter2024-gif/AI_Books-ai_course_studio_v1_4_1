import { readdir, readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { parseMarkdown } from '../lib/markdown-contract.mjs';

const root = join(process.cwd(), 'content', 'courses');
let failures = 0;
for (const course of await readdir(root, { withFileTypes: true })) {
  if (!course.isDirectory()) continue;
  for (const file of await readdir(join(root, course.name), { withFileTypes: true })) {
    if (!file.isFile() || !file.name.endsWith('.md')) continue;
    const name = join(course.name, file.name);
    const source = await readFile(join(root, name), 'utf8');
    try {
      const lesson = parseMarkdown(source, name);
      if (lesson.courseId !== course.name || lesson.lessonId !== file.name.slice(0, -3)) throw new Error(`${name}: ID와 파일 경로가 다릅니다.`);
    } catch (error) { console.error(error.message); failures++; }
  }
}
if (failures) process.exit(1);
console.log('콘텐츠 스키마 검사 통과');
