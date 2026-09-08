export type Lesson = {
  courseId: string; lessonId: string; title: string; audience: string;
  learningObjectives: string[]; estimatedMinutes: number; published: boolean;
  description: string; body: string;
};
export function parseMarkdown(raw: string, source?: string): Lesson;
