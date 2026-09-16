import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
# Server environment variables always win; .env only fills missing values.
load_dotenv(PROJECT_DIR / ".env", override=False)

# Versioning policy: patch for small fixes (v1.4.1 -> v1.4.2), minor for
# substantial user-facing changes (v1.4.1 -> v1.5.0).
VERSION = "1.29.0"
LAST_UPDATED = "2026-09-16"
APP_TITLE = f"AI 강의 활용 Studio v{VERSION} [{LAST_UPDATED}]"
BASE_DIR = PROJECT_DIR


def _env_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, "true" if default else "false").strip().lower() in {"1", "true", "yes", "on"}


def _bounded_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


# Configuration is deliberately local-first.  A public gateway is a later,
# separate deployment concern; changing these values never exposes Docker or
# provider services.
APP_ENV = os.getenv("APP_ENV", "development").strip().lower() or "development"
if APP_ENV not in {"development", "test", "staging", "production"}:
    raise ValueError("APP_ENV must be development, test, staging, or production")
APP_HOST = os.getenv("APP_HOST", "127.0.0.1").strip() or "127.0.0.1"
APP_PORT = _bounded_int("APP_PORT", 8765, 1, 65535)
APP_BASE_URL = f"http://{APP_HOST}:{APP_PORT}"
PUBLIC_ACCESS = _env_flag("PUBLIC_ACCESS", False)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").strip()
AUDIT_SAFE_MODE = _env_flag("AI_COURSE_STUDIO_AUDIT_SAFE_MODE", False)
# The learning/update surfaces are part of the shipped Studio workflow. An
# operator can still disable them explicitly for a constrained deployment.
FEATURE_AI_TOOL_LEARNING_CENTER = _env_flag("FEATURE_AI_TOOL_LEARNING_CENTER", True)

# SQLite remains the authoritative Studio store in this release.  The Docker
# PostgreSQL/MongoDB stack is optional replication/integration infrastructure,
# not a fallback or an automatic promotion target.
DATA_STORE_ROLE = "sqlite-authoritative"
# Keep production data in the project by default. Tests and isolated runs can
# set this path before importing the application, without touching user data.
RUNTIME_DIR = Path(os.getenv("AI_COURSE_STUDIO_RUNTIME_DIR", str(BASE_DIR))).resolve()
DB_PATH = RUNTIME_DIR / "data" / "studio.db"
RDBMS_NAME = "SQLite 3"
RDBMS_ROLE = "기본 실행·저장소"
EXPORTS_DIR = RUNTIME_DIR / "exports"
BOOK_EXPORTS_DIR = EXPORTS_DIR / "books"
LOGS_DIR = RUNTIME_DIR / "logs"
STATIC_DIR = BASE_DIR / "static"
UPLOADS_DIR = RUNTIME_DIR / "uploads"
ASSETS_DIR = RUNTIME_DIR / "assets"
SOURCE_PACKS_DIR = EXPORTS_DIR / "source_packs"
SUMMARY_EXPORTS_DIR = EXPORTS_DIR / "summaries"
PDF_OUTPUT_DIR = RUNTIME_DIR / "output" / "pdf"
MAX_UPLOAD_BYTES = _bounded_int("MAX_UPLOAD_SIZE_MB", 500, 1, 500) * 1024 * 1024
MAX_IMAGE_ASSET_BYTES = _bounded_int("MAX_IMAGE_ASSET_SIZE_MB", 12, 1, 20) * 1024 * 1024
UPLOAD_CHUNK_BYTES = _bounded_int("UPLOAD_CHUNK_SIZE_MB", 1, 1, 16) * 1024 * 1024
EXTRACTED_TEXT_LIMIT = 120_000
# Summary calls are deliberately bounded: a single worker protects local
# models and a small queue prevents unbounded thread/memory growth when
# several browser tabs submit large documents at once.
def _safe_limit(name: str, default: int, minimum: int, maximum: int) -> int:
    return _bounded_int(name, default, minimum, maximum)


