"""Visual assets remain optional metadata plus local files, never lesson JSON blobs."""
import asyncio
from io import BytesIO
import json

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from starlette.datastructures import Headers

from studio.application import create_app
from studio.db import connect
from studio.services.asset_service import add_uploaded_asset, create_prompt_draft, list_visuals, remove_asset
from studio.services.publication_snapshot import publication_snapshot


def _seed_lesson(book_id: int = 9921, week: int = 1) -> None:
    create_app()
    lesson = {"week": week, "topic": "AI 첫걸음", "student": {"goals": ["AI의 기본 기능을 안전하게 연습합니다."], "story": "쉬운 설명"}, "teacher": {"teaching_goal": ["AI 기본 기능"], "deep_explanation": "강사 설명"}, "learning_design": {"objectives": ["AI 기본 기능"], "source_ids": []}, "exercises": []}
    profile = {"audience": "60대", "experience": "처음", "device_paths": ["pc_web"]}
    quality = {"publishable": True, "validation_status": "needs_review"}
    with connect() as conn:
        conn.execute("INSERT OR REPLACE INTO books(id,weeks,audience,provider,model,created_at,data_json,md_path) VALUES(?,?,?,?,?,?,?,?)", (book_id, 1, "60대", "test", "test", "2026-09-09", "{}", ""))
        conn.execute("INSERT OR REPLACE INTO lesson_units(book_id,week,audience,profile_json,content_json,qa_json,approval_status,created_at) VALUES(?,?,?,?,?,?,?,?)", (book_id, week, "60대", json.dumps(profile), json.dumps(lesson), json.dumps(quality), "pending", "2026-09-09"))


def _png_upload() -> UploadFile:
    image = Image.new("RGB", (32, 18), "navy")
    data = BytesIO(); image.save(data, format="PNG"); data.seek(0)
    return UploadFile(file=data, filename="lesson.png", headers=Headers({"content-type": "image/png"}))


def _png_with_wrong_extension() -> UploadFile:
    upload = _png_upload()
    upload.filename = "lesson.jpg"
    return upload


def test_prompt_draft_and_local_image_asset_are_optional_and_gate_publication():
    book_id, week = 9921, 1
    _seed_lesson(book_id, week)
    prompt = create_prompt_draft(book_id, week, purpose="주차 대표 이미지", style="교육용 일러스트", aspect_ratio="16:9")
    assert prompt["prompt_ko"] and prompt["prompt_en"] and prompt["review_status"] == "needs_review"
    before = list_visuals(book_id, week)
    assert before["assets"] == [] and before["checklist"]["image_present"] is False
    with pytest.raises(HTTPException, match="강사 승인"):
        publication_snapshot(book_id, week)
    with connect() as conn:
        conn.execute("UPDATE lesson_units SET approval_status='approved' WHERE book_id=? AND week=?", (book_id, week))
    assert publication_snapshot(book_id, week)["visual_assets"] == []
    asset = asyncio.run(add_uploaded_asset(book_id, week, _png_upload(), {"role": "hero", "alt_text_ko": "AI 학습 장면", "alt_text_en": "AI learning scene", "caption_ko": "", "caption_en": "", "source_type": "uploaded", "source_url": "", "creator": "", "license": "", "copyright_status": "review_required"}))
    assert asset["mime_type"] == "image/png" and asset["width"] == 32 and asset["approved"] is False
    with pytest.raises(HTTPException, match="이미지가 있는 차시"):
        publication_snapshot(book_id, week)
    remove_asset(asset["id"])
    with pytest.raises(HTTPException, match="확장자"):
        asyncio.run(add_uploaded_asset(book_id, week, _png_with_wrong_extension(), {"role": "hero", "alt_text_ko": "AI 학습 장면", "alt_text_en": "", "caption_ko": "", "caption_en": "", "source_type": "uploaded", "source_url": "", "creator": "", "license": "", "copyright_status": "review_required"}))
    with connect() as conn:
        conn.execute("DELETE FROM lesson_units WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))
