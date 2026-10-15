"""Persistence boundary for completed scans.

Workers collect in memory. Only this service is allowed to publish collected
records to the authoritative SQLite store after a successful scan.
"""
from typing import Any, Dict, Iterable
from scanner.database import save_declarations_batch, update_scan_stats, DB_FILE
from scanner.store import merge_class5_records, save_store


def publish_targeted_scan(scan_id: int, records: Iterable[Dict[str, Any]]) -> tuple[int, int]:
    records = list(records)
    class5_records = [r for r in records if r.get("has_class_5")]
    target_records = class5_records if class5_records else records
    save_declarations_batch(scan_id, target_records, db_path=DB_FILE)
    added = merge_class5_records(target_records)
    count = len(target_records)
    update_scan_stats(scan_id, count, count, 0, db_path=DB_FILE)
    return added, count


def publish_declaration_snapshot(records: Dict[str, Dict[str, Any]]) -> None:
    """Atomically replace the authoritative declaration snapshot."""
    save_store(records)
