import { promises as fs } from 'node:fs';
import path from 'node:path';
import { cache } from 'react';
import { parseMarkdown } from './markdown-contract.mjs';
import type { Lesson } from './markdown-contract.mjs';
export type { Lesson } from './markdown-contract.mjs';

const coursesRoot = path.join(process.cwd(), 'content', 'courses');

export const getLessons = cache(async (): Promise<Lesson[]> => {
  const courseDirectories = await fs.readdir(coursesRoot, { withFileTypes: true });
  const nested = await Promise.all(courseDirectories.filter(e => e.isDirectory()).map(async course => {
    const directory = path.join(coursesRoot, course.name);
    const files = await fs.readdir(directory, { withFileTypes: true });
    return Promise.all(files.filter(e => e.isFile() && e.name.endsWith('.md')).map(async file => {
      const source = path.join(directory, file.name);
      const lesson = parseMarkdown(await fs.readFile(source, 'utf8'), source);
      if (lesson.courseId !== course.name || lesson.lessonId !== path.basename(file.name, '.md')) {
        throw new Error('Markdown ID and file path mismatch');
      }
      return lesson;
    }));
  }));
  return nested.flat().filter(e => e.published).sort((a,b) => a.courseId.localeCompare(b.courseId) || a.lessonId.localeCompare(b.lessonId));
});

export async function getLesson(courseId: string, lessonId: string) {
  return (await getLessons()).find(e => e.courseId === courseId && e.lessonId === lessonId);
}
