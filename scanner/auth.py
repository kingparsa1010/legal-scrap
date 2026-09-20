"""
مدیریت احراز هویت، توکن و نشست پایدار سامانه مالکیت معنوی (SSAA)
Authentication & Persistent Session Manager for ipm.ssaa.ir
"""
import os
import json
import re
import time
from typing import Dict, Any, Tuple, Optional
import requests
import urllib3

from scanner.logger import get_logger

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("auth")

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
SESSION_FILE = os.path.join(ROOT_DIR, "session_auth.json")
STORAGE_STATE_FILE = os.path.join(ROOT_DIR, "session_storage.json")
START_URL = "https://ipm.ssaa.ir/CA/DeclarationList"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"


def has_saved_session() -> bool:
    """بررسی وجود فایل‌های نشست ذخیره‌شده."""
    return os.path.exists(STORAGE_STATE_FILE) or os.path.exists(SESSION_FILE)


def get_saved_cookies() -> Dict[str, str]:
    """خواندن کوکی‌های ذخیره‌شده از فایل نشست یا فایل استوریج استیت."""
    # ابتدا از فایل نشست ساختاریافته بخوانیم
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    cookies = data.get("cookies", {})
                    if cookies:
                        return cookies
                elif isinstance(data, list):
                    return {c["name"]: c["value"] for c in data if "name" in c and "value" in c}
        except Exception as e:
            logger.warning(f"خطا در خواندن session_auth.json: {e}")

    # در صورت عدم وجود، از storage_state استخراج شود
    if os.path.exists(STORAGE_STATE_FILE):
        try:
            with open(STORAGE_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cookie_list = data.get("cookies", [])
                cookies = {c["name"]: c["value"] for c in cookie_list if "name" in c and "value" in c}
                if cookies:
                    return cookies
        except Exception as e:
            logger.warning(f"خطا در خواندن session_storage.json: {e}")

    return {}


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
        logger.info(f"اطلاعات نشست کاربر '{user_name}' با {len(cookies)} کوکی در {SESSION_FILE} ذخیره شد.")
    except Exception as e:
        logger.error(f"خطا در ذخیره سازی نشست: {e}")


def get_authenticated_session() -> requests.Session:
    """ایجاد یا بازیابی نشست requests با کوکی‌های ذخیره‌شده."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fa,en-US;q=0.9,en;q=0.8",
    })
    cookies = get_saved_cookies()
    for k, v in cookies.items():
        session.cookies.set(k, v, domain="ipm.ssaa.ir")
    return session


def get_saved_user_name() -> str:
    """خواندن نام کاربر از نشست ذخیره‌شده."""
    if not os.path.exists(SESSION_FILE):
        return ""
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("user_name", "")
    except Exception:
        return ""


def check_session_alive(session: Optional[requests.Session] = None) -> Tuple[bool, str]:
    """
    بررسی اولیه وجود و وضعیت نشست جاری:
    خروجی: (آیا نشست وجود دارد؟, نام کاربر یا وضعیت)
    """
    if not has_saved_session():
        logger.debug("هیچ نشست ذخیره‌شده‌ای یافت نشد.")
        return False, "no_session"

    user_name = get_saved_user_name()
    if user_name:
        logger.debug(f"نشست محلی برای کاربر '{user_name}' معتبر تشخیص داده شد.")
        return True, user_name

    return True, "کاربر سامانه"


def clear_saved_session():
    """حذف کامل نشست‌های ذخیره‌شده جهت خروج از حساب."""
    for path in [SESSION_FILE, STORAGE_STATE_FILE]:
        if os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"فایل نشست {path} حذف شد.")
            except Exception as e:
                logger.error(f"خطا در حذف {path}: {e}")


def perform_browser_login(timeout_seconds: int = 300, on_status_update=None) -> Tuple[bool, str]:
    """
    باز کردن پنجره مرورگر جهت ورود دستی کاربر و حل کپچا، سپس ذخیره خودکار کامل Storage State و کوکی‌ها.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("کتابخانه playwright نصب نیست.")
        return False, "کتابخانه playwright نصب نیست."

    msg = "در حال باز کردن پنجره مرورگر برای ورود دستی به سامانه..."
    logger.info(msg)
    if on_status_update:
        on_status_update(msg)

    try:
        with sync_playwright() as p:
            logger.debug("راه‌اندازی Chromium با headless=False")
            browser = p.chromium.launch(
                headless=False,
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
            context = browser.new_context(
                no_viewport=True,
                user_agent=USER_AGENT
            )
            page = context.new_page()

            logger.info(f"در حال هدایت به {START_URL}")
            try:
                page.goto(START_URL, timeout=60000)
            except Exception as e:
                logger.warning(f"خطا در بارگذاری اولیه صفحه: {e}")

            start = time.time()
            logged_in = False
            user_name = "کاربر سامانه"

            while time.time() - start < timeout_seconds:
                try:
                    # بررسی ورود با تشخیص userData یا جدول اظهارنامه‌ها
                    user_data_count = page.locator("#userData").count()
                    data_list_count = page.locator("#DataList").count()

                    if user_data_count > 0 or data_list_count > 0:
                        logged_in = True
                        if user_data_count > 0:
                            text = page.locator("#userData").inner_text()
                            clean = re.sub(r'\s+', ' ', text).replace("خروج", "").replace("سلام", "").strip()
                            if clean:
                                user_name = clean
                        logger.info(f"ورود موفق کاربر تشخیص داده شد: '{user_name}'")
                        break
                except Exception as e:
                    logger.debug(f"درحال انتظار برای ورود... ({e})")

                time.sleep(1.5)

            if not logged_in:
                logger.warning("مهلت زمان ورود منقضی شد یا پنجره توسط کاربر بسته شد.")
                browser.close()
                return False, "زمان ورود منقضی شد یا پنجره بسته شد."

            # ۱. ذخیره کامل وضعیت نشست مرورگر (کوکی‌ها با تمام خصوصیات امنیتی + localStorage)
            try:
                context.storage_state(path=STORAGE_STATE_FILE)
                logger.info(f"وضعیت کامل نشست (storage_state) در {STORAGE_STATE_FILE} ذخیره شد.")
            except Exception as e:
                logger.error(f"خطا در ذخیره storage_state: {e}")

            # ۲. استخراج کوکی‌ها جهت سازگاری با ماژول‌های سبک requests
            try:
                cookies_list = context.cookies()
                cookies_dict = {c["name"]: c["value"] for c in cookies_list}
                save_cookies(cookies_dict, user_name)
            except Exception as e:
                logger.error(f"خطا در ذخیره کوکی‌های متنی: {e}")

            browser.close()
            logger.info("پنجره ورود مرورگر بسته شد و اطلاعات با موفقیت ثبت شد.")
            return True, user_name

    except Exception as e:
        logger.critical(f"خطای بحرانی در فرآیند ورود: {e}")
        return False, f"خطا در فرآیند ورود: {e}"


