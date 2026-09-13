import re
import sqlite3
from dataclasses import dataclass
from .config import DB_PATH
from .data.catalog import PRODUCTS


@dataclass(frozen=True)
class Migration:
    """One ordered, transactional schema migration."""

    version: str
    statements: tuple[str, ...]


# Existing releases 001-006 are still bootstrapped by the legacy-compatible
# init block below. New schema work must be added here starting at 007.
MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        "007_agent_drafts",
        (
            """CREATE TABLE agent_drafts(
                id TEXT PRIMARY KEY,
                agent_task_id TEXT NOT NULL UNIQUE,
                agent_source TEXT NOT NULL,
                agent_version TEXT NOT NULL,
                content TEXT NOT NULL,
                review_required INTEGER NOT NULL DEFAULT 1 CHECK(review_required=1),
                quality_gate_status TEXT NOT NULL DEFAULT 'not_checked',
                human_approval_status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX idx_agent_drafts_created_at ON agent_drafts(created_at DESC)",
        ),
    ),
    Migration(
        "008_agent_task_audit",
        (
            """CREATE TABLE agent_task_audit(
                correlation_id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                hermes_task_id TEXT UNIQUE,
                status TEXT NOT NULL,
                prompt_sha256 TEXT NOT NULL,
                deadline_at TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0 CHECK(retry_count >= 0 AND retry_count <= 2),
                error_code TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            "CREATE INDEX idx_agent_task_audit_hermes_task_id ON agent_task_audit(hermes_task_id)",
            "CREATE INDEX idx_agent_task_audit_updated_at ON agent_task_audit(updated_at DESC)",
        ),
    ),
    Migration(
        "009_weekly_research_state",
        (
            """CREATE TABLE weekly_research_state(
                source TEXT PRIMARY KEY,
                digest TEXT NOT NULL,
                last_success_at TEXT NOT NULL
            )""",
        ),
    ),
)


