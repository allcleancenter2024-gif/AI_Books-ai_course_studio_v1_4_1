import Link from 'next/link';
import { getLessons } from '../lib/content';

export default async function Home() {
  const lessons = await getLessons();
  return <main className="shell">
    <header className="site-header"><Link href="/" className="brand">느린 배움 교재</Link><span>차분하게, 한 단계씩</span></header>
    <section className="welcome" aria-labelledby="welcome-title">
      <p className="kicker">시니어 친화형 디지털 학습</p>
      <h1 id="welcome-title">오늘 배울 한 가지를<br />천천히 시작해 보세요.</h1>
      <p>큰 글씨와 충분한 여백, 따라 하기 쉬운 순서로 구성한 웹 교재입니다.</p>
    </section>
    <section aria-labelledby="course-list-title">
      <h2 id="course-list-title">학습할 교재</h2>
      <div className="lesson-grid">
        {lessons.map((lesson) => <article className="lesson-card" key={`${lesson.courseId}-${lesson.lessonId}`}>
          <p className="card-meta">약 {lesson.estimatedMinutes}분 · {lesson.audience === 'senior_beginner' ? '처음 배우는 분' : lesson.audience}</p>
          <h3>{lesson.title}</h3>
          <p>{lesson.description}</p>
          <Link className="card-link" href={`/courses/${lesson.courseId}/${lesson.lessonId}`}>교재 시작하기</Link>
        </article>)}
      </div>
    </section>
  </main>;
}
