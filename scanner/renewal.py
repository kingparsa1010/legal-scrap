"""Registration-based renewal reminder dates (Jalali calendar)."""
from datetime import datetime, timedelta, timezone
import jdatetime

def renewal_info(record, today=None):
    raw = str(record.get("workflow_registration_date") or "").strip()
    if not raw:
        return "", None, "تاریخ ثبت نامشخص"
    try:
        year, month, day = map(int, raw.replace("-", "/").split("/"))
        registered = jdatetime.date(year, month, day)
        try:
            anniversary = jdatetime.date(year + 10, month, day)
        except ValueError:
            anniversary = jdatetime.date(year + 10, month, day - 1)
        target = anniversary - timedelta(days=120)
        if today is None:
            current = datetime.now(timezone(timedelta(hours=3, minutes=30))).date()
            today = jdatetime.date.fromgregorian(date=current)
        days = (target - today).days
        label = (f"{days} روز باقی‌مانده" if days > 0 else
                 "امروز موعد است" if days == 0 else f"{-days} روز از موعد گذشته")
        date = target.strftime("%Y/%m/%d")
        return date, days, f"{date} — {label}"
    except (ValueError, TypeError, OverflowError):
        return "", None, "تاریخ ثبت نامشخص"

