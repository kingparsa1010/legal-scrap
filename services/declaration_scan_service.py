"""Collection logic for the authenticated declaration-list scan."""
import re
import time
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, parse_qs, urlencode
logger = logging.getLogger("legal_scrap.registration")
from typing import Any, Callable, Dict, List, Tuple
from scanner.parser import parse_declaration_page, parse_declaration_detail, ensure_record_fields, to_english_digits

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
    from scanner.parser import to_english_digits
    first_rows = parse_declaration_page(first_html)
    counts = re.findall(r"TotalRecord=(\d+)", to_english_digits(first_html), re.I)
    total_records = max(map(int, counts)) if counts else None
    if mode == "full_rescan" and total_records is None:
        raise IncompleteFullScan("تعداد کل رکوردها از پاسخ سامانه قابل تأیید نیست.")
    if mode == "full_rescan" and not first_rows:
        raise IncompleteFullScan("صفحه اول فاقد رکورد قابل تأیید است؛ داده‌های قبلی حفظ شدند.")
    # Page size is measured from the actual response, never assumed to be 20.
    page_size = max(1, len(first_rows))
    calculated_pages = max(1, ((total_records or page_size) + page_size - 1) // page_size)
    if mode == "full_rescan" and max_pages < calculated_pages:
        raise IncompleteFullScan(f"اسکن کامل به حدود {calculated_pages} صفحه نیاز دارد، اما سقف {max_pages} است.")
    on_progress(15, f"تعداد کل: {total_records if total_records is not None else 'نامشخص'}؛ اندازه صفحه: {page_size}")
    store = dict(existing_store) if mode == "new_only" else {}
    first_run = not store
    collected = []
    seen = set()
    for page in range(1, max_pages + 1):
        if not is_running():
            break
        if page == 1:
            rows = first_rows
        else:
            rows = []
            failure = "پاسخ خالی یا تکراری"
            for attempt in range(3):
                if not is_running():
                    break
                try:
                    response = session.get(BASE_LIST_URL.format(total_record=total_records or '', page=page), timeout=12, verify=False)
                    response.raise_for_status()
                    if any(part in str(getattr(response, 'url', '')).lower() for part in ('signin', '/login')):
                        raise ValueError("نشست منقضی شده است")
                    candidate = parse_declaration_page(response.text)
                    if candidate and any(str(r['dec_no_id']) not in seen for r in candidate):
                        rows = candidate
                        break
                except Exception as exc:
                    failure = type(exc).__name__
                if attempt < 2:
                    time.sleep(0.15 * (attempt + 1))
            if not rows:
                if mode == "full_rescan" and is_running():
                    raise IncompleteFullScan(f"صفحه {page} پس از ۳ تلاش تأیید نشد ({failure})؛ {len(seen)} از {total_records} رکورد دریافت شد.")
                break
        new_on_page = 0
        for raw_entry in rows:
            if not is_running():
                break
            entry = dict(raw_entry)
            key = str(entry['dec_no_id'])
            if key in seen:
                continue
            seen.add(key)
            already_known = key in existing_store
            previous = existing_store.get(key, {})
            for field in ('register_no', 'registration_date', 'renewal_date', 'certificate_url', 'print_url', 'workflow_url', 'steps_url', 'registration_fetch_status', 'queue_count', 'queue_checked_at', 'workflow_registration_date'):
                if previous.get(field) is not None and previous.get(field) != '' and (entry.get(field) is None or entry.get(field) == ''):
                    entry[field] = previous[field]
            if entry.get('registration_date'):
                entry['reg_date'] = entry['registration_date']
            ensure_record_fields(entry)
            # لینک‌های قدیمیِ Summary بدون DID فقط فهرست عمومی را باز می‌کنند؛
            # آن‌ها نباید به‌عنوان گردش کار ذخیره یا نمایش داده شوند.
            if entry.get('workflow_url') and 'DID=' not in str(entry.get('workflow_url')):
                entry['workflow_url'] = ''
            store[key] = entry
            # Refresh known rows without counting or emitting them as new rows.
            if mode != "new_only" or not already_known:
                collected.append(entry)
                new_on_page += 1
                on_record(entry)
        on_progress(min(90, 15 + int(75 * len(seen) / max(1, total_records or len(seen)))), f"صفحه {page}؛ {len(seen)} رکورد یکتا")
        if total_records is not None and len(seen) >= total_records:
            break
        # مکث مصنوعی بین صفحات حذف شده تا اسکن کامل سریع‌تر انجام شود.
    if mode == "full_rescan" and is_running() and len(seen) != total_records:
        raise IncompleteFullScan(f"اسکن ناقص است: {len(seen)} رکورد یکتا از {total_records}؛ مخزن قبلی جایگزین نمی‌شود.")
    return store, collected, len(collected), total_records or len(seen)


def enrich_with_details(
    session,
    records: List[Dict[str, Any]],
    is_running: Callable[[], bool] = lambda: True,
    on_progress: Callable[[int, str], None] = lambda *_: None,
    limit: int = None,
) -> int:
    """تکمیل شماره ثبت، تاریخ تمدید و لینک گواهی با مراجعه به صفحه جزئیات هر پرونده.

    فقط رکوردهای جدید و تا سقف limit enrichment می‌شوند تا اسکن کند نشود.
    هر خطا نادیده گرفته می‌شود و ستون مربوطه «—» می‌ماند. خروجی: تعداد غنی‌شده.
    """
    enriched = 0
    for record in records:
        ensure_record_fields(record)
    targets = [r for r in records if r.get("detail_url")]
    targets.sort(key=lambda r: "ثبت قطعی شده" not in str(r.get("status", "")))
    if limit is not None:
        targets = targets[:max(0, limit)]
    total = len(targets)
    for i, rec in enumerate(targets, start=1):
        if not is_running():
            break
        # اگر هر سه فیلد از قبل پر است، درخواست نزن
        # Re-read workflow status for old records as well as queue updates.
        try:
            # timeout کوتاه نگه داشته می‌شود تا یک پرونده معیوب کل جستجوی سریع را معطل نکند.
            resp = session.get(rec['detail_url'], timeout=5, verify=False)
            if getattr(resp, 'status_code', 0) != 200:
                raise ValueError('HTTP ' + str(getattr(resp, 'status_code', 0)))
            if any(x in str(getattr(resp, 'url', '')).lower() for x in ('signin', '/login')):
                raise ValueError('نشست منقضی شده؛ دریافت صفحه ورود به جای پرونده')
            detail = parse_declaration_detail(getattr(resp, 'text', ''), getattr(resp, 'url', '') or rec['detail_url'])
            queue_verified = (
                'declarationsummery' in urlsplit(getattr(resp, 'url', '') or rec['detail_url']).path.lower()
                and ('گردش کار پرونده' in getattr(resp, 'text', '') or detail.get('queue_count') is not None)
            )
            # شماره ثبت و تاریخ ثبت قطعی در صفحه گردش کار پرونده قرار دارند.
            workflow_detail = detail
            workflow_url = detail.get('workflow_url') or rec.get('workflow_url')
            # صفحه‌ای که کاربر باید ببیند، Steps است؛ Summary بدون DID فقط فهرست را نشان می‌دهد.
            parts = urlsplit(getattr(resp, 'url', '') or rec['detail_url'])
            query = parse_qs(parts.query)
            token = (query.get('ID') or [''])[0]
            dec_no = re.sub(r'[^0-9]', '', to_english_digits(str(rec.get('dec_no_display') or rec.get('declaration_no') or '')))
            if token and dec_no:
                rec['steps_url'] = f"{parts.scheme or 'https'}://{parts.netloc or 'ipm.ssaa.ir'}/CA/Steps?" + urlencode({'Type': 'BusinessSign', 'DecNo': dec_no, 'ID': token})
            if workflow_url and 'DID=' not in str(workflow_url):
                workflow_url = ''
            if workflow_url:
                workflow_url = urljoin(getattr(resp, 'url', '') or rec['detail_url'], workflow_url)
                rec['workflow_url'] = workflow_url
            if workflow_url:
                try:
                    wf_resp = session.get(workflow_url, timeout=5, verify=False)
                    if getattr(wf_resp, 'status_code', 0) == 200:
                        workflow_detail = parse_declaration_detail(getattr(wf_resp, 'text', ''), getattr(wf_resp, 'url', '') or workflow_url)
                        workflow_valid = (
                            not any(x in str(getattr(wf_resp, 'url', '')).lower() for x in ('signin', '/login'))
                            and ('گردش کار پرونده' in getattr(wf_resp, 'text', '') or workflow_detail.get('queue_count') is not None)
                        )
                        if workflow_valid:
                            queue_verified = True
                            detail['queue_count'] = workflow_detail.get('queue_count')
                        for key in ('register_no', 'reg_date', 'renewal_date', 'certificate_url'):
                            if workflow_detail.get(key):
                                detail[key] = workflow_detail[key]
                except Exception as exc:
                    logger.warning("Workflow request failed: %s", type(exc).__name__)
            verified_page = workflow_detail if workflow_url and queue_verified else detail
            page_number = verified_page.get('workflow_declaration_no') if queue_verified else ''
            expected_number = re.sub(r'[^0-9]', '', to_english_digits(str(rec.get('dec_no_display') or rec.get('declaration_no') or '')))
            if page_number and expected_number and page_number != expected_number:
                rec['registration_fetch_status'] = 'identity_mismatch'
                logger.error("Workflow identity mismatch: expected=%s received=%s; skipped", expected_number, page_number)
                continue
            if page_number and expected_number == page_number and verified_page.get('workflow_status'):
                if 'list_status' not in rec:
                    rec['status'] = verified_page['workflow_status']
                rec['workflow_status'] = verified_page['workflow_status']
                rec['workflow_status_verified'] = True
                rec['workflow_status_checked_at'] = datetime.now(timezone.utc).isoformat()
                # An explicit, matching workflow page supersedes stale metadata.
                # Formation/declaration dates must never stand in for registration.
                rec['register_no'] = verified_page.get('register_no') or ''
                rec['workflow_registration_date'] = verified_page.get('workflow_registration_date') or ''
                rec['registration_date'] = rec['workflow_registration_date']
                if verified_page.get('formation_date'):
                    rec['formation_date'] = verified_page['formation_date']
                if rec['registration_date']:
                    rec['reg_date'] = rec['registration_date']
                else:
                    rec['reg_date'] = verified_page.get('formation_date') or rec.get('declaration_date', '')
                logger.info("Workflow status verified: declaration=%s status=%s", expected_number, rec['status'])
            if queue_verified:
                rec['queue_count'] = (None if 'ثبت قطعی شده' in str(rec.get('status', '')) else detail.get('queue_count'))
                rec['queue_checked_at'] = datetime.now(timezone.utc).isoformat()
            if detail.get('register_no'):
                rec['register_no'] = detail['register_no']
            if rec.get('workflow_registration_date'):
                rec['registration_date'] = rec['workflow_registration_date']
                rec['reg_date'] = rec['workflow_registration_date']
            if detail.get('renewal_date'):
                rec['renewal_date'] = detail['renewal_date']
            if detail.get('certificate_url'):
                rec['certificate_url'] = detail['certificate_url']
            if detail.get('print_url'):
                rec['print_url'] = detail['print_url']
            if detail.get('title_fa'):
                rec['title_fa'] = detail['title_fa']
            if detail.get('title_en'):
                rec['title_en'] = detail['title_en']
            ensure_record_fields(rec)
            if rec.get('registration_date'):
                rec['registration_fetch_status'] = 'ok'
                enriched += 1
            elif 'ثبت قطعی شده' in str(rec.get('status', '')):
                rec['registration_fetch_status'] = ('workflow_missing_date' if workflow_url else 'workflow_link_missing')
                logger.warning("Registration unavailable: declaration=%s reason=%s page=%s", rec.get('declaration_no', ''), rec['registration_fetch_status'], urlsplit(getattr(resp, 'url', '') or rec['detail_url']).path)
        except Exception as exc:
            rec['registration_fetch_status'] = 'request_failed'
            logger.warning("Registration request failed: declaration=%s error=%s", rec.get('declaration_no', ''), type(exc).__name__)
            continue
        if i % 10 == 0:
            try:
                on_progress(90, f"تکمیل جزئیات پرونده‌ها ({i}/{total})...")
            except Exception:
                pass
        # بدون مکث مصنوعی؛ کنترل نرخ درخواست را timeout و سرور انجام می‌دهند.
    registered = [r for r in targets if 'ثبت قطعی شده' in str(r.get('status', ''))]
    missing = sum(not r.get('registration_date') for r in registered)
    logger.info("Registration summary: checked=%s registered=%s missing=%s", total, len(registered), missing)
    on_progress(91, f"تاریخ ثبت قطعی: {len(registered) - missing} تکمیل، {missing} ناموفق")
    return enriched