SUMMARY_MAX_CONCURRENT = _safe_limit("AI_COURSE_STUDIO_SUMMARY_MAX_CONCURRENT", 1, 1, 2)
SUMMARY_QUEUE_LIMIT = _safe_limit("AI_COURSE_STUDIO_SUMMARY_QUEUE_LIMIT", 2, 0, 4)
BOOK_GENERATION_MAX_CONCURRENT = 1
BOOK_GENERATION_QUEUE_LIMIT = _safe_limit("AI_COURSE_STUDIO_BOOK_GENERATION_QUEUE_LIMIT", 2, 0, 4)
UPLOAD_PARSE_MAX_CONCURRENT = _safe_limit("AI_COURSE_STUDIO_UPLOAD_PARSE_MAX_CONCURRENT", 1, 1, 2)
UPLOAD_PARSE_QUEUE_LIMIT = _safe_limit("AI_COURSE_STUDIO_UPLOAD_PARSE_QUEUE_LIMIT", 2, 0, 4)
UPLOAD_STAGING_RETENTION_SECONDS = _bounded_int("AI_COURSE_STUDIO_UPLOAD_STAGING_RETENTION_SECONDS", 24 * 60 * 60, 300, 7 * 24 * 60 * 60)
AUTH_COOKIE_SECURE = _env_flag("AI_COURSE_STUDIO_COOKIE_SECURE", False)

# Provider endpoints stay host-local by default.  These values are consumed by
# the provider boundary, never by browser JavaScript.
OLLAMA_ENABLED = _env_flag("OLLAMA_ENABLED", True)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1").strip().rstrip("/")
OLLAMA_TIMEOUT_SECONDS = _bounded_int("OLLAMA_TIMEOUT_SECONDS", 900, 30, 900)
LMSTUDIO_ENABLED = _env_flag("LMSTUDIO_ENABLED", True)
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:12345/v1").strip().rstrip("/")
LMSTUDIO_TIMEOUT_SECONDS = _bounded_int("LMSTUDIO_TIMEOUT_SECONDS", 180, 30, 600)
# Local model requests are deliberately serialized. Raising concurrency is not
# an environment option until measured host memory/VRAM capacity is reviewed.
LMSTUDIO_MAX_PARALLEL_CALLS = 1
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "auto").strip().lower() or "auto"
WEB_SEARCH_ENABLED = _env_flag("WEB_SEARCH_ENABLED", True)
WEB_SEARCH_PROVIDER = os.getenv("AI_COURSE_STUDIO_WEB_SEARCH_PROVIDER", "searxng").strip().lower() or "searxng"
WEB_SEARCH_TIMEOUT_SECONDS = _bounded_int("SEARXNG_TIMEOUT_SECONDS", _bounded_int("AI_COURSE_STUDIO_WEB_SEARCH_TIMEOUT", 15, 1, 60), 1, 60)
WEB_SEARCH_CACHE_MAX_ENTRIES = _bounded_int("SEARXNG_CACHE_MAX_ENTRIES", 256, 16, 1024)
LOCAL_WEB_EXTRACTOR_MAX_BYTES = _bounded_int("LOCAL_WEB_EXTRACTOR_MAX_BYTES", 8 * 1024 * 1024, 1024, 32 * 1024 * 1024)
LOCAL_WEB_EXTRACTOR_MAX_TEXT_CHARS = _bounded_int("LOCAL_WEB_EXTRACTOR_MAX_TEXT_CHARS", 120_000, 1_000, 500_000)
LOCAL_WEB_EXTRACTOR_TIMEOUT_SECONDS = _bounded_int("LOCAL_WEB_EXTRACTOR_TIMEOUT_SECONDS", WEB_SEARCH_TIMEOUT_SECONDS, 1, 60)

