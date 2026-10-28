"""Collection logic for the authenticated declaration-list scan."""
import re
import time
from typing import Any, Callable, Dict, List, Tuple
from scanner.parser import parse_declaration_page, parse_declaration_detail, ensure_record_fields

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
            ensure_record_fields(entry)
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


def enrich_with_details(
    session,
    records: List[Dict[str, Any]],
    is_running: Callable[[], bool] = lambda: True,
    on_progress: Callable[[int, str], None] = lambda *_: None,
    limit: int = 300,
) -> int:
    """تکمیل شماره ثبت، تاریخ تمدید و لینک گواهی با مراجعه به صفحه جزئیات هر پرونده.

    فقط رکوردهای جدید و تا سقف limit enrichment می‌شوند تا اسکن کند نشود.
    هر خطا نادیده گرفته می‌شود و ستون مربوطه «—» می‌ماند. خروجی: تعداد غنی‌شده.
    """
    enriched = 0
    targets = [r for r in records if r.get('detail_url')][:max(0, limit)]
    total = len(targets)
    for i, rec in enumerate(targets, start=1):
        if not is_running():
            break
        # اگر هر سه فیلد از قبل پر است، درخواست نزن
        if rec.get('register_no') and rec.get('renewal_date') and rec.get('certificate_url'):
            continue
        try:
            resp = session.get(rec['detail_url'], timeout=15, verify=False)
            if getattr(resp, 'status_code', 0) != 200:
                continue
            detail = parse_declaration_detail(getattr(resp, 'text', ''))
            # شماره ثبت و تاریخ ثبت قطعی در صفحه گردش کار پرونده قرار دارند.
            workflow_url = detail.get('workflow_url')
            if workflow_url:
                try:
                    wf_resp = session.get(workflow_url, timeout=15, verify=False)
                    if getattr(wf_resp, 'status_code', 0) == 200:
                        workflow_detail = parse_declaration_detail(getattr(wf_resp, 'text', ''))
                        for key in ('register_no', 'reg_date', 'renewal_date', 'certificate_url'):
                            if workflow_detail.get(key):
                                detail[key] = workflow_detail[key]
                except Exception:
                    pass
            if detail.get('register_no'):
                rec['register_no'] = detail['register_no']
            if detail.get('reg_date') and not rec.get('reg_date'):
                rec['reg_date'] = detail['reg_date']
                rec['declaration_date'] = detail['reg_date']
            if detail.get('renewal_date'):
                rec['renewal_date'] = detail['renewal_date']
            if detail.get('certificate_url'):
                rec['certificate_url'] = detail['certificate_url']
            if detail.get('title_fa'):
                rec['title_fa'] = detail['title_fa']
            if detail.get('title_en'):
                rec['title_en'] = detail['title_en']
            ensure_record_fields(rec)
            enriched += 1
        except Exception:
            continue
        if i % 10 == 0:
            try:
                on_progress(90, f"تکمیل جزئیات پرونده‌ها ({i}/{total})...")
            except Exception:
                pass
        time.sleep(0.1)
    return enriched
