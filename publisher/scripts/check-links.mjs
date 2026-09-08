import { access, readdir, readFile } from 'node:fs/promises';
import { constants } from 'node:fs';
import { dirname, join, resolve } from 'node:path';

const root = join(process.cwd(), 'content', 'courses');
let failures = 0;
for (const course of await readdir(root, { withFileTypes: true })) {
  if (!course.isDirectory()) continue;
  const directory = join(root, course.name);
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (!entry.isFile() || !entry.name.endsWith('.md')) continue;
    const file = join(directory, entry.name);
    const source = await readFile(file, 'utf8');
    for (const [, href] of source.matchAll(/\[[^\]]+\]\(([^)]+)\)/g)) {
      if (/^(https?:|mailto:|#)/.test(href)) continue;
      try { await access(resolve(dirname(file), href.split('#')[0]), constants.F_OK); }
      catch { console.error(`${file}: 존재하지 않는 상대 링크 ${href}`); failures++; }
    }
  }
}
if (failures) process.exit(1);
console.log('상대 링크 검사 통과');
