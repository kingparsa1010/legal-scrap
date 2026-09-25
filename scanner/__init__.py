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