# Optional agent orchestration. Hermes is deliberately separate from the LLM
# provider gateway and disabled unless an operator explicitly enables it.
SCHEDULER_OWNER = os.getenv("SCHEDULER_OWNER", "STUDIO").strip().upper() or "STUDIO"
HERMES_CRON_ENABLED = _env_flag("HERMES_CRON_ENABLED", False)
HERMES_ENABLED = _env_flag("HERMES_ENABLED", False)
HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "").strip().rstrip("/")
HERMES_API_KEY = os.getenv("HERMES_API_KEY", "").strip()
HERMES_HEALTH_TIMEOUT_SECONDS = _bounded_int("HERMES_HEALTH_TIMEOUT_SECONDS", 3, 1, 15)
HERMES_TASK_TIMEOUT_SECONDS = _bounded_int("HERMES_TASK_TIMEOUT_SECONDS", 300, 30, 3600)
HERMES_WEEKLY_SUMMARY_TIMEOUT_SECONDS = _bounded_int("HERMES_WEEKLY_SUMMARY_TIMEOUT_SECONDS", 180, 120, 300)
# These limits are used only by the Studio-owned weekly summary contract.  They
# do not alter generic Hermes tasks or the selected Hermes model/profile.
HERMES_WEEKLY_SOURCE_CHAR_LIMIT = _bounded_int("HERMES_WEEKLY_SOURCE_CHAR_LIMIT", 900, 400, 3000)
HERMES_WEEKLY_OUTPUT_CHAR_LIMIT = _bounded_int("HERMES_WEEKLY_OUTPUT_CHAR_LIMIT", 600, 200, 1200)
HERMES_ALLOW_WRITE = _env_flag("HERMES_ALLOW_WRITE", False)
HERMES_ALLOW_BROWSER = _env_flag("HERMES_ALLOW_BROWSER", False)
HERMES_ALLOW_TERMINAL = _env_flag("HERMES_ALLOW_TERMINAL", False)
HERMES_ALLOW_CRON = _env_flag("HERMES_ALLOW_CRON", False)
HERMES_ALLOW_MCP = _env_flag("HERMES_ALLOW_MCP", False)
HERMES_ALLOW_BOT_MODE = _env_flag("HERMES_ALLOW_BOT_MODE", False)
HERMES_ALLOW_WEBHOOK = _env_flag("HERMES_ALLOW_WEBHOOK", False)
HERMES_PROFILE = os.getenv("HERMES_PROFILE", "studio").strip() or "studio"
HERMES_VERSION = os.getenv("HERMES_VERSION", "0.17.0").strip() or "0.17.0"


def configuration_summary() -> dict[str, object]:
    """Safe, secret-free configuration facts for diagnostics and tests."""
    return {
        "app_env": APP_ENV,
        "app_host": APP_HOST,
        "app_port": APP_PORT,
        "app_base_url": APP_BASE_URL,
        "public_access": PUBLIC_ACCESS,
        "audit_safe_mode": AUDIT_SAFE_MODE,
        "feature_ai_tool_learning_center": FEATURE_AI_TOOL_LEARNING_CENTER,
        "runtime_dir": str(RUNTIME_DIR),
        "data_store_role": DATA_STORE_ROLE,
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_image_asset_bytes": MAX_IMAGE_ASSET_BYTES,
        "upload_parse_max_concurrent": UPLOAD_PARSE_MAX_CONCURRENT,
        "upload_parse_queue_limit": UPLOAD_PARSE_QUEUE_LIMIT,
        "upload_staging_retention_seconds": UPLOAD_STAGING_RETENTION_SECONDS,
        "ollama_enabled": OLLAMA_ENABLED,
        "lmstudio_enabled": LMSTUDIO_ENABLED,
        "ollama_timeout_seconds": OLLAMA_TIMEOUT_SECONDS,
        "lmstudio_timeout_seconds": LMSTUDIO_TIMEOUT_SECONDS,
        "lmstudio_max_parallel_calls": LMSTUDIO_MAX_PARALLEL_CALLS,
        "book_generation_max_concurrent": BOOK_GENERATION_MAX_CONCURRENT,
        "book_generation_queue_limit": BOOK_GENERATION_QUEUE_LIMIT,
        "web_search_enabled": WEB_SEARCH_ENABLED,
        "web_search_timeout_seconds": WEB_SEARCH_TIMEOUT_SECONDS,
        "scheduler_owner": SCHEDULER_OWNER,
        "hermes_cron_enabled": HERMES_CRON_ENABLED,
        "hermes_enabled": HERMES_ENABLED,
        "hermes_health_timeout_seconds": HERMES_HEALTH_TIMEOUT_SECONDS,
        "hermes_task_timeout_seconds": HERMES_TASK_TIMEOUT_SECONDS,
        "hermes_weekly_summary_timeout_seconds": HERMES_WEEKLY_SUMMARY_TIMEOUT_SECONDS,
        "hermes_weekly_source_char_limit": HERMES_WEEKLY_SOURCE_CHAR_LIMIT,
        "hermes_weekly_output_char_limit": HERMES_WEEKLY_OUTPUT_CHAR_LIMIT,
        "hermes_allow_write": HERMES_ALLOW_WRITE,
    }


