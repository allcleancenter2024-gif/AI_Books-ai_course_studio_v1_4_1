from typing import Optional, Literal
from pydantic import BaseModel, Field

LocalProvider = Literal["lmstudio", "ollama"]
BookEdition = Literal["student", "teacher", "combined"]
GenerationMode = Literal["local_only", "web_enhanced", "external_edit"]
WebScope = Literal["disabled", "official_only", "official_and_expert", "include_educational_video", "high_quality"]

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)
    remember: bool = False

class CourseRequest(BaseModel):
    weeks: int
    audience: str = "전체 초보자"

class LessonRequest(BaseModel):
    topic: str
    audience: str = "전체 초보자"

class ProviderConfigRequest(BaseModel):
    provider: LocalProvider
    model: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    timeout: Optional[float] = Field(default=None, ge=30, le=3600)

class ProviderTestRequest(BaseModel):
    provider: LocalProvider

class WeekAIRequest(BaseModel):
    provider: LocalProvider
    weeks: int = 12
    week: int = Field(ge=1, le=15)
    audience: str = "전체 초보자"
    experience: str = "처음"
    device_paths: list[str] = Field(default_factory=lambda: ["pc_web", "android_app", "ios_ipados_app"])
    source_ids: list[int] = Field(default_factory=list)
    job_id: str = ""
    edition: BookEdition = "combined"
    generation_mode: GenerationMode = "local_only"
    web_scope: WebScope = "disabled"
    freshness_days: int = Field(default=365, ge=0, le=3650)
    external_ai_allowed: bool = False
    cost_limit_usd: float = Field(default=0, ge=0, le=1000)

class WeekPartRequest(WeekAIRequest):
    part: str

class BookAIRequest(BaseModel):
    provider: LocalProvider
    weeks: int
    audience: str = "전체 초보자"
    experience: str = "처음"
    device_paths: list[str] = Field(default_factory=lambda: ["pc_web", "android_app", "ios_ipados_app"])
    start_week: int = Field(default=1, ge=1, le=15)
    end_week: Optional[int] = Field(default=None, ge=1, le=15)
    source_ids: list[int] = Field(default_factory=list)
    job_id: str = ""
    edition: BookEdition = "combined"
    generation_mode: GenerationMode = "local_only"
    web_scope: WebScope = "disabled"
    freshness_days: int = Field(default=365, ge=0, le=3650)
    external_ai_allowed: bool = False
    cost_limit_usd: float = Field(default=0, ge=0, le=1000)

class HybridEvaluateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    audience: str = Field(default="전체 초보자", max_length=100)
    source_ids: list[int] = Field(default_factory=list)

class HybridSearchRequest(HybridEvaluateRequest):
    generation_mode: GenerationMode = "web_enhanced"
    web_scope: WebScope = "official_only"
    max_results: int = Field(default=8, ge=1, le=20)
    freshness_days: int = Field(default=365, ge=0, le=3650)

class WebSourceRequest(BaseModel):
    url: str
    title: str = ""

class VideoSourceRequest(BaseModel):
    url: str
    title: str = ""

class SourceSummaryRequest(BaseModel):
    source_id: int
    provider: LocalProvider
    job_id: str = ""

class SourceIdsRequest(BaseModel):
    source_ids: list[int] = Field(default_factory=list)

class LessonApprovalRequest(BaseModel):
    approved: bool
    reviewer: str = "강사"
    note: str = ""

class ImagePromptDraftRequest(BaseModel):
    purpose: str = Field(default="주차 대표 이미지", min_length=1, max_length=100)
    style: str = Field(default="따뜻한 교육용 플랫 일러스트", min_length=1, max_length=160)
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|4:3|1:1)$")

class ImagePromptApprovalRequest(BaseModel):
    approved: bool

class VisualAssetMetadataRequest(BaseModel):
    role: str = Field(default="hero", pattern=r"^(hero|concept|step|example|comparison|warning|summary|thumbnail)$")
    alt_text_ko: str = Field(min_length=1, max_length=500)
    alt_text_en: str = Field(default="", max_length=500)
    caption_ko: str = Field(default="", max_length=500)
    caption_en: str = Field(default="", max_length=500)
    source_type: str = Field(default="uploaded", pattern=r"^(uploaded|ai_generated|licensed|public_domain)$")
    source_url: str = Field(default="", max_length=1000)
    creator: str = Field(default="", max_length=200)
    license: str = Field(default="", max_length=200)
    copyright_status: str = Field(default="review_required", pattern=r"^(review_required|cleared|restricted)$")

class ManualPDFChapter(BaseModel):
    index: int = Field(ge=1, le=100)
    category: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=500)
    text: str = Field(min_length=1, max_length=30_000)

class ManualPDFRequest(BaseModel):
    title: str = Field(default="AI 강의 활용 Studio 설치 및 운영 설명서", max_length=200)
    chapters: list[ManualPDFChapter] = Field(min_length=1, max_length=100)

class ExternalEditRequest(BaseModel):
    book_id: int = Field(ge=1)
    instruction: str = Field(min_length=1, max_length=4000)
    consent: bool = False
    cost_limit_usd: float = Field(gt=0, le=1000)