def apply_migrations(conn: sqlite3.Connection, migrations: tuple[Migration, ...] = MIGRATIONS) -> list[str]:
    """Apply each pending migration once, rolling back a failed version fully."""
    versions = [migration.version for migration in migrations]
    if versions != sorted(versions) or len(versions) != len(set(versions)):
        raise ValueError("Migration versions must be unique and sorted")
    if any(not re.fullmatch(r"\d{3}_[a-z0-9_]+", version) for version in versions):
        raise ValueError("Migration versions must use NNN_lowercase_name")

    conn.execute(
        "CREATE TABLE IF NOT EXISTS app_schema_migrations("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    conn.commit()
    applied = {row[0] for row in conn.execute("SELECT version FROM app_schema_migrations")}
    completed: list[str] = []
    for migration in migrations:
        if migration.version in applied:
            continue
        try:
            conn.execute("BEGIN IMMEDIATE")
            for statement in migration.statements:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO app_schema_migrations(version,applied_at) VALUES(?,datetime('now'))",
                (migration.version,),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        completed.append(migration.version)
    return completed


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def init_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS app_schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    cur.execute("""CREATE TABLE IF NOT EXISTS ai_products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, product_name TEXT UNIQUE, current_name TEXT,
        current_version TEXT, release_date TEXT, checked_date TEXT, features TEXT, source_url TEXT, source_level TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS courses(
        id INTEGER PRIMARY KEY AUTOINCREMENT, course_type INTEGER, audience TEXT, created_date TEXT, data_json TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS lessons(
        id INTEGER PRIMARY KEY AUTOINCREMENT, course_id INTEGER, week INTEGER, topic TEXT, student_text TEXT, teacher_text TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT, weeks INTEGER, audience TEXT, provider TEXT, model TEXT,
        created_at TEXT, data_json TEXT, md_path TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS app_sequences(
        entity_type TEXT PRIMARY KEY, last_id INTEGER NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS lesson_units(
        id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER NOT NULL, week INTEGER NOT NULL,
        audience TEXT NOT NULL, profile_json TEXT NOT NULL, content_json TEXT NOT NULL,
        qa_json TEXT NOT NULL, approval_status TEXT NOT NULL DEFAULT 'pending',
        approved_at TEXT, created_at TEXT NOT NULL,
        UNIQUE(book_id, week))""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lesson_units_book_week ON lesson_units(book_id, week)")
    cur.execute("""CREATE TABLE IF NOT EXISTS app_users(
        username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS app_sessions(
        token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
        FOREIGN KEY(username) REFERENCES app_users(username) ON DELETE CASCADE)""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_app_sessions_expiry ON app_sessions(expires_at)")
    cur.execute("""CREATE TABLE IF NOT EXISTS job_states(
        id TEXT PRIMARY KEY, phase TEXT NOT NULL, message TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
        bytes_done INTEGER NOT NULL DEFAULT 0, bytes_total INTEGER NOT NULL DEFAULT 0, error TEXT NOT NULL DEFAULT '',
        result_json TEXT, payload_json TEXT, updated_at TEXT NOT NULL)""")
    if "payload_json" not in {row[1] for row in cur.execute("PRAGMA table_info(job_states)")}: 
        cur.execute("ALTER TABLE job_states ADD COLUMN payload_json TEXT")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_job_states_updated_at ON job_states(updated_at)")
    cur.execute("""CREATE TABLE IF NOT EXISTS visual_assets(
        id TEXT PRIMARY KEY, book_id INTEGER NOT NULL, week INTEGER NOT NULL,
        role TEXT NOT NULL, storage_key TEXT NOT NULL UNIQUE, original_name TEXT NOT NULL,
        mime_type TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
        aspect_ratio TEXT NOT NULL, alt_text_ko TEXT NOT NULL, alt_text_en TEXT NOT NULL DEFAULT '',
        caption_ko TEXT NOT NULL DEFAULT '', caption_en TEXT NOT NULL DEFAULT '',
        source_type TEXT NOT NULL, source_url TEXT NOT NULL DEFAULT '', creator TEXT NOT NULL DEFAULT '',
        license TEXT NOT NULL DEFAULT '', copyright_status TEXT NOT NULL DEFAULT 'review_required',
        checksum TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
        approved_at TEXT, FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE)""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_visual_assets_book_week ON visual_assets(book_id, week)")
    cur.execute("""CREATE TABLE IF NOT EXISTS image_prompts(
        id TEXT PRIMARY KEY, book_id INTEGER NOT NULL, week INTEGER NOT NULL, asset_id TEXT,
        purpose TEXT NOT NULL, prompt_ko TEXT NOT NULL, prompt_en TEXT NOT NULL,
        negative_prompt_ko TEXT NOT NULL DEFAULT '', negative_prompt_en TEXT NOT NULL DEFAULT '',
        style TEXT NOT NULL, aspect_ratio TEXT NOT NULL, audience TEXT NOT NULL,
        generation_status TEXT NOT NULL DEFAULT 'prompt_only', review_status TEXT NOT NULL DEFAULT 'needs_review',
        prompt_source_language TEXT NOT NULL DEFAULT 'ko_en', translation_status TEXT NOT NULL DEFAULT 'draft',
        created_by TEXT NOT NULL DEFAULT 'studio', created_at TEXT NOT NULL, approved_at TEXT,
        FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
        FOREIGN KEY(asset_id) REFERENCES visual_assets(id) ON DELETE SET NULL)""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_image_prompts_book_week ON image_prompts(book_id, week)")
    cur.execute("""CREATE TABLE IF NOT EXISTS manual_update_state(
        id INTEGER PRIMARY KEY CHECK(id=1), snapshot_json TEXT NOT NULL,
        fingerprint TEXT NOT NULL, applied_at TEXT NOT NULL)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS evidence_packs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, status TEXT NOT NULL,
        fingerprint TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS evidence_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT, pack_id INTEGER NOT NULL, evidence_key TEXT NOT NULL,
        source_type TEXT NOT NULL, source_grade TEXT NOT NULL, source_title TEXT NOT NULL,
        source_url TEXT NOT NULL, publisher TEXT, published_at TEXT, retrieved_at TEXT NOT NULL,
        claim TEXT NOT NULL, evidence_summary TEXT NOT NULL, relevance_score REAL NOT NULL,
        freshness_score REAL NOT NULL, trust_score REAL NOT NULL, lecture_use TEXT,
        FOREIGN KEY(pack_id) REFERENCES evidence_packs(id) ON DELETE CASCADE,
        UNIQUE(pack_id, evidence_key))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sources(
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, title TEXT, original_name TEXT, url TEXT, mime_type TEXT,
        local_path TEXT, extracted_text TEXT, summary TEXT, status TEXT, created_at TEXT, metadata_json TEXT)""")
    source_columns = {row[1] for row in cur.execute("PRAGMA table_info(sources)")}
    for name, definition in (("updated_at", "TEXT"), ("content_hash", "TEXT"), ("vector_status", "TEXT"), ("storage_mode", "TEXT"), ("summary_path", "TEXT")):
        if name not in source_columns:
            cur.execute(f"ALTER TABLE sources ADD COLUMN {name} {definition}")
    cur.execute("""CREATE TABLE IF NOT EXISTS source_vectors(
        source_id INTEGER NOT NULL, chunk_no INTEGER NOT NULL, char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
        embedding BLOB NOT NULL, PRIMARY KEY(source_id, chunk_no), FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE)""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_source_vectors_source ON source_vectors(source_id)")
    cur.execute("""CREATE TABLE IF NOT EXISTS web_api_usage(
        month TEXT NOT NULL, provider TEXT NOT NULL, request_count INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL, PRIMARY KEY(month, provider))""")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sources_updated_at ON sources(updated_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_books_created_at ON books(created_at DESC)")
    for p in PRODUCTS:
        cur.execute("""INSERT INTO ai_products(company,product_name,current_name,current_version,release_date,checked_date,features,source_url,source_level)
            VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(product_name) DO UPDATE SET
            company=excluded.company,current_name=excluded.current_name,current_version=excluded.current_version,
            release_date=excluded.release_date,checked_date=excluded.checked_date,features=excluded.features,
            source_url=excluded.source_url,source_level=excluded.source_level""", p)
    cur.execute("INSERT OR IGNORE INTO app_schema_migrations(version,applied_at) VALUES('001_initial_schema',datetime('now'))")
    cur.execute("INSERT OR IGNORE INTO app_schema_migrations(version,applied_at) VALUES('002_manual_update_state',datetime('now'))")
    cur.execute("INSERT OR IGNORE INTO app_schema_migrations(version,applied_at) VALUES('003_hybrid_evidence',datetime('now'))")
    cur.execute("INSERT OR IGNORE INTO app_schema_migrations(version,applied_at) VALUES('004_web_api_usage',datetime('now'))")
    cur.execute("INSERT OR IGNORE INTO app_schema_migrations(version,applied_at) VALUES('005_persistent_job_states',datetime('now'))")
    cur.execute("INSERT OR IGNORE INTO app_schema_migrations(version,applied_at) VALUES('006_visual_assets_and_image_prompts',datetime('now'))")
    conn.commit()
    apply_migrations(conn)
    conn.close()
