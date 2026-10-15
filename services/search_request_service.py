"""Pure construction and validation of targeted-search requests."""
from dataclasses import dataclass
from typing import Any, Dict
from scanner.parser import to_english_digits


class SearchRequestError(ValueError):
    pass


@dataclass(frozen=True)
class SearchRequest:
    params: Dict[str, Any]
    scan_date: str
    title_summary: str


def _digits(value: Any) -> str:
    return to_english_digits(str(value or "").strip())


def build_search_request(values: Dict[str, Any], is_today: bool) -> SearchRequest:
    class_value = _digits(values.get("class")) or "5"
    item_title = str(values.get("item_title") or "").strip()
    declaration_no = _digits(values.get("declaration_no"))
    register_no = _digits(values.get("register_no"))
    from_date = None if is_today else (_digits(values.get("from_issue_date")) or None)
    to_date = None if is_today else (_digits(values.get("to_issue_date")) or None)

    if not is_today and not any((from_date, item_title, declaration_no, register_no)):
        raise SearchRequestError("حداقل تاریخ انتشار، عنوان، شماره اظهارنامه یا شماره ثبت لازم است.")

    if is_today:
        scan_date = "منتشر شده امروز (روزنامه جاری)"
        title_summary = f"طبقه {class_value} — آگهی‌های امروز"
    else:
        scan_date = from_date or "سفارشی"
        title_summary = f"طبقه {class_value}"
        if from_date:
            title_summary += f" از {from_date}"
        if to_date:
            title_summary += f" تا {to_date}"
        if item_title:
            title_summary += f" («{item_title[:15]}» )"

    params = {
        "GetCurrentIssue": is_today,
        "FromIssueDate": from_date,
        "ToIssueDate": to_date,
        "SignProductId": class_value,
        "SignImageStage": _digits(values.get("image_stage")) or None,
        "ItemTitle": item_title or None,
        "SearchItemTitleAsLike": str(values.get("title_like", "3")),
        "RegisterNo": register_no or None,
        "DeclarationNo": declaration_no or None,
        "ManualNo": _digits(values.get("manual_no")) or None,
        "FromDeclarationDateRange": _digits(values.get("from_declaration_date")) or None,
        "ToDeclarationDateRange": _digits(values.get("to_declaration_date")) or None,
        "personType": str(values.get("person_type", "1")),
        "RealOwnerName": str(values.get("owner_name") or "").strip() or None,
        "RealOwnerFamily": str(values.get("owner_family") or "").strip() or None,
        "RealOwnerNationalityCode": _digits(values.get("national_code")) or None,
        "LegalOwnerRecordNo": _digits(values.get("legal_record_no")) or None,
        "LegalOwnerNationalityNo": _digits(values.get("legal_national_no")) or None,
    }
    return SearchRequest(params=params, scan_date=scan_date, title_summary=title_summary)
