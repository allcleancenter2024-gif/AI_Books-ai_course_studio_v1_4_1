from studio.services.source_service import _insert, delete_source
from studio.services.vector_index import retrieve


def test_retrieval_exposes_hybrid_attribution_and_lexical_signal():
    source = _insert("file", "하이브리드 자료", "hybrid.txt", text="AI 교육 실습 단계와 검증 방법을 설명합니다.")
    try:
        rows = retrieve([source["id"]], "AI 실습 검증", max_total=4000, per_source=2000)
        assert rows
        assert rows[0]["retrieval_type"] == "hybrid_rrf"
        assert rows[0]["source_name"] == "하이브리드 자료"
        assert isinstance(rows[0]["score"], float)
        assert "하이브리드 자료" in rows[0]["text"]
    finally:
        delete_source(source["id"])
