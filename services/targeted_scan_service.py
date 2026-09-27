"""Targeted scan use case, independent of Qt and GUI widgets."""
import re
import time
from typing import Any, Callable, Dict, List
from scanner.parser import parse_search_results


class ScanValidationError(RuntimeError):
    pass


def _validate_first_page(html: str) -> List[Dict[str, Any]]:
    if "کد امنیتی نادرست است" in html or "کد امنیتی اشتباه" in html:
        raise ScanValidationError("کد امنیتی (کپچا) اشتباه است. کد جدیدی دریافت کنید.")
    records = parse_search_results(html)
    if records:
        return records
    if "موردی یافت نشد" in html:
        return []
    if not html.strip():
        raise ScanValidationError("پاسخ دریافتی از سامانه ثبت خالی بود.")
    if "خیلی کلی است" in html or "isSearchValid = false" in html:
        raise ScanValidationError("شرایط جستجو از نظر سامانه ثبت خیلی کلی است؛ بازه را محدودتر کنید.")
    snippet = " ".join(re.sub(r"<[^>]+>", " ", html).split())[:120]
    raise ScanValidationError(f"پاسخ غیرمنتظره از سرور ثبت دریافت شد: «{snippet}»")


def _matches_target_class(row: Dict[str, Any], target_class: int = 5) -> bool:
    """بررسی قطعی تعلق داشتن اظهارنامه به طبقه درخواستی (مثلاً طبقه ۵)."""
    classes = row.get("classes", [])
    if isinstance(classes, (list, set, tuple)):
        if target_class in classes:
            return True
    if target_class == 5 and row.get("has_class_5"):
        return True
    return False


def collect_targeted_scan(
    client,
    params: Dict[str, Any],
    captcha: str,
    max_pages: int,
    is_cancelled: Callable[[], bool],
    on_progress: Callable[[int, str], None],
    on_record: Callable[[Dict[str, Any]], None],
) -> List[Dict[str, Any]]:
    on_progress(10, "ارسال درخواست اولیه به سامانه (صفحه ۱)...")
    html, total_records = client.search_first_page(params, captcha)
    if is_cancelled():
        return []

    # استخراج شماره طبقه هدف (پیش‌فرض طبقه ۵)
    raw_class = str(params.get("SignProductId") or "").strip()
    target_class = int(raw_class) if raw_class.isdigit() else 5

    first_page = _validate_first_page(html)
    collected: List[Dict[str, Any]] = []
    seen = set()

    def add(records):
        added = 0
        for row in records:
            # رکوردهایی که طبقه مورد نظر (مثلاً ۵) را ندارند، کاملاً نادیده گرفته و حذف می‌شوند
            if not _matches_target_class(row, target_class):
                continue
            key = row.get("declaration_no")
            if key and key not in seen:
                seen.add(key)
                collected.append(row)
                on_record(row)
                added += 1
        return added

    add(first_page)
    if not first_page:
        on_progress(100, "جستجو انجام شد: موردی یافت نشد.")
        return collected
    on_progress(20, f"صفحه ۱ پردازش شد ({len(collected)} رکورد معتبر طبقه {target_class}).")

    page = 2
    consecutive_empty = 0
    while page <= max_pages and not is_cancelled():
        on_progress(min(90, int(20 + (page / max_pages) * 70)), f"در حال استخراج و پالایش صفحه {page}...")
        time.sleep(1.0)
        raw_html = client.get_page(page, params, captcha, total_records)
        page_records = parse_search_results(raw_html)
        if not page_records:
            break

        # جلوگیری از حلقه تکراری در صورتی که سرور صفحه آخر را مکرراً تکرار کند
        page_keys = [r.get("declaration_no") for r in page_records if r.get("declaration_no")]
        if page_keys and all(k in seen for k in page_keys):
            break

        added_now = add(page_records)
        if added_now == 0:
            consecutive_empty += 1
            if consecutive_empty >= 5:
                break
        else:
            consecutive_empty = 0

        page += 1
    return collected
