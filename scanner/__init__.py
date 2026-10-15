"""
سامانه استخراج و پایش علائم تجاری مرکز مالکیت معنوی
Legal Scraping & Trademark Brand Protection Engine
"""
import os
import sys

def get_base_dir() -> str:
    """
    برگرداندن مسیر ریشه برنامه:
    در حالت فایل EXE فریز شده، مسیر پوشه قرارگیری فایل اجرایی برگردانده می‌شود.
    در حالت سورس پایتون، مسیر ریشه پروژه برگردانده می‌شود.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = get_base_dir()

def get_data_dir() -> str:
    """
    مسیر پوشه واحد داده‌های برنامه (data/)؛ در صورت عدم وجود ساخته می‌شود.
    """
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

DATA_DIR = os.path.join(BASE_DIR, "data")

# پوشه پروفایل مشترک Edge WebView2 برای حفظ نشست (کوکی‌ها) بین پنجره‌ها.
# پنجره ورود و پنجره‌های مشاهده پرونده هر دو از همین پروفایل استفاده می‌کنند
# تا بعد از یک‌بار ورود، باز کردن گواهی/پرونده نیاز به لاگین مجدد نداشته باشد.
WEBVIEW_PROFILE_DIR = os.path.join(DATA_DIR, "webview_profile")


def webview_start_kwargs() -> dict:
    """پارامترهای مشترک webview.start برای نشست یکپارچه (غیرخصوصی + پروفایل ماندگار)."""
    return {"gui": "edgechromium", "debug": False, "private_mode": False, "storage_path": WEBVIEW_PROFILE_DIR}
