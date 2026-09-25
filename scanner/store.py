"""Authoritative SQLite-backed record store with legacy API compatibility."""
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from scanner import BASE_DIR
from scanner.logger import get_logger

logger = get_logger("store")
DB_PATH = os.path.join(BASE_DIR, "scans.db")
# Compatibility name only; live data is stored in scans.db.
DATA_STORE_PATH = os.path.join(BASE_DIR, "data_store.json")
CLASS5_STORE_PATH = DATA_STORE_PATH
DECLARATIONS_BUCKET = "declarations"
CLASS5_BUCKET = "class5"


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("""CREATE TABLE IF NOT EXISTS record_store (
            bucket TEXT NOT NULL, record_key TEXT NOT NULL, payload_json TEXT NOT NULL,
            updated_at TEXT NOT NULL, PRIMARY KEY (bucket, record_key))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS store_meta (
            meta_key TEXT PRIMARY KEY, meta_value TEXT NOT NULL)""")
        with conn:
            yield conn
    finally:
        conn.close()


def _record_key(entry: Dict[str, Any]) -> str:
    from scanner.parser import to_english_digits
    raw = entry.get("dec_no_id") or entry.get("declaration_no") or entry.get("dec_no_display") or ""
    return to_english_digits(str(raw)).strip()


def _legacy_payload(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
            return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _migrate_legacy_json_once() -> None:
    marker = "legacy_json_migrated_v1"
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM store_meta WHERE meta_key=?", (marker,)).fetchone():
            return
        raw = _legacy_payload(DATA_STORE_PATH)
        declarations = raw.get("declarations", {}) if raw else {}
        class5 = raw.get("class5", {}) if raw else {}
        if raw and not declarations and not class5:
            declarations = raw
        now = datetime.now(timezone.utc).isoformat()
        for bucket, records in ((DECLARATIONS_BUCKET, declarations), (CLASS5_BUCKET, class5)):
            if isinstance(records, dict):
                conn.executemany(
                    "INSERT OR IGNORE INTO record_store VALUES (?, ?, ?, ?)",
                    [(bucket, str(k), json.dumps(v, ensure_ascii=False), now)
                     for k, v in records.items() if isinstance(v, dict)],
                )
        conn.execute("INSERT INTO store_meta VALUES (?, ?)", (marker, now))
        conn.commit()


def _load_bucket(bucket: str) -> Dict[str, Any]:
    _migrate_legacy_json_once()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT record_key, payload_json FROM record_store WHERE bucket=?", (bucket,)
        ).fetchall()
    result = {}
    for key, payload in rows:
        try:
            value = json.loads(payload)
            if isinstance(value, dict):
                result[key] = value
        except (TypeError, json.JSONDecodeError):
            logger.warning("Ignoring corrupt stored record: %s/%s", bucket, key)
    return result


def _replace_bucket(bucket: str, records: Dict[str, Any]) -> None:
    """Replace a logical store in one transaction; previous data survives failures."""
    now = datetime.now(timezone.utc).isoformat()
    rows = [(bucket, str(k), json.dumps(v, ensure_ascii=False), now)
            for k, v in records.items() if isinstance(v, dict)]
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM record_store WHERE bucket=?", (bucket,))
        conn.executemany("INSERT INTO record_store VALUES (?, ?, ?, ?)", rows)
        conn.commit()


def _merge_bucket(bucket: str, entries) -> int:
    now = datetime.now(timezone.utc).isoformat()
    prepared = []
    for entry in entries:
        key = _record_key(entry)
        if key:
            prepared.append((bucket, key, json.dumps(entry, ensure_ascii=False), now))
    if not prepared:
        return 0
    with _connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = {r[0] for r in conn.execute(
            "SELECT record_key FROM record_store WHERE bucket=?", (bucket,))}
        conn.executemany("""INSERT INTO record_store VALUES (?, ?, ?, ?)
            ON CONFLICT(bucket,record_key) DO UPDATE SET
            payload_json=excluded.payload_json, updated_at=excluded.updated_at""", prepared)
        conn.commit()
    return sum(1 for _, key, _, _ in prepared if key not in existing)


def load_store(path: str = DATA_STORE_PATH) -> Dict[str, Any]:
    if os.path.abspath(path) != os.path.abspath(DATA_STORE_PATH):
        raw = _legacy_payload(path)
        return raw.get("declarations", raw) if isinstance(raw, dict) else {}
    return _load_bucket(DECLARATIONS_BUCKET)


def save_store(store: Dict[str, Any], path: str = DATA_STORE_PATH):
    if os.path.abspath(path) != os.path.abspath(DATA_STORE_PATH):
        raise ValueError("JSON stores are migration inputs only; live storage is SQLite")
    _replace_bucket(DECLARATIONS_BUCKET, store)


def load_class5_store(path: str = DATA_STORE_PATH) -> Dict[str, Any]:
    return _load_bucket(CLASS5_BUCKET)


def save_class5_store(store: Dict[str, Any], path: str = DATA_STORE_PATH):
    _replace_bucket(CLASS5_BUCKET, store)


def load_account_store(user_name: str) -> Dict[str, Any]:
    bucket = f"account:{user_name}"
    records = _load_bucket(bucket)
    if records:
        return records
    # One-time compatibility import for installations that used per-account JSON.
    folder = re.sub(r'[\\/*?:"<>|]', "_", user_name).strip() or "default_user"
    legacy_path = os.path.join(BASE_DIR, "accounts", folder, "data_store.json")
    raw = _legacy_payload(legacy_path)
    legacy_records = raw.get("declarations", raw) if isinstance(raw, dict) else {}
    if legacy_records:
        _replace_bucket(bucket, legacy_records)
        return legacy_records
    return {}


def save_account_store(user_name: str, store: Dict[str, Any]) -> None:
    if user_name:
        _replace_bucket(f"account:{user_name}", store)


def merge_records(store: Dict[str, Any], entries) -> int:
    added = 0
    for entry in entries:
        key = _record_key(entry)
        if not key:
            continue
        added += int(key not in store)
        store[key] = entry
    return added


def merge_class5_records(entries, path: str = DATA_STORE_PATH) -> int:
    return _merge_bucket(CLASS5_BUCKET, entries)


def store_counts(path: str = DATA_STORE_PATH) -> Dict[str, int]:
    with _connect() as conn:
        rows = dict(conn.execute("""SELECT bucket, COUNT(*) FROM record_store
            WHERE bucket IN (?,?) GROUP BY bucket""",
            (DECLARATIONS_BUCKET, CLASS5_BUCKET)).fetchall())
    return {"data": int(rows.get(DECLARATIONS_BUCKET, 0)),
            "class5": int(rows.get(CLASS5_BUCKET, 0))}
