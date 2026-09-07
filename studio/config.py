import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
# Server environment variables always win; .env only fills missing values.
load_dotenv(PROJECT_DIR / ".env", override=False)

# Versioning policy: patch for small fixes (v1.4.1 -> v1.4.2), minor for
# substantial user-facing changes (v1.4.1 -> v1.5.0).
VERSION = "1.24.0"
LAST_UPDATED = "2026-08-29"
APP_TITLE = f"AI 강의 활용 Studio v{VERSION} [{LAST_UPDATED}]"
BASE_DIR = PROJECT_DIR
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
SOURCE_PACKS_DIR = EXPORTS_DIR / "source_packs"
SUMMARY_EXPORTS_DIR = EXPORTS_DIR / "summaries"
PDF_OUTPUT_DIR = RUNTIME_DIR / "output" / "pdf"
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
UPLOAD_CHUNK_BYTES = 1024 * 1024
EXTRACTED_TEXT_LIMIT = 120_000
AUTH_COOKIE_SECURE = os.getenv("AI_COURSE_STUDIO_COOKIE_SECURE", "0") == "1"

for path in (DB_PATH.parent, EXPORTS_DIR, BOOK_EXPORTS_DIR, LOGS_DIR, UPLOADS_DIR, SOURCE_PACKS_DIR, SUMMARY_EXPORTS_DIR, PDF_OUTPUT_DIR):
    path.mkdir(parents=True, exist_ok=True)
