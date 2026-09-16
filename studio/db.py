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
    Migration(
        "010_weekly_research_lock",
        (
            """CREATE TABLE weekly_research_lock(
                lock_name TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )""",
        ),
    ),
    Migration(
        "011_learning_tools",
        (
            """CREATE TABLE learning_tools(
                id TEXT PRIMARY KEY,
                slug TEXT NOT NULL UNIQUE,
                name_ko TEXT NOT NULL,
                name_en TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('SERVICE','CONCEPT','WORKFLOW')),
                vendor TEXT NOT NULL DEFAULT '',
                summary_ko TEXT NOT NULL DEFAULT '',
                summary_en TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""",
            """CREATE TABLE tool_versions(
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                version_label TEXT NOT NULL,
                released_at TEXT,
                checked_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'VERIFIED',
                source_evidence_id TEXT,
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE tool_capabilities(
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                capability_key TEXT NOT NULL,
                label_ko TEXT NOT NULL,
                label_en TEXT NOT NULL,
                description_ko TEXT NOT NULL DEFAULT '',
                description_en TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE,
                UNIQUE(tool_id, capability_key)
            )""",
            """CREATE TABLE timeline_events(
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_title_ko TEXT NOT NULL,
                event_title_en TEXT NOT NULL,
                summary_ko TEXT NOT NULL DEFAULT '',
                summary_en TEXT NOT NULL DEFAULT '',
                importance TEXT NOT NULL DEFAULT 'normal',
                source_evidence_id TEXT,
                verified_at TEXT NOT NULL,
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE prompt_frameworks(
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description_ko TEXT NOT NULL DEFAULT '',
                description_en TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
            )""",
            """CREATE TABLE prompt_skills(
                id TEXT PRIMARY KEY,
                framework_id TEXT NOT NULL,
                skill_key TEXT NOT NULL,
                name_ko TEXT NOT NULL,
                name_en TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                FOREIGN KEY(framework_id) REFERENCES prompt_frameworks(id) ON DELETE CASCADE,
                UNIQUE(framework_id, skill_key)
            )""",
            """CREATE TABLE prompt_examples(
                prompt_id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                level TEXT NOT NULL CHECK(level IN ('BEGINNER','INTERMEDIATE','ADVANCED')),
                example_no INTEGER NOT NULL CHECK(example_no BETWEEN 1 AND 3),
                title_ko TEXT NOT NULL,
                title_en TEXT NOT NULL,
                prompt_ko TEXT NOT NULL,
                prompt_en TEXT NOT NULL,
                purpose TEXT NOT NULL,
                skills_json TEXT NOT NULL DEFAULT '[]',
                framework_json TEXT NOT NULL DEFAULT '{}',
                verified_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ACTIVE',
                version INTEGER NOT NULL DEFAULT 1 CHECK(version > 0),
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE,
                UNIQUE(tool_id, level, example_no)
            )""",
            """CREATE TABLE modern_prompt_examples(
                modern_prompt_id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                title_ko TEXT NOT NULL,
                title_en TEXT NOT NULL,
                prompt_ko TEXT NOT NULL,
                prompt_en TEXT NOT NULL,
                effective_from TEXT NOT NULL,
                source_evidence_ids_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'VERIFIED',
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE update_events(
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                official_published_at TEXT,
                checked_at TEXT NOT NULL,
                service_version TEXT NOT NULL DEFAULT '',
                region TEXT NOT NULL DEFAULT '',
                plan_scope TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'DISCOVERED',
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE source_evidence(
                id TEXT PRIMARY KEY,
                tool_id TEXT,
                source_type TEXT NOT NULL,
                source_title TEXT NOT NULL,
                source_url TEXT NOT NULL,
                published_at TEXT,
                checked_at TEXT NOT NULL,
                region TEXT NOT NULL DEFAULT '',
                plan_scope TEXT NOT NULL DEFAULT '',
                verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
                notes TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE SET NULL
            )""",
            """CREATE TABLE update_rules(
                id TEXT PRIMARY KEY,
                rule_key TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL,
                change_level TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1))
            )""",
            """CREATE TABLE course_tool_references(
                id TEXT PRIMARY KEY,
                course_id INTEGER NOT NULL,
                week_id INTEGER,
                lesson_id INTEGER,
                tool_id TEXT NOT NULL,
                match_method TEXT NOT NULL DEFAULT 'human_approved',
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE course_update_matches(
                id TEXT PRIMARY KEY,
                course_id INTEGER NOT NULL,
                tool_id TEXT NOT NULL,
                update_event_id TEXT NOT NULL,
                week_id INTEGER,
                lesson_id INTEGER,
                matched_text TEXT NOT NULL,
                match_context TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE,
                FOREIGN KEY(update_event_id) REFERENCES update_events(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE course_update_suggestions(
                id TEXT PRIMARY KEY,
                course_id INTEGER NOT NULL,
                week_id INTEGER,
                lesson_id INTEGER,
                tool_id TEXT NOT NULL,
                match_id TEXT,
                matched_text TEXT NOT NULL,
                suggested_text TEXT NOT NULL,
                reason TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_evidence_id TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewed_by TEXT,
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE CASCADE,
                FOREIGN KEY(match_id) REFERENCES course_update_matches(id) ON DELETE SET NULL,
                FOREIGN KEY(source_evidence_id) REFERENCES source_evidence(id) ON DELETE SET NULL
            )""",
            """CREATE TABLE course_update_decisions(
                id TEXT PRIMARY KEY,
                suggestion_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK(decision IN ('KEEP','PARTIAL_APPLY','FULL_APPLY','DEFER','REJECT')),
                reviewed_by TEXT NOT NULL,
                reviewed_at TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                source_version TEXT NOT NULL DEFAULT '',
                target_version TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(suggestion_id) REFERENCES course_update_suggestions(id) ON DELETE CASCADE
            )""",
            """CREATE TABLE course_versions(
                id TEXT PRIMARY KEY,
                course_id INTEGER NOT NULL,
                source_version TEXT NOT NULL,
                version_label TEXT NOT NULL,
                content_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'DRAFT'
            )""",
            """CREATE INDEX idx_learning_tools_active ON learning_tools(active, name_ko)""",
            """CREATE INDEX idx_timeline_events_tool_date ON timeline_events(tool_id, event_date DESC)""",
            """CREATE INDEX idx_prompt_examples_tool_level ON prompt_examples(tool_id, level, example_no)""",
            """CREATE INDEX idx_modern_prompt_examples_tool ON modern_prompt_examples(tool_id, effective_from DESC)""",
            """CREATE INDEX idx_update_events_tool_status ON update_events(tool_id, status, checked_at DESC)""",
            """CREATE INDEX idx_course_tool_references_course ON course_tool_references(course_id, tool_id)""",
            """CREATE INDEX idx_course_update_suggestions_course ON course_update_suggestions(course_id, status, created_at DESC)""",
            """CREATE INDEX idx_course_versions_course ON course_versions(course_id, created_at DESC)""",
        ),
    ),
    Migration(
        "012_learning_audit_log",
        (
            """CREATE TABLE learning_audit_log(
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                course_id INTEGER,
                tool_id TEXT,
                source_version TEXT NOT NULL DEFAULT '',
                target_version TEXT NOT NULL DEFAULT '',
                decision TEXT NOT NULL DEFAULT '',
                timestamp TEXT NOT NULL,
                evidence_id TEXT,
                result TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(tool_id) REFERENCES learning_tools(id) ON DELETE SET NULL
            )""",
            "CREATE INDEX idx_learning_audit_course_time ON learning_audit_log(course_id, timestamp DESC)",
            "CREATE INDEX idx_learning_audit_event_type ON learning_audit_log(event_type, timestamp DESC)",
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
