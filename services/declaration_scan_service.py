"""Collection logic for the authenticated declaration-list scan."""
import re
import time
from typing import Any, Callable, Dict, Tuple
from scanner.parser import parse_declaration_page

BASE_LIST_URL = (
    "https://ipm.ssaa.ir/CA/DeclarationList?DeclarationType=&decNo=&FromDate=&ToDate="
    "&DeclarationState=&dTitle=&DeclarationSort=1&TotalRecord={total_record}&p={page}"
)


class IncompleteFullScan(RuntimeError):
    pass


def collect_declarations(
    session,
    first_html: str,
    mode: str,
    max_pages: int,
    existing_store: Dict[str, Dict[str, Any]],
    is_running: Callable[[], bool],
    on_progress: Callable[[int, str], None],
    on_record: Callable[[Dict[str, Any]], None],
) -> Tuple[Dict[str, Dict[str, Any]], list, int, int]:
    match = re.search(r"TotalRecord=(\d+)", first_html)
    total_records = int(match.group(1)) if match else 1001
    calculated_pages = max(1, (total_records + 19) // 20)
    if mode == "full_rescan" and max_pages < calculated_pages:
        raise IncompleteFullScan(
            f"اسکن کامل به {calculated_pages} صفحه نیاز دارد، اما سقف {max_pages} صفحه است."
        )
    page_limit = min(max_pages, calculated_pages)
    on_progress(15, f"تعداد کل: {total_records} مورد (~{calculated_pages} صفحه)")

    store = dict(existing_store) if mode == "new_only" else {}
    first_run = not store
    collected = []
    page = 1
    while page <= page_limit and is_running():
        if page == 1:
            html = first_html
        else:
            try:
                response = session.get(
                    BASE_LIST_URL.format(total_record=total_records, page=page),
                    timeout=30,
                    verify=False,
                )
                response.raise_for_status()
                html = response.text
            except Exception as exc:
                if mode == "full_rescan":
                    raise IncompleteFullScan(f"دریافت صفحه {page} ناموفق بود: {exc}") from exc
                break

        rows = parse_declaration_page(html)
        if not rows:
            if mode == "full_rescan" and page <= calculated_pages:
                raise IncompleteFullScan(f"صفحه {page} برخلاف تعداد اعلام‌شده خالی بود.")
            break

        new_on_page = 0
        for entry in rows:
            if not is_running():
                break
            key = entry["dec_no_id"]
            if mode == "new_only" and key in store:
                continue
            store[key] = entry
            collected.append(entry)
            new_on_page += 1
            on_record(entry)

        percent = min(90, int(15 + (page / page_limit) * 75))
        label = f"{len(collected)} مورد جدید" if mode == "new_only" else f"{len(store)} رکورد"
        on_progress(percent, f"صفحه {page} از {page_limit} ({label})")
        if mode == "new_only" and not first_run and new_on_page == 0:
            break
        page += 1
        time.sleep(0.15)

    return store, collected, len(collected), total_records