def configuration_issues() -> list[str]:
    """Return deployment errors without ever including secret values."""
    issues: list[str] = []
    if PUBLIC_ACCESS and not PUBLIC_BASE_URL.startswith("https://"):
        issues.append("PUBLIC_ACCESS requires an HTTPS PUBLIC_BASE_URL")
    if APP_ENV == "production" and not AUTH_COOKIE_SECURE:
        issues.append("production requires AI_COURSE_STUDIO_COOKIE_SECURE=1")
    if APP_ENV == "test" and RUNTIME_DIR == BASE_DIR:
        issues.append("test runtime must not use the project runtime directory")
    if SCHEDULER_OWNER != "STUDIO":
        issues.append("SCHEDULER_OWNER must be STUDIO")
    if HERMES_CRON_ENABLED or HERMES_ALLOW_CRON:
        issues.append("Hermes Cron must remain disabled; Studio owns scheduling")
    if HERMES_ENABLED and not HERMES_BASE_URL.startswith(("http://", "https://")):
        issues.append("HERMES_ENABLED requires an HTTP(S) HERMES_BASE_URL")
    if HERMES_ENABLED and not HERMES_API_KEY:
        issues.append("HERMES_ENABLED requires HERMES_API_KEY")
    return issues


def web_search_configuration() -> dict[str, object]:
    """Read the non-secret web-search settings at provider construction time.

    Web search providers are intentionally created per job/request.  Reading
    these values here keeps the central validation rules while allowing tests
    and an operator's next request to use an updated environment without a
    process restart.  Credentials remain outside this helper.
    """
    timeout = _bounded_int(
        "SEARXNG_TIMEOUT_SECONDS",
        _bounded_int("AI_COURSE_STUDIO_WEB_SEARCH_TIMEOUT", 15, 1, 60),
        1,
        60,
    )
    return {
        "enabled": _env_flag("WEB_SEARCH_ENABLED", True),
        "provider": os.getenv("AI_COURSE_STUDIO_WEB_SEARCH_PROVIDER", "searxng").strip().lower() or "searxng",
        "timeout_seconds": timeout,
        "cache_max_entries": _bounded_int("SEARXNG_CACHE_MAX_ENTRIES", 256, 16, 1024),
        "extractor_max_bytes": _bounded_int("LOCAL_WEB_EXTRACTOR_MAX_BYTES", 8 * 1024 * 1024, 1024, 32 * 1024 * 1024),
        "extractor_max_text_chars": _bounded_int("LOCAL_WEB_EXTRACTOR_MAX_TEXT_CHARS", 120_000, 1_000, 500_000),
        "extractor_timeout_seconds": _bounded_int("LOCAL_WEB_EXTRACTOR_TIMEOUT_SECONDS", timeout, 1, 60),
    }

for path in (DB_PATH.parent, EXPORTS_DIR, BOOK_EXPORTS_DIR, LOGS_DIR, UPLOADS_DIR, ASSETS_DIR, SOURCE_PACKS_DIR, SUMMARY_EXPORTS_DIR, PDF_OUTPUT_DIR):
    path.mkdir(parents=True, exist_ok=True)
