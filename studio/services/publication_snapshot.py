"""Build the only Studio-to-Publisher handoff shape; Publisher never opens SQLite."""
from __future__ import annotations

from fastapi import HTTPException

from .asset_service import list_visuals
from .education_quality import load_lesson_unit


def publication_snapshot(book_id: int, week: int) -> dict:
    record = load_lesson_unit(book_id, week)
    if not record:
        raise HTTPException(404, "출판 스냅샷을 만들 주차 교재를 찾을 수 없습니다.")
    quality = record["qa"]
    if record["approval_status"] != "approved" or not quality.get("publishable"):
        raise HTTPException(409, "강사 승인과 품질 검사를 통과한 차시만 출판 스냅샷을 만들 수 있습니다.")
    visuals = list_visuals(book_id, week)
    checklist = visuals["checklist"]
    if visuals["assets"] and not (checklist["alt_complete"] and checklist["copyright_cleared"] and checklist["asset_approved"]):
        raise HTTPException(409, "이미지가 있는 차시는 ALT, 저작권, 이미지 승인을 완료해야 출판할 수 있습니다.")
    content = record["content"]
    return {
        "snapshot_version": 1,
        "book_id": book_id,
        "week": week,
        "audience": record["audience"],
        "profile": record["profile"],
        "content": {key: content.get(key) for key in ("week", "topic", "student", "teacher", "learning_design", "prompt_examples", "exercises")},
        "visual_assets": [{key: asset.get(key) for key in ("id", "role", "mime_type", "width", "height", "aspect_ratio", "alt_text_ko", "alt_text_en", "caption_ko", "caption_en", "source_type", "license", "copyright_status")} for asset in visuals["assets"]],
        "publication": {"quality": quality, "approval_status": record["approval_status"], "visual_checklist": checklist},
    }
