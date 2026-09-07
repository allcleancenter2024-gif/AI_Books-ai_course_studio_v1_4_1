from __future__ import annotations

from collections.abc import Callable


def summarize_text(provider_manager, provider: str, text: str, progress: Callable[[int, int, str], None] | None = None) -> str:
    """Bound every model call so small local contexts cannot overflow.

    Long documents are summarized in small passes and reduced in groups of three.
    The callback reports the completed model-call count for the UI progress view.
    """
    system = "당신은 교육자료 조사·요약 보조자입니다. <SOURCE> 안의 자료에만 근거하며 숫자와 날짜를 보존합니다. 원문에 없는 내용은 만들지 마세요."
    local = provider in {"lmstudio", "ollama"}
    chunk_size = 2_400 if local else 7_000
    output_tokens = 320 if local else 650
    source = text[:120_000].strip()
    chunks = [source[i:i + chunk_size] for i in range(0, len(source), chunk_size)] or [""]
    # Upper bound used only for a stable, understandable progress bar.
    estimated_total = len(chunks) + max(1, (len(chunks) + 2) // 3) + 1
    completed = 0
    def report(message: str):
        nonlocal completed
        completed += 1
        if progress: progress(completed, estimated_total, message)
    partials = []
    for index, chunk in enumerate(chunks, 1):
        prompt = f"자료 조각 {index}/{len(chunks)}입니다. 핵심 사실, 숫자·날짜, 기능 또는 주의사항만 간결한 글머리표로 정리하세요.\n\n<SOURCE>\n{chunk}\n</SOURCE>"
        partials.append(provider_manager.generate(provider, system, prompt, max_tokens=output_tokens, temperature=.2))
        report(f"원문 조각 {index}/{len(chunks)} 요약 완료")
    round_no = 1
    while len(partials) > 1:
        next_partials = []
        groups = [partials[i:i + 3] for i in range(0, len(partials), 3)]
        for index, group in enumerate(groups, 1):
            prompt = f"요약 묶음 {index}/{len(groups)}을 중복 없이 통합하세요. 사실·수치·날짜를 보존하고, 원문에 없는 해석은 넣지 마세요.\n\n<SOURCE>\n" + "\n\n".join(group) + "\n</SOURCE>"
            next_partials.append(provider_manager.generate(provider, system, prompt, max_tokens=output_tokens, temperature=.2))
            report(f"요약 통합 {round_no}-{index}/{len(groups)} 완료")
        partials = next_partials; round_no += 1
    final_prompt = "다음 요약을 교육용으로 정리하세요. '핵심 내용 5개', '쉬운 설명', '원문 대조가 필요한 정보' 제목을 반드시 사용하고 추측하지 마세요.\n\n<SOURCE>\n" + partials[0] + "\n</SOURCE>"
    result = provider_manager.generate(provider, system, final_prompt, max_tokens=700 if local else 1_100, temperature=.2)
    report("최종 교육용 요약 작성 완료")
    return result
