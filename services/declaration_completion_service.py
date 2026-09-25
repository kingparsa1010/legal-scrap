"""Commit and export a successfully completed declaration scan."""
import time
from typing import Any, Callable, Dict, List
from scanner.auth import get_authenticated_session, save_account_data
from scanner.database import create_scan_session, save_declarations_batch, update_scan_stats, DB_FILE
from scanner.word_exporter import export_declarations_to_word
from services.scan_persistence_service import publish_declaration_snapshot


def complete_declaration_scan(
    mode: str,
    total_records: int,
    store: Dict[str, Dict[str, Any]],
    new_records: List[Dict[str, Any]],
    user_name: str,
    docx_path: str,
    on_progress: Callable[[int, str], None],
) -> None:
    # The current snapshot is published atomically only after collection succeeds.
    publish_declaration_snapshot(store)
    save_account_data(user_name, store, docx_path)

    scan_id = create_scan_session(
        scan_date=time.strftime("%Y/%m/%d %H:%M"),
        search_params={"mode": mode, "source": "DeclarationList", "total": total_records},
        total_records=len(store), class5_count=0, alerts_count=0, db_path=DB_FILE,
    )
    if new_records:
        save_declarations_batch(scan_id, new_records, db_path=DB_FILE)
    update_scan_stats(scan_id, len(store), 0, 0, db_path=DB_FILE)

    on_progress(92, "در حال تولید فایل Word...")
    new_ids = {row["dec_no_id"] for row in new_records}
    older = [row for row in store.values() if row.get("dec_no_id") not in new_ids]
    ordered = list(new_records) + older
    export_declarations_to_word(
        declarations=ordered,
        output_path=docx_path,
        session=get_authenticated_session(),
        progress_callback=lambda cur, total: on_progress(
            min(99, 92 + int((cur / max(1, total)) * 7)),
            f"تعبیه تصاویر و پیوندها در Word ({cur}/{total})...",
        ),
    )
