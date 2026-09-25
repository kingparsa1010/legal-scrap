"""Persistence boundary for completed scans.

Workers collect in memory. Only this service is allowed to publish collected
records to the authoritative SQLite store after a successful scan.
"""
from typing import Any, Dict, Iterable
from scanner.database import save_declarations_batch, update_scan_stats, DB_FILE
from scanner.store import merge_class5_records, save_store


def publish_targeted_scan(scan_id: int, records: Iterable[Dict[str, Any]]) -> tuple[int, int]:
    records = list(records)
    save_declarations_batch(scan_id, records, db_path=DB_FILE)
    added = merge_class5_records(records)
    class5_count = sum(1 for row in records if row.get("has_class_5"))
    update_scan_stats(scan_id, len(records), class5_count, 0, db_path=DB_FILE)
    return added, class5_count


def publish_declaration_snapshot(records: Dict[str, Dict[str, Any]]) -> None:
    """Atomically replace the authoritative declaration snapshot."""
    save_store(records)
