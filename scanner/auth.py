import os
import sys
import json
import re
import time
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional, List
import requests
import urllib3

from scanner.logger import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("auth")

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(ROOT_DIR, "session_auth.json")
ACCOUNTS_DIR = os.path.join(ROOT_DIR, "accounts")
DATA_STORE_PATH = os.path.join(ROOT_DIR, "data_store.json")
WORD_OUTPUT_PATH = os.path.join(ROOT_DIR, "brands.docx")

START_URL = "https://ipm.ssaa.ir/CA/DeclarationList"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def sanitize_account_name(name: str) -> str:
    """تبدیل نام حساب به رشته‌ای ایمن برای نام پوشه در ویندوز."""
    clean = re.sub(r'[\\/*?:"<>|]', '_', name).strip()
    return clean if clean else "default_user"


def get_account_dir(user_name: str) -> str:
    """مسیر پوشه اختصاصی حساب کاربری را برمی‌گرداند و در صورت نیاز می‌سازد."""
    folder_name = sanitize_account_name(user_name)
    acc_dir = os.path.join(ACCOUNTS_DIR, folder_name)
    os.makedirs(acc_dir, exist_ok=True)
    return acc_dir


def has_account_saved_data(user_name: str) -> Tuple[bool, int, str]:
    """
    بررسی وجود سوابق اسکن‌شده برای یک حساب:
    خروجی: (آیا داده موجود است؟، تعداد رکوردها، تاریخ آخرین اسکن)
    """
    acc_dir = get_account_dir(user_name)
    store_file = os.path.join(acc_dir, "data_store.json")
    meta_file = os.path.join(acc_dir, "meta.json")

    if not os.path.exists(store_file):
        return False, 0, ""

    try:
        with open(store_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            count = len(data)

        last_date = ""
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                last_date = meta.get("last_scan_date", "")

        return count > 0, count, last_date
    except Exception as e:
        logger.warning(f"خطا در بررسی سوابق حساب {user_name}: {e}")
        return False, 0, ""


def save_account_data(user_name: str, store: Dict[str, Any], docx_path: str = ""):
    """ذخیره و همگام‌سازی فایل‌های یک حساب در پوشه اختصاصی آن."""
    if not user_name:
        return

    acc_dir = get_account_dir(user_name)
    acc_store = os.path.join(acc_dir, "data_store.json")
    acc_meta = os.path.join(acc_dir, "meta.json")

    try:
        # ۱. ذخیره data_store.json
        with open(acc_store, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)

        # ۲. کپی فایل Word در صورت وجود
        if docx_path and os.path.exists(docx_path):
            acc_docx = os.path.join(acc_dir, "brands.docx")
            shutil.copy2(docx_path, acc_docx)

        # ۳. ثبت متادیتا
        meta_payload = {
            "user_name": user_name,
            "total_records": len(store),
            "last_scan_date": time.strftime("%Y/%m/%d %H:%M:%S")
        }
        with open(acc_meta, "w", encoding="utf-8") as f:
            json.dump(meta_payload, f, ensure_ascii=False, indent=2)

        logger.info(f"اطلاعات اسکن مربوط به حساب '{user_name}' با {len(store)} رکورد در پوشه {acc_dir} ذخیره گردید.")
    except Exception as e:
        logger.error(f"خطا در ذخیره داده‌های حساب {user_name}: {e}")


def restore_account_data(user_name: str) -> Tuple[Dict[str, Any], str]:
    """بازیابی داده‌های ذخیره‌شده حساب به فایل‌های فعال برنامه."""
    acc_dir = get_account_dir(user_name)
    acc_store = os.path.join(acc_dir, "data_store.json")
    acc_docx = os.path.join(acc_dir, "brands.docx")

    store = {}
    if os.path.exists(acc_store):
        try:
            with open(acc_store, "r", encoding="utf-8") as f:
                store = json.load(f)
            # رونوشت به data_store فعال ریشه
            with open(DATA_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(store, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"خطا در بازیابی data_store: {e}")

    restored_docx = ""
    if os.path.exists(acc_docx):
        try:
            shutil.copy2(acc_docx, WORD_OUTPUT_PATH)
            restored_docx = WORD_OUTPUT_PATH
        except Exception as e:
            logger.error(f"خطا در رونوشت brands.docx: {e}")

    logger.info(f"داده‌های حساب '{user_name}' بازیابی شدند ({len(store)} رکورد).")
    return store, restored_docx


def has_saved_session() -> bool:
    """بررسی وجود نشست معتبر ذخیره‌شده در فایل."""
    return os.path.exists(SESSION_FILE)


def get_saved_cookies() -> Dict[str, str]:
    """خواندن کوکی‌های ذخیره‌شده از فایل نشست."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cookies = data.get("cookies", {})
                    if cookies:
                        return cookies
        except Exception as e:
            logger.warning(f"خطا در خواندن session_auth.json: {e}")
    return {}


def get_saved_cookie_list() -> List[Dict[str, Any]]:
    """خواندن فهرست کامل کوکی‌ها همراه با خصوصیات امنیتی."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("cookie_list", [])
        except Exception:
            pass
    return []


def save_cookies(cookies: Dict[str, str], user_name: str = ""):
    """ذخیره کوکی‌ها و اطلاعات نشست در فایل."""
    try:
        payload = {
            "user_name": user_name,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cookies": cookies
        }
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        logger.info(f"اطلاعات نشست کاربر '{user_name}' با {len(cookies)} کوکی ذخیره شد.")
    except Exception as e:
        logger.error(f"خطا در ذخیره سازی نشست: {e}")


def get_authenticated_session() -> requests.Session:
    """ایجاد یا بازیابی نشست requests با کوکی‌های ذخیره‌شده."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
        "Referer": START_URL,
    })

    # ابتدا کوکی‌های ساختاریافته کامل را بارگذاری کنیم
    cookie_list = get_saved_cookie_list()
    if cookie_list:
        for c in cookie_list:
            session.cookies.set(
                name=c.get("name", ""),
                value=c.get("value", ""),
                domain=c.get("domain") or "ipm.ssaa.ir",
                path=c.get("path") or "/",
                secure=bool(c.get("secure", False))
            )
    else:
        # در غیر این صورت دیکشنری ساده کوکی‌ها
        cookies = get_saved_cookies()
        for k, v in cookies.items():
            session.cookies.set(k, v, domain="ipm.ssaa.ir", path="/")

    return session


def get_saved_user_name() -> str:
    """خواندن نام کاربر از نشست جاری."""
    if not os.path.exists(SESSION_FILE):
        return ""
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("user_name", "")
    except Exception:
        return ""


def check_session_alive(session: Optional[requests.Session] = None) -> Tuple[bool, str]:
    """بررسی وجود نام کاربر در فایل نشست."""
    if not has_saved_session():
        return False, "no_session"

    user_name = get_saved_user_name()
    if user_name:
        return True, user_name
    return True, "کاربر سامانه"


def clear_active_session():
    """
    حذف توکن‌ها و نشست جاری در هنگام بستن برنامه یا خروج از حساب.
    اطلاعات آرشیو شده هر حساب در پوشه accounts/ دست‌نخورده باقی می‌ماند.
    """
    for fname in ["session_auth.json", "session_storage.json"]:
        p = os.path.join(ROOT_DIR, fname)
        if os.path.exists(p):
            try:
                os.remove(p)
                logger.info(f"فایل توکن موقت {p} هنگام خروج پاکسازی شد.")
            except Exception as e:
                logger.warning(f"عدم امکان حذف {p}: {e}")


def clear_saved_session():
    """حذف دستی نشست ذخیره‌شده."""
    clear_active_session()


def perform_browser_login(timeout_seconds: int = 360, on_status_update=None) -> Tuple[bool, str]:
    """
    باز کردن پنجره ورود بومی با استفاده از Microsoft Edge WebView2 ویندوز.
    (کاملاً مستقل از Playwright و بدون نیاز به نصب مرورگر Google Chrome)
    """
    msg = "در حال باز کردن پنجره ورود با موتور وب‌ویوی بومی ویندوز (Edge WebView2)..."
    logger.info(msg)
    if on_status_update:
        on_status_update(msg)

    login_script = os.path.join(ROOT_DIR, "scanner", "login_window.py")
    if not os.path.exists(login_script):
        logger.error(f"اسکریپت لاگین یافت نشد: {login_script}")
        return False, "اسکریپت ورود به سامانه موجود نیست."

    try:
        # اجرای اسکریپت پنجره لاگین در فرآیند فرزند مستقل
        cmd = [sys.executable, login_script]
        logger.info(f"اجرای فرآیند پنجره لاگین: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        stdout, stderr = proc.communicate(timeout=timeout_seconds)

        if proc.returncode != 0 and not os.path.exists(SESSION_FILE):
            logger.warning(f"خطا در اجرای پنجره ورود: {stderr}")
            return False, f"خطا در باز کردن پنجره ورود: {stderr.strip()[:200]}"

        # بررسی نتایج استخراج شده در session_auth.json
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    user_name = data.get("user_name", "کاربر سامانه")
                    cookies = data.get("cookies", {})
                    if cookies:
                        logger.info(f"ورود با موفقیت انجام شد: کاربر='{user_name}'، تعداد کوکی‌ها={len(cookies)}")
                        return True, user_name
            except Exception as e:
                logger.error(f"خطا در خواندن فایل نشست پس از ورود: {e}")

        # در صورتی که کاربری ذخیره نشده باشد
        return False, "پنجره ورود بدون لاگین بسته شد یا مهلت زمانی به پایان رسید."

    except subprocess.TimeoutExpired:
        logger.warning("مهلت زمان ورود کاربر به پایان رسید.")
        try:
            proc.kill()
        except Exception:
            pass
        return False, "مهلت زمان ورود به پایان رسید."
    except Exception as e:
        logger.critical(f"خطا در فرآیند ورود: {e}")
        return False, f"خطا در فرآیند ورود: {e}"



