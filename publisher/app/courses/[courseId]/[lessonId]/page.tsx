import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getLesson, getLessons } from '../../../../lib/content';

type Props = { params: Promise<{ courseId: string; lessonId: string }> };
export const dynamicParams = false;

export async function generateStaticParams() {
  const lessons = await getLessons();
  return lessons.map(({ courseId, lessonId }) => ({ courseId, lessonId }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { courseId, lessonId } = await params;
  const lesson = await getLesson(courseId, lessonId);
  return lesson ? { title: lesson.title, description: lesson.description } : {};
}

export default async function LessonPage({ params }: Props) {
  const { courseId, lessonId } = await params;
  const lesson = await getLesson(courseId, lessonId);
  if (!lesson) notFound();
  return <main className="lesson-shell">
    <header className="site-header"><Link href="/" className="brand">느린 배움 교재</Link><Link href="/" className="back-link">교재 목록</Link></header>
    <article className="lesson">
      <p className="kicker">{lesson.courseId} · {lesson.estimatedMinutes}분</p>
      <h1>{lesson.title}</h1>
      <p className="lead">{lesson.description}</p>
      <aside className="objective-card" aria-labelledby="objective-title"><h2 id="objective-title">이번 시간에 할 수 있는 일</h2><ul>{lesson.learningObjectives.map((objective) => <li key={objective}>{objective}</li>)}</ul></aside>
      <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{lesson.body}</ReactMarkdown></div>
    </article>
  </main>;
}
