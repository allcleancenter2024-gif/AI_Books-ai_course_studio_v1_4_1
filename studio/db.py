import sqlite3
from .config import DB_PATH
from .data.catalog import PRODUCTS


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
    conn.commit()
    conn.close()
