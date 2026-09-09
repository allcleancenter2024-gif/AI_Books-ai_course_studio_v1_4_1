"""Optional visual-asset boundary for lesson preview; image bytes never enter SQLite."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from ..config import ASSETS_DIR, MAX_IMAGE_ASSET_BYTES
from ..db import connect
from .education_quality import load_lesson_unit

ALLOWED_IMAGE_TYPES = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"), "WEBP": ("image/webp", ".webp")}
ASSET_ROLES = {"hero", "concept", "step", "example", "comparison", "warning", "summary", "thumbnail"}


@dataclass(frozen=True)
class StoredAsset:
    storage_key: str
    mime_type: str
    width: int
    height: int
    checksum: str


class AssetStorage(Protocol):
    def store(self, *, book_id: int, week: int, asset_id: str, extension: str, data: bytes, mime_type: str, width: int, height: int) -> StoredAsset: ...
    def remove(self, storage_key: str) -> None: ...
    def resolve(self, storage_key: str) -> Path: ...


class LocalStorageAdapter:
    """Runtime-local implementation; MinIO can later implement AssetStorage unchanged."""

    def store(self, *, book_id: int, week: int, asset_id: str, extension: str, data: bytes, mime_type: str, width: int, height: int) -> StoredAsset:
        relative = Path("courses") / str(book_id) / f"week-{week}" / f"{asset_id}{extension}"
        target = (ASSETS_DIR / relative).resolve()
        if ASSETS_DIR.resolve() not in target.parents:
            raise HTTPException(400, "안전하지 않은 이미지 저장 경로입니다.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredAsset(str(relative).replace("\\", "/"), mime_type, width, height, sha256(data).hexdigest())

    def resolve(self, storage_key: str) -> Path:
        target = (ASSETS_DIR / Path(storage_key).name if "/" not in storage_key else ASSETS_DIR / storage_key).resolve()
        if ASSETS_DIR.resolve() not in target.parents or not target.is_file():
            raise HTTPException(404, "이미지 파일을 찾을 수 없습니다.")
        return target

    def remove(self, storage_key: str) -> None:
        try:
            self.resolve(storage_key).unlink(missing_ok=True)
        except HTTPException:
            pass


storage: AssetStorage = LocalStorageAdapter()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _lesson(book_id: int, week: int) -> dict:
    record = load_lesson_unit(book_id, week)
    if not record:
        raise HTTPException(404, "이미지를 연결할 주차 교재를 찾을 수 없습니다.")
    return record


def _aspect_ratio(width: int, height: int) -> str:
    ratio = width / max(height, 1)
    return min((("16:9", 16 / 9), ("4:3", 4 / 3), ("1:1", 1)), key=lambda item: abs(item[1] - ratio))[0]


def _row(row) -> dict:
    value = dict(row)
    value["approved"] = bool(value["approved"])
    return value


def list_visuals(book_id: int, week: int) -> dict:
    _lesson(book_id, week)
    with connect() as conn:
        assets = [_row(row) for row in conn.execute("SELECT * FROM visual_assets WHERE book_id=? AND week=? ORDER BY created_at", (book_id, week))]
        prompts = [dict(row) for row in conn.execute("SELECT * FROM image_prompts WHERE book_id=? AND week=? ORDER BY created_at", (book_id, week))]
    for asset in assets:
        asset["file_url"] = f"/api/visual-assets/{asset['id']}/file"
    return {"assets": assets, "prompts": prompts, "checklist": visual_checklist(assets, prompts)}


def visual_checklist(assets: list[dict], prompts: list[dict]) -> dict:
    meaningful = [asset for asset in assets if asset["role"] != "thumbnail"]
    return {
        "image_present": bool(meaningful),
        "alt_complete": all(asset.get("alt_text_ko", "").strip() for asset in meaningful),
        "copyright_cleared": all(asset.get("copyright_status") == "cleared" for asset in meaningful),
        "prompt_ko": bool(prompts and all(prompt.get("prompt_ko", "").strip() for prompt in prompts)),
        "prompt_en": bool(prompts and all(prompt.get("prompt_en", "").strip() for prompt in prompts)),
        "prompt_reviewed": bool(prompts) and all(prompt.get("review_status") == "approved" for prompt in prompts),
        "asset_approved": bool(meaningful) and all(asset.get("approved") for asset in meaningful),
    }


async def add_uploaded_asset(book_id: int, week: int, upload: UploadFile, metadata: dict) -> dict:
    _lesson(book_id, week)
    if metadata["role"] not in ASSET_ROLES:
        raise HTTPException(422, "지원하지 않는 이미지 역할입니다.")
    data = await upload.read(MAX_IMAGE_ASSET_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_ASSET_BYTES:
        raise HTTPException(413, "이미지는 12MB 이하의 JPG, PNG 또는 WEBP 파일이어야 합니다.")
    try:
        image = Image.open(BytesIO(data))
        image.verify()
        image = Image.open(BytesIO(data))
        image_format = image.format or ""
        width, height = image.size
    except (UnidentifiedImageError, OSError):
        raise HTTPException(415, "손상되었거나 지원하지 않는 이미지 파일입니다.") from None
    if image_format not in ALLOWED_IMAGE_TYPES or width < 1 or height < 1 or width * height > 30_000_000:
        raise HTTPException(415, "JPG, PNG, WEBP 형식과 안전한 이미지 크기만 지원합니다.")
    mime_type, extension = ALLOWED_IMAGE_TYPES[image_format]
    declared = (upload.content_type or "").lower()
    if declared and declared not in {mime_type, "application/octet-stream"}:
        raise HTTPException(415, "파일 확장자와 MIME 유형이 일치하지 않습니다.")
    asset_id = f"asset_{uuid4().hex}"
    stored = storage.store(book_id=book_id, week=week, asset_id=asset_id, extension=extension, data=data, mime_type=mime_type, width=width, height=height)
    try:
        with connect() as conn:
            conn.execute("""INSERT INTO visual_assets(id,book_id,week,role,storage_key,original_name,mime_type,width,height,aspect_ratio,alt_text_ko,alt_text_en,caption_ko,caption_en,source_type,source_url,creator,license,copyright_status,checksum,approved,created_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         (asset_id, book_id, week, metadata["role"], stored.storage_key, Path(upload.filename or "image").name[:140], stored.mime_type, stored.width, stored.height, _aspect_ratio(stored.width, stored.height), metadata["alt_text_ko"].strip(), metadata.get("alt_text_en", "").strip(), metadata.get("caption_ko", "").strip(), metadata.get("caption_en", "").strip(), metadata["source_type"], metadata.get("source_url", "").strip(), metadata.get("creator", "").strip(), metadata.get("license", "").strip(), metadata["copyright_status"], stored.checksum, 0, _now()))
    except Exception:
        storage.remove(stored.storage_key)
        raise
    return get_asset(asset_id)


