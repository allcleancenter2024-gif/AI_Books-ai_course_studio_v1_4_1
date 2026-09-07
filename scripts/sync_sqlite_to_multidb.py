"""One-way, idempotent migration from the legacy SQLite file into MongoDB and PostgreSQL.

The SQLite database is never modified. Run after the Docker stack is healthy:
  python scripts/sync_sqlite_to_multidb.py
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pymongo import ASCENDING, MongoClient
import psycopg

ROOT = Path(__file__).resolve().parents[1]
SQLITE_PATH = ROOT / "data" / "studio.db"
SERVICE_TABLES = ("ai_products", "courses", "lessons", "books")


def load_local_env() -> dict[str, str]:
    """Read the local Compose credentials without adding a dotenv dependency."""
    values: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def json_value(value):
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return value


def main() -> None:
    if not SQLITE_PATH.exists():
        raise SystemExit(f"SQLite database not found: {SQLITE_PATH}")
    env = load_local_env()
    mongo_uri = os.getenv("MONGODB_URI") or (
        f"mongodb://{env['MONGO_INITDB_ROOT_USERNAME']}:{env['MONGO_INITDB_ROOT_PASSWORD']}@"
        f"127.0.0.1:{env.get('MONGO_HOST_PORT', '27018')}/{env['MONGO_INITDB_DATABASE']}?authSource=admin"
    )
    postgres_dsn = os.getenv("DATABASE_URL") or (
        f"postgresql://{env['POSTGRES_USER']}:{env['POSTGRES_PASSWORD']}@"
        f"127.0.0.1:{env.get('POSTGRES_HOST_PORT', '5434')}/{env['POSTGRES_DB']}"
    )
    mongo = MongoClient(mongo_uri)
    raw = mongo.get_database().raw_sources
    raw.create_index([("legacy_source_id", ASCENDING)], unique=True)
    raw.create_index([("collectedAt", ASCENDING)])

    with sqlite3.connect(SQLITE_PATH) as legacy, psycopg.connect(postgres_dsn) as postgres:
        legacy.row_factory = sqlite3.Row
        with postgres.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS "ServiceRecord" (
                id INTEGER NOT NULL, "entityType" TEXT NOT NULL, payload JSONB NOT NULL,
                "mongoId" TEXT, "createdAt" TIMESTAMPTZ, "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT "ServiceRecord_pkey" PRIMARY KEY (id, "entityType"))''')
            cur.execute('CREATE INDEX IF NOT EXISTS service_record_entity_updated_idx ON "ServiceRecord" ("entityType", "updatedAt")')
            source_count = 0
            for row in legacy.execute("SELECT * FROM sources"):
                doc = dict(row)
                doc["metadata"] = json_value(doc.pop("metadata_json", "{}"))
                doc["legacy_source_id"] = doc["id"]
                doc["collectedAt"] = datetime.now(timezone.utc)
                result = raw.update_one({"legacy_source_id": doc["id"]}, {"$set": doc}, upsert=True)
                raw_id = result.upserted_id or raw.find_one({"legacy_source_id": doc["id"]}, {"_id": 1})["_id"]
                service_payload = {key: value for key, value in doc.items() if key not in {"extracted_text", "embedding"}}
                cur.execute('''INSERT INTO "ServiceRecord" (id, "entityType", payload, "mongoId", "createdAt")
                    VALUES (%s, 'source', %s::jsonb, %s, %s)
                    ON CONFLICT (id, "entityType") DO UPDATE SET payload=EXCLUDED.payload, "mongoId"=EXCLUDED."mongoId", "updatedAt"=now()''',
                    (doc["id"], json.dumps(service_payload, ensure_ascii=False, default=str), str(raw_id), doc.get("created_at")))
                source_count += 1
            for table in SERVICE_TABLES:
                for row in legacy.execute(f"SELECT * FROM {table}"):
                    data = dict(row)
                    cur.execute('''INSERT INTO "ServiceRecord" (id, "entityType", payload, "createdAt")
                        VALUES (%s, %s, %s::jsonb, %s)
                        ON CONFLICT (id, "entityType") DO UPDATE SET payload=EXCLUDED.payload, "updatedAt"=now()''',
                        (data["id"], table, json.dumps(data, ensure_ascii=False, default=str), data.get("created_at") or data.get("created_date")))
        postgres.commit()
    print(f"Sync complete: {source_count} source records copied to MongoDB; service records upserted to PostgreSQL.")


if __name__ == "__main__":
    main()
