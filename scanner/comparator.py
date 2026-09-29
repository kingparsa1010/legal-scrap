"""
موتور مقایسه عنوان‌های data_store با رکوردهای اسکن‌شده کلاس ۵ (حالت ۲)
Manual comparison engine: SQLite declaration records × class-5 records
"""
from typing import Any, Dict, List

from scanner.similarity import TrademarkSimilarityEngine
from scanner.store import load_store, load_class5_store, DATA_STORE_PATH
from scanner.parser import to_english_digits, is_rejected_status
from scanner.logger import get_logger

logger = get_logger("comparator")


def is_rejected_entry(entry: Dict[str, Any]) -> bool:
    """بررسی اینکه آیا پرونده رد شده، ابطال شده یا نامعتبر است."""
    if not entry or not isinstance(entry, dict):
        return False
    is_rej = entry.get("is_rejected")
    if is_rej is True or is_rej == 1 or str(is_rej).strip().lower() in ("true", "1"):
        return True
    return is_rejected_status(entry.get("status", ""))


def compare_stores(
    data_store: Dict[str, Any],
    class5_store: Dict[str, Any],
    threshold: float = None,
    include_rejected: bool = False,
) -> List[Dict[str, Any]]:
    """
    مقایسه تمام عنوان‌های data_store با تمام رکوردهای کلاس ۵.
    رکوردهای رد شده در سامانه (به‌ویژه در بخش جستجوی پیشرفته) در نتایج مقایسه نمایش داده نمی‌شوند.
    خروجی: لیست جفت‌های منطبق (مرتب‌شده بر اساس درصد شباهت نزولی).
    """
    engine = TrademarkSimilarityEngine()
    if threshold is None:
        threshold = engine.medium_threshold

    data_entries = [
        e for e in data_store.values()
        if e.get("title") and (include_rejected or not is_rejected_entry(e))
    ]
    class5_entries = [
        e for e in class5_store.values()
        if e.get("title")
        and (include_rejected or not is_rejected_entry(e))
        and (e.get("has_class_5") or not e.get("classes") or 5 in e.get("classes", []))
    ]

    logger.info(
        "آماده‌سازی مقایسه: %d عنوان مرجع با %d رکورد معتبر (غیر رد شده) کلاس ۵",
        len(data_entries), len(class5_entries)
    )

    if not data_entries or not class5_entries:
        return []

    matches: List[Dict[str, Any]] = []
    for a in data_entries:
        title_a = a.get("title", "")
        for b in class5_entries:
            # جلوگیری از مقایسه یک رکورد با خودش
            if _same_record(a, b):
                continue
            score = engine.calculate_similarity(title_a, b.get("title", ""))
            if score < threshold:
                continue
            risk = "high" if score >= engine.high_threshold else "medium"
            matches.append(_build_match(a, b, score, risk))

    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches


def compare_default_stores(threshold: float = None, include_rejected: bool = False) -> List[Dict[str, Any]]:
    """مقایسه مخزن‌های پیش‌فرض SQLite."""
    return compare_stores(load_store(DATA_STORE_PATH), load_class5_store(), threshold, include_rejected=include_rejected)


def _same_record(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    a_raw = str(a.get("dec_no_id") or a.get("declaration_no") or a.get("dec_no_display") or "")
    b_raw = str(b.get("dec_no_id") or b.get("declaration_no") or b.get("dec_no_display") or "")
    a_no = to_english_digits(a_raw).strip()
    b_no = to_english_digits(b_raw).strip()
    a_clean = a_no.lstrip('0') or a_no
    b_clean = b_no.lstrip('0') or b_no
    return bool(a_clean) and a_clean == b_clean


def _build_match(a: Dict[str, Any], b: Dict[str, Any], score: float, risk: str) -> Dict[str, Any]:
    return {
        "score": score,
        "risk": risk,
        "title_a": a.get("title", ""),
        "declaration_no_a": a.get("dec_no_display") or a.get("declaration_no", ""),
        "declaration_date_a": a.get("declaration_date") or a.get("reg_date", ""),
        "status_a": a.get("status", ""),
        "detail_url_a": a.get("detail_url", ""),
        "title_b": b.get("title", ""),
        "declaration_no_b": b.get("dec_no_display") or b.get("declaration_no", ""),
        "declaration_date_b": b.get("declaration_date") or b.get("reg_date", ""),
        "status_b": b.get("status", ""),
        "detail_url_b": b.get("detail_url", ""),
    }