def get_asset(asset_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM visual_assets WHERE id=?", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "이미지 자산을 찾을 수 없습니다.")
    asset = _row(row)
    asset["file_url"] = f"/api/visual-assets/{asset_id}/file"
    return asset


def remove_asset(asset_id: str) -> None:
    asset = get_asset(asset_id)
    with connect() as conn:
        conn.execute("DELETE FROM visual_assets WHERE id=?", (asset_id,))
    storage.remove(asset["storage_key"])


def asset_file(asset_id: str) -> tuple[dict, Path]:
    asset = get_asset(asset_id)
    return asset, storage.resolve(asset["storage_key"])


def create_prompt_draft(book_id: int, week: int, *, purpose: str, style: str, aspect_ratio: str) -> dict:
    record = _lesson(book_id, week)
    content, profile = record["content"], record["profile"]
    topic = str(content.get("topic") or f"{week}주차 AI 학습")
    goals = content.get("student", {}).get("goals") or content.get("learning_design", {}).get("objectives") or []
    goal = str(goals[0]) if goals else "핵심 개념을 안전하게 직접 연습하기"
    audience = str(profile.get("audience") or "AI 초보 학습자")
    prompt_ko = f"{audience} 학습자가 {topic}을(를) 배우는 장면. {goal}을 자연스럽게 보여준다. {style}, 명확한 인물 동작, 복잡하지 않은 배경, {aspect_ratio} 구성. 실제 회사 로고, 상표, 읽을 수 있는 UI 글자, 개인정보, 과도하게 미래적인 로봇은 포함하지 않는다."
    prompt_en = f"A warm educational illustration of {audience} learners studying {topic}. Show {goal} through clear, natural actions. {style}, simple uncluttered background, {aspect_ratio} composition. No real company logos, trademarks, readable interface text, personal information, or overly futuristic robots."
    prompt_id = f"prompt_{uuid4().hex}"
    with connect() as conn:
        conn.execute("""INSERT INTO image_prompts(id,book_id,week,asset_id,purpose,prompt_ko,prompt_en,negative_prompt_ko,negative_prompt_en,style,aspect_ratio,audience,generation_status,review_status,prompt_source_language,translation_status,created_by,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                     (prompt_id, book_id, week, None, purpose, prompt_ko, prompt_en, "로고, 상표, 읽을 수 있는 UI 글자, 개인정보, 과도하게 미래적인 로봇", "logos, trademarks, readable interface text, personal information, overly futuristic robots", style, aspect_ratio, audience, "prompt_only", "needs_review", "ko_en", "draft", "studio_template", _now()))
    return get_prompt(prompt_id)


def get_prompt(prompt_id: str) -> dict:
    with connect() as conn:
        row = conn.execute("SELECT * FROM image_prompts WHERE id=?", (prompt_id,)).fetchone()
    if not row:
        raise HTTPException(404, "이미지 프롬프트를 찾을 수 없습니다.")
    return dict(row)


def set_prompt_approval(prompt_id: str, approved: bool) -> dict:
    with connect() as conn:
        result = conn.execute("UPDATE image_prompts SET review_status=?, approved_at=? WHERE id=?", ("approved" if approved else "needs_review", _now() if approved else None, prompt_id))
        if not result.rowcount:
            raise HTTPException(404, "이미지 프롬프트를 찾을 수 없습니다.")
    return get_prompt(prompt_id)
